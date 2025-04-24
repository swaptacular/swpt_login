import pytest
import sqlalchemy
import flask_migrate
from datetime import datetime, timezone
from swpt_login import create_app
from swpt_login.extensions import db

config_dict = {
    "TESTING": True,
    "PREFERRED_URL_SCHEME": "http",
    "LOGIN_PATH": "/login",
    "CONSENT_PATH": "/consent",
    "API_RESOURCE_SERVER": "https://resource-server.example.com",
    "API_RESERVE_USER_ID_PATH": "/debtors/.debtor-reserve",
}


@pytest.fixture(scope="module")
def app(request):
    """Get a Flask application object."""

    app = create_app(config_dict)
    with app.app_context():
        flask_migrate.upgrade()
        yield app


@pytest.fixture(scope="function")
def db_session(app):
    """Get a Flask-SQLAlchmey session, with an automatic cleanup."""

    yield db.session

    # Cleanup:
    db.session.remove()
    for cmd in [
        "TRUNCATE TABLE user_registration",
        "TRUNCATE TABLE user_update_signal",
        "TRUNCATE TABLE registered_user_signal",
    ]:
        db.session.execute(sqlalchemy.text(cmd))
    db.session.commit()


@pytest.fixture(scope="function")
def current_ts():
    return datetime.now(tz=timezone.utc)
