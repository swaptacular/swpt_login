import sqlalchemy
from dataclasses import dataclass
from unittest.mock import Mock
from swpt_login import models as m
from swpt_login.extensions import db


@dataclass
class Response:
    status_code: int


def test_flush_messages_success(mocker, app, db_session):
    class RequestSessionMock:
        post = Mock(return_value=Response(200))

    requests_session = RequestSessionMock()
    mocker.patch("swpt_login.models.requests_session", requests_session)
    assert len(m.ActivateUserSignal.query.all()) == 0
    db.session.add(
        m.ActivateUserSignal(
            user_id="123",
            reservation_id="456",
            email="test@example.com",
            salt="x",
            password_hash="y",
            recovery_code_hash="z",
        )
    )
    db.session.commit()
    assert len(m.ActivateUserSignal.query.all()) == 1
    db.session.commit()

    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "swpt_login",
            "flush",
            "--wait",
            "0.1",
            "--quit-early",
        ]
    )
    assert result.exit_code == 1
    requests_session.post.assert_called_once()
    requests_session.post.assert_called_with(
        json={"reservationId": "456"},
        url="https://resource-server.example.com/debtors/123/activate",
        verify=False,
    )
    assert len(m.ActivateUserSignal.query.all()) == 0
    users = m.UserRegistration.query.all()
    assert len(users) == 1
    assert users[0].email == "test@example.com"
    assert users[0].user_id == "123"
    assert users[0].salt == "x"
    assert users[0].password_hash == "y"
    assert users[0].recovery_code_hash == "z"

    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "swpt_login",
            "flush",
            "--wait",
            "0.1",
            "--quit-early",
        ]
    )
    assert result.exit_code == 1
    requests_session.post.assert_called_once()
    assert len(m.ActivateUserSignal.query.all()) == 0
    assert len(m.UserRegistration.query.all()) == 1


def test_flush_messages_failure(mocker, app, db_session):
    class RequestSessionMock:
        post = Mock(return_value=Response(500))

    requests_session = RequestSessionMock()
    mocker.patch("swpt_login.models.requests_session", requests_session)
    assert len(m.ActivateUserSignal.query.all()) == 0
    db.session.add(
        m.ActivateUserSignal(
            user_id="123",
            reservation_id="456",
            email="test@example.com",
            salt="x",
            password_hash="y",
            recovery_code_hash="z",
        )
    )
    db.session.commit()
    assert len(m.ActivateUserSignal.query.all()) == 1
    db.session.commit()

    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "swpt_login",
            "flush",
            "--wait",
            "0.1",
            "--quit-early",
        ]
    )
    assert result.exit_code == 1
    requests_session.post.assert_called_once()
    assert len(m.ActivateUserSignal.query.all()) == 1
    assert len(m.UserRegistration.query.all()) == 0
