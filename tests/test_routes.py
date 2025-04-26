import pytest
import re
from typing import Callable
from dataclasses import dataclass
from unittest.mock import Mock
from swpt_login import utils
from swpt_login import models as m
from swpt_login.extensions import mail


@dataclass
class Response:
    status_code: int
    json: Callable = lambda: {}
    raise_for_status = Mock()


@pytest.fixture(scope="function")
def client(app, db_session):
    return app.test_client()


USER_ID = '1234'
USER_EMAIL = "test@example.com"
USER_SALT = utils.generate_password_salt()
USER_PASSWORD = "qwertyuiopasdfg"
USER_RECOVERY_CODE = utils.generate_recovery_code()


@pytest.fixture(params=[200, 500])
def acitivation_status_code(request):
    return request.param


@pytest.fixture
def user(db_session):
    db_session.add(
        m.UserRegistration(
            user_id=USER_ID,
            email=USER_EMAIL,
            salt=USER_SALT,
            password_hash=utils.calc_crypt_hash(USER_SALT, USER_PASSWORD),
            recovery_code_hash=utils.calc_crypt_hash('', USER_RECOVERY_CODE),
            two_factor_login=True,
        )
    )
    db_session.commit()


def test_404_error(client):
    r = client.get("/login/invalid-path")
    assert r.status_code == 404


def test_signup(mocker, client, db_session):
    class ReservationMock:
        post = Mock(return_value=Response(
            200,
            lambda: {
                "type": "DebtorReservation",
                "createdAt": "2019-08-24T14:15:22Z",
                "debtorId": "1234",
                "reservationId": "456",
                "validUntil": "2099-08-24T14:15:22Z"
            },
        ))

    class ActivationMock:
        post = Mock(return_value=Response(
            acitivation_status_code,
            lambda: {
                "type": "Debtor",
                "uri": "/debtors/1234/",
                # The real response has more fields, but they will be
                # ignored.
            },
        ))

    mocker.patch("swpt_login.redis.requests_session", ReservationMock())
    mocker.patch("swpt_login.models.requests_session", ActivationMock())

    r = client.get("/login/signup")
    assert r.status_code == 200
    assert "Create a New Account" in r.get_data(as_text=True)

    with mail.record_messages() as outbox:
        r = client.post("/login/signup", data={
            "email": USER_EMAIL,
        })
        assert r.status_code == 302
        r = client.get(r.location)
        assert "Please check your inbox" in r.get_data(as_text=True)
        assert len(outbox) == 1
        assert outbox[0].subject == "Create a New Account"
        msg = str(outbox[0])

    match = re.search(r"^http://localhost(/login/password/[^/\s]+)", msg, flags=re.M)
    assert match
    received_link = match[1]
    r = client.get(received_link)
    assert r.status_code == 200
    assert "Choose Password" in r.get_data(as_text=True)

    r = client.post(received_link, data={
        "password": USER_PASSWORD,
        "confirm": USER_PASSWORD,
    })
    assert r.status_code == 200
    assert "Your account recovery code is" in r.get_data(as_text=True)

    user = m.UserRegistration.query.one_or_none()
    assert user
    assert user.user_id == "1234"
    assert user.email == USER_EMAIL
    assert user.password_hash == utils.calc_crypt_hash(user.salt, USER_PASSWORD)


def test_change_password(mocker, client, db_session, user):
    invalidate_credentials = Mock()
    mocker.patch("swpt_login.hydra.invalidate_credentials", invalidate_credentials)

    r = client.get("/login/signup?recover=true")
    assert r.status_code == 200
    assert "Change Account Password" in r.get_data(as_text=True)

    with mail.record_messages() as outbox:
        r = client.post("/login/signup?recover=true", data={
            "email": USER_EMAIL,
        })
        assert r.status_code == 302
        r = client.get(r.location)
        assert "Please check your inbox" in r.get_data(as_text=True)
        assert len(outbox) == 1
        assert outbox[0].subject == "Change Account Password"
        msg = str(outbox[0])

    match = re.search(r"^http://localhost(/login/password/[^/\s]+)", msg, flags=re.M)
    assert match
    received_link = match[1]
    r = client.get(received_link)
    assert r.status_code == 200
    assert "Choose Password" in r.get_data(as_text=True)

    r = client.post(received_link, data={
        "recovery_code": "wrong_recovery_code",
        "password": "my shiny new password",
        "confirm": "my shiny new password",
    })
    assert r.status_code == 200
    assert "Incorrect recovery code" in r.get_data(as_text=True)
    invalidate_credentials.assert_not_called()
    assert m.UserRegistration.query.filter_by(
        password_hash=utils.calc_crypt_hash(USER_SALT, USER_PASSWORD),
    ).one_or_none()

    r = client.post(received_link, data={
        "recovery_code": USER_RECOVERY_CODE,
        "password": "my shiny new password",
        "confirm": "my shiny new password",
    })
    assert r.status_code == 200
    invalidate_credentials.assert_called_with(USER_ID)
    assert "Your password has been successfully reset" in r.get_data(as_text=True)
    assert m.UserRegistration.query.filter_by(
        password_hash=utils.calc_crypt_hash(USER_SALT, "my shiny new password"),
    ).one_or_none()


def test_change_recovery_code(client, db_session, user):
    r = client.get("/login/change-recovery-code")
    assert r.status_code == 200
    assert "Change Recovery Code" in r.get_data(as_text=True)
    assert "Enter your email" in r.get_data(as_text=True)

    with mail.record_messages() as outbox:
        r = client.post("/login/change-recovery-code", data={
            "email": USER_EMAIL,
        })
        assert r.status_code == 302
        r = client.get(r.location)
        assert "An email has been sent" in r.get_data(as_text=True)
        assert len(outbox) == 1
        assert outbox[0].subject == "Change Recovery Code"
        msg = str(outbox[0])

    match = re.search(r"^http://localhost(/login/recovery-code/[^/\s]+)", msg, flags=re.M)
    assert match
    received_link = match[1]
    r = client.get(received_link)
    assert r.status_code == 200
    assert "Change Recovery Code" in r.get_data(as_text=True)
    assert "Enter your password" in r.get_data(as_text=True)

    r = client.post(received_link, data={
        "password": "wrong_password",
    })
    assert r.status_code == 200
    assert "Incorrect password" in r.get_data(as_text=True)
    assert m.UserRegistration.query.filter_by(
        recovery_code_hash=utils.calc_crypt_hash('', USER_RECOVERY_CODE),
    ).one_or_none()

    r = client.post(received_link, data={
        "password": USER_PASSWORD,
    })
    assert r.status_code == 200
    print(r.get_data(as_text=True))
    assert "Your account recovery code has been changed" in r.get_data(as_text=True)
    assert not m.UserRegistration.query.filter_by(
        recovery_code_hash=utils.calc_crypt_hash('', USER_RECOVERY_CODE),
    ).one_or_none()
