#!/bin/sh
set -e

# The WEBSERVER_* variables should be used instead of the GUNICORN_*
# variables, because we do not want to tie the public interface to the
# "gunicorn" server, which we may, or may not use in the future.
export GUNICORN_WORKERS=${WEBSERVER_WORKERS:-1}
export GUNICORN_THREADS=${WEBSERVER_THREADS:-3}

# HYDRA_LOG_LEVEL, HYDRA_LOG_FORMAT, HYDRA_DSN variables should be
# used instead of LOG_LEVEL, LOG_FORMAT, and DSN variables, because
# those names are less ambiguous. Also, for consistency we want to
# allow the "warning" and "critical" log level names.
case "$HYDRA_LOG_LEVEL" in
    warning)
        export LOG_LEVEL=warn
        ;;
    critical)
        export LOG_LEVEL=fatal
        ;;
    ?*)
        export LOG_LEVEL="$HYDRA_LOG_LEVEL"
        ;;
esac
if [[ -n "$HYDRA_LOG_FORMAT" ]]; then
    export LOG_FORMAT="$HYDRA_LOG_FORMAT"
fi
if [[ -n "$HYDRA_DSN" ]]; then
    export DSN="$HYDRA_DSN"
fi

# When SUBJECT_PREFIX is set to one of the two standard values (which
# almost certainly will be case), even if API_RESERVE_USER_ID_PATH
# and/or API_USER_ID_FIELD_NAME variables are not set, we can guess
# their values with certainty.
case "$SUBJECT_PREFIX" in
    debtors:)
        export API_RESERVE_USER_ID_PATH=${API_RESERVE_USER_ID_PATH:-/debtors/.debtor-reserve}
        export API_USER_ID_FIELD_NAME=${API_USER_ID_FIELD_NAME:-debtorId}
        ;;
    creditors:)
        export API_RESERVE_USER_ID_PATH=${API_RESERVE_USER_ID_PATH:-/creditors/.creditor-reserve}
        export API_USER_ID_FIELD_NAME=${API_USER_ID_FIELD_NAME:-creditorId}
        ;;
esac

# If not set, the values of LOGIN_PATH and CONSENT_PATH variables can
# be guessed from the values of URLS_LOGIN and URLS_CONSENT.
if [[ -z "$LOGIN_PATH" ]]; then
    export LOGIN_PATH=$(echo "$URLS_LOGIN" | sed -E "s/^.*(\/[^\/]+)\/?$/\1/")
fi
if [[ -z "$CONSENT_PATH" ]]; then
    export CONSENT_PATH=$(echo "$URLS_CONSENT" | sed -E "s/^.*(\/[^\/]+)\/?$/\1/")
fi

# This function tries to upgrade the login database schema with
# exponential backoff. This is necessary during development, because
# the database might not be running yet when this script executes.
perform_db_upgrade() {
    local retry_after=1
    local time_limit=$(($retry_after << 5))
    local error_file="$APP_ROOT_DIR/flask-db-upgrade.error"
    echo -n 'Running login database schema upgrade ...'
    while [[ $retry_after -lt $time_limit ]]; do
        if flask db upgrade &>$error_file; then
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
        if hydra migrate sql "$DSN" --yes &>$error_file; then
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
    hydraserver)
        exec hydra serve all
        ;;
    all)
        # Spawns all the necessary processes in one container.
        exec supervisord -c "$APP_ROOT_DIR/supervisord.conf"
        ;;
    *)
        exec "$@"
        ;;
esac
