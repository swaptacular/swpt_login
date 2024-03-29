from werkzeug.local import LocalProxy
from flask_sqlalchemy import SQLAlchemy
from swpt_pythonlib.flask_signalbus import SignalBusMixin
from flask_mail import Mail
from flask_redis import FlaskRedis
from flask_babel import Babel
from flask_migrate import Migrate
from .api_requests_session import get_requests_session


class CustomAlchemy(SignalBusMixin, SQLAlchemy):
    def apply_driver_hacks(self, app, info, options):
        if "isolation_level" not in options:
            options["isolation_level"] = "REPEATABLE_READ"
        return super().apply_driver_hacks(app, info, options)


db = CustomAlchemy()
migrate = Migrate()
mail = Mail()
redis_store = FlaskRedis(socket_timeout=5, charset="utf-8", decode_responses=True)
babel = Babel()
requests_session = LocalProxy(get_requests_session)


def init_app(app):
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    redis_store.init_app(app)
    babel.init_app(app)
