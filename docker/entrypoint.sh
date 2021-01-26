#!/bin/sh
set -e

# This function tries to upgrade the database schema with exponential
# backoff. This is necessary during development, because the database
# might not be running yet when this script executes.
perform_db_upgrade() {
    local retry_after=1
    local time_limit=$(($retry_after << 5))
    local error_file="$APP_ROOT_DIR/flask-db-upgrade.error"
    echo -n 'Running database schema upgrade ...'
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

configure_web_server() {
    export GUNICORN_LOGLEVEL=${WEBSERVER_LOGLEVEL:-warning}
    export GUNICORN_WORKERS=${WEBSERVER_WORKERS:-1}
    export GUNICORN_THREADS=${WEBSERVER_THREADS:-3}
}

case $1 in
    develop-run-flask)
        shift;
        exec flask run --host=0.0.0.0 --port $PORT --without-threads "$@"
        ;;
    configure)
        perform_db_upgrade
        ;;
    webserver)
        configure_web_server
        exec gunicorn --config "$APP_ROOT_DIR/gunicorn.conf.py" -b :$PORT wsgi:app
        ;;
    all)
        configure_web_server
        exec supervisord -c "$APP_ROOT_DIR/supervisord.conf"
        ;;
    *)
        exec "$@"
        ;;
esac
