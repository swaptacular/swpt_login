import os
import os.path
import logging
import logging.config

# Configure app logging. If the value of "$APP_LOGGING_CONFIG_FILE" is
# a relative path, the directory of this (__init__.py) file will be
# used as a current directory.
config_filename = os.environ.get('APP_LOGGING_CONFIG_FILE')
if config_filename:  # pragma: no cover
    if not os.path.isabs(config_filename):
        current_dir = os.path.dirname(__file__)
        config_filename = os.path.join(current_dir, config_filename)
    logging.config.fileConfig(config_filename, disable_existing_loggers=False)
else:
    logging.basicConfig(level=logging.WARNING)


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
