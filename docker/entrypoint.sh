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
    serve)
        exec gunicorn --config "$APP_ROOT_DIR/gunicorn.conf.py" -b :$PORT wsgi:app
        ;;
    supervisord)
        exec supervisord -c "$APP_ROOT_DIR/supervisord.conf"
        ;;
    *)
        exec "$@"
        ;;
esac
