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
    assert len(m.RegisteredUserSignal.query.all()) == 0
    db.session.execute(
         sqlalchemy.text(
             "INSERT INTO registered_user_signal (user_id, reservation_id) "
             "VALUES ('123', '456')"
         )
    )
    db.session.commit()
    assert len(m.RegisteredUserSignal.query.all()) == 1
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
        json={'reservationId': '456'},
        url='https://resource-server.example.com/debtors/123/activate',
        verify=False,
    )
    assert len(m.RegisteredUserSignal.query.all()) == 0

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
    assert len(m.RegisteredUserSignal.query.all()) == 0


def test_flush_messages_failure(mocker, app, db_session):
    class RequestSessionMock:
        post = Mock(return_value=Response(500))

    requests_session = RequestSessionMock()
    mocker.patch("swpt_login.models.requests_session", requests_session)
    assert len(m.RegisteredUserSignal.query.all()) == 0
    db.session.execute(
         sqlalchemy.text(
             "INSERT INTO registered_user_signal (user_id, reservation_id) "
             "VALUES ('123', '456')"
         )
    )
    db.session.commit()
    assert len(m.RegisteredUserSignal.query.all()) == 1
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
    assert len(m.RegisteredUserSignal.query.all()) == 1
