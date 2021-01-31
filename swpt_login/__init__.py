import logging
import sys
import os
import os.path
from typing import List


def configure_logging(level: str, format: str, associated_loggers: List[str]) -> None:  # pragma: no cover
    root_logger = logging.getLogger()

    # Setup the root logger's handler if necessary.
    if not root_logger.hasHandlers():
        handler = logging.StreamHandler(sys.stdout)
        fmt = '%(asctime)s:%(levelname)s:%(name)s:%(message)s'

        if format == 'text':
            handler.setFormatter(logging.Formatter(fmt))
        elif format == 'json':
            from pythonjsonlogger import jsonlogger
            handler.setFormatter(jsonlogger.JsonFormatter(fmt))
        else:
            raise RuntimeError(f'invalid log format: {format}')

        root_logger.addHandler(handler)

    # Set the log level for this app's logger.
    app_logger = logging.getLogger(__name__)
    app_logger.setLevel(level.upper())
    app_logger_level = app_logger.getEffectiveLevel()

    # Make sure that all loggers that are associated to this app have
    # their log levels set to the specified level as well.
    for qualname in associated_loggers:
        logging.getLogger(qualname).setLevel(app_logger_level)

    # Make sure that the root logger's log level (that is: the log
    # level for all third party libraires) is not lower than the
    # specified level.
    if app_logger_level > root_logger.getEffectiveLevel():
        root_logger.setLevel(app_logger_level)

    # Delete all gunicorn's log handlers (they are not needed in a
    # docker container because everything goes to the stdout anyway),
    # and make sure that the gunicorn logger's log level is not lower
    # than the specified level.
    gunicorn_logger = logging.getLogger('gunicorn.error')
    gunicorn_logger.propagate = True
    for h in gunicorn_logger.handlers:
        gunicorn_logger.removeHandler(h)
    if app_logger_level > gunicorn_logger.getEffectiveLevel():
        gunicorn_logger.setLevel(app_logger_level)


def create_app(config_object=None):
    from werkzeug.middleware.proxy_fix import ProxyFix
    from flask import Flask
    from . import extensions
    from .config import Configuration
    from .routes import login, consent

    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_port=1)
    app.config.from_object(config_object or Configuration)
    extensions.init_app(app)
    app.register_blueprint(login, url_prefix=app.config['LOGIN_PATH'])
    app.register_blueprint(consent, url_prefix=app.config['CONSENT_PATH'])
    return app


configure_logging(
    level=os.environ.get('APP_LOG_LEVEL', 'warning'),
    format=os.environ.get('APP_LOG_FORMAT', 'text'),
    associated_loggers=os.environ.get('APP_ASSOCIATED_LOGGERS', '').split(),
)
