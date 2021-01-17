#!/bin/sh
set -e

case $1 in
    develop-run-flask)
        shift;
        export FLASK_ENV=development
        exec flask run --host=0.0.0.0 --port $PORT --without-threads "$@"
        ;;
    configure)
        exec flask db upgrade
        ;;
    webserver)
        export GUNICORN_LOGLEVEL=${WEBSERVER_LOGLEVEL:-warning}
        export GUNICORN_WORKERS=${WEBSERVER_WORKERS:-1}
        export GUNICORN_THREADS=${WEBSERVER_THREADS:-3}
        exec gunicorn --config "$APP_ROOT_DIR/gunicorn.conf.py" -b :$PORT wsgi:app
        ;;
    all)
        exec supervisord -c "$APP_ROOT_DIR/supervisord.conf"
        ;;
    *)
        exec "$@"
        ;;
esac
