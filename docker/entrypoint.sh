#!/bin/sh
set -e

# This function tries to upgrade the login database schema with
# exponential backoff. This is necessary during development, because
# the database might not be running yet when this script executes.
perform_db_upgrade() {
    local retry_after=1
    local time_limit=$(($retry_after << 5))
    local error_file="$APP_ROOT_DIR/flask-db-upgrade.error"
    echo -n 'Running login database schema upgrade ...'
    while [[ $retry_after -lt $time_limit ]]; do
        if flask db upgrade 2>$error_file; then
            perform_db_initialization
            echo ' done.'
            return 0
        fi
        sleep $retry_after
        retry_after=$((2 * retry_after))
    done
    echo
    cat "$error_file"
    return 1
}

# This function is intended to perform additional one-time database
# initialization. Make sure that it is idempotent.
# (https://en.wikipedia.org/wiki/Idempotence)
perform_db_initialization() {
    return 0
}

# This function tries to preform hydra's database migrations with
# exponential backoff. This is necessary during development, because
# the database might not be running yet when this script executes.
perform_hydra_migrations() {
    local retry_after=1
    local time_limit=$(($retry_after << 5))
    local error_file="$APP_ROOT_DIR/hydra-db-migration.error"
    echo -n 'Running hydra schema migrations ...'
    while [[ $retry_after -lt $time_limit ]]; do
        if hydra migrate sql "$DSN" --yes 2>$error_file; then
            echo ' done.'
            return 0
        fi
        sleep $retry_after
        retry_after=$((2 * retry_after))
    done
    echo
    cat "$error_file"
    return 1
}

# HYDRA_DSN is preferred over DSN, because it is less ambiguous.
if [[ -n "$HYDRA_DSN" ]]; then
    export DSN="$HYDRA_DSN"
fi

# If URLS_LOGIN is empty, try to guess its value.
if [[ -z "$URLS_LOGIN" && -n "$URLS_SELF_ISSUER" && -n "LOGIN_PATH" ]]; then
    export URLS_LOGIN="$URLS_SELF_ISSUER$LOGIN_PATH"
fi

# If URLS_CONSENT is empty, try to guess its value.
if [[ -z "$URLS_CONSENT" && -n "$URLS_SELF_ISSUER" && -n "CONSENT_PATH" ]]; then
    export URLS_CONSENT="$URLS_SELF_ISSUER$CONSENT_PATH"
fi

export GUNICORN_LOGLEVEL=${WEBSERVER_LOGLEVEL:-warning}
export GUNICORN_WORKERS=${WEBSERVER_WORKERS:-1}
export GUNICORN_THREADS=${WEBSERVER_THREADS:-3}

case $1 in
    develop-run-flask)
        shift;
        exec flask run --host=0.0.0.0 --port $WEBSERVER_PORT --without-threads "$@"
        ;;
    configure)
        perform_db_upgrade
        perform_hydra_migrations
        ;;
    webserver)
        exec gunicorn --config "$APP_ROOT_DIR/gunicorn.conf.py" -b :$WEBSERVER_PORT wsgi:app
        ;;
    all)
        exec supervisord -c "$APP_ROOT_DIR/supervisord.conf"
        ;;
    *)
        exec "$@"
        ;;
esac
