from dataclasses import dataclass
from unittest.mock import Mock, call
from swpt_login import models as m
from swpt_login.extensions import db


@dataclass
class Response:
    status_code: int


def test_flush_activations_success(mocker, app, db_session):
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


def test_flush_activations_failure(mocker, app, db_session):
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


def test_flush_deactivations_success(mocker, app, db_session):
    class RequestSessionMock:
        post = Mock(return_value=Response(204))

    requests_session = RequestSessionMock()
    mocker.patch("swpt_login.models.requests_session", requests_session)
    assert len(m.DeactivateUserSignal.query.all()) == 0
    db.session.add(
        m.DeactivateUserSignal(user_id="123")
    )
    db.session.commit()
    assert len(m.DeactivateUserSignal.query.all()) == 1
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
        json={"type": "DebtorDeactivationRequest"},
        url="https://resource-server.example.com/debtors/123/deactivate",
        verify=False,
    )
    assert len(m.DeactivateUserSignal.query.all()) == 0

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


def test_flush_deactivations_failure(mocker, app, db_session):
    class RequestSessionMock:
        post = Mock(return_value=Response(404))

    requests_session = RequestSessionMock()
    mocker.patch("swpt_login.models.requests_session", requests_session)
    assert len(m.DeactivateUserSignal.query.all()) == 0
    db.session.add(
        m.DeactivateUserSignal(user_id="123")
    )
    db.session.commit()
    assert len(m.DeactivateUserSignal.query.all()) == 1
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
    assert len(m.DeactivateUserSignal.query.all()) == 1


def test_suspend_user_registrations(mocker, app, db_session):
    invalidate_credentials = Mock()
    mocker.patch("swpt_login.cli.invalidate_credentials", invalidate_credentials)

    db_session.add(
        m.UserRegistration(
            user_id="1234",
            email="user1234@example.com",
            salt="",
            password_hash="x",
            recovery_code_hash="y",
            status=0,
        )
    )
    db_session.add(
        m.UserRegistration(
            user_id="5678",
            email="user5678@example.com",
            salt="",
            password_hash="x",
            recovery_code_hash="y",
            status=0,
        )
    )
    db_session.commit()

    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "swpt_login",
            "suspend_user_registrations",
            "1234",  # exists
            "5678",  # exists
            "9999",  # do not exist
        ]
    )
    assert result.exit_code == 0
    users = m.UserRegistration.query.order_by(m.UserRegistration.user_id).all()
    assert len(users) == 2
    assert users[0].user_id == "1234"
    assert users[0].status == 1
    assert users[1].user_id == "5678"
    assert users[1].status == 1
    invalidate_credentials.assert_has_calls(
        [
            call("1234"),
            call("5678"),
        ]
    )

    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "swpt_login",
            "resume_user_registrations",
            "1234",  # exists
            "9999",  # do not exist
        ]
    )
    assert result.exit_code == 0
    users = m.UserRegistration.query.order_by(m.UserRegistration.user_id).all()
    assert len(users) == 2
    assert users[0].user_id == "1234"
    assert users[0].status == 0
    assert users[1].user_id == "5678"
    assert users[1].status == 1
