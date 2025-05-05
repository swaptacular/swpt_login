from werkzeug.local import LocalProxy
from flask_sqlalchemy import SQLAlchemy
from swpt_pythonlib.flask_signalbus import (
    SignalBusMixin,
    AtomicProceduresMixin,
)
from flask_mail import Mail
from flask_babel import Babel
from flask_migrate import Migrate
from .flask_redis import FlaskRedis
from .api_requests_session import get_requests_session


def select_locale():
    from flask import current_app, request

    language = request.cookies.get(current_app.config["LANGUAGE_COOKIE_NAME"])
    language_choices = [
        choices[0] for choices in current_app.config["LANGUAGE_CHOICES"]
    ]
    if language in language_choices:
        return language
    return request.accept_languages.best_match(language_choices, language_choices[0])


def select_timezone():
    return None


class CustomAlchemy(AtomicProceduresMixin, SignalBusMixin, SQLAlchemy):
    pass


db = CustomAlchemy()
migrate = Migrate()
mail = Mail()
redis_store = FlaskRedis(socket_timeout=5, encoding="utf-8", decode_responses=True)
babel = Babel()
requests_session = LocalProxy(get_requests_session)


def init_app(app):
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    redis_store.init_app(app)
    babel.init_app(
        app,
        locale_selector=select_locale,
        timezone_selector=select_timezone,
    )
