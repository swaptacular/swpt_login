import pytest
import base64
from typing import Callable
from dataclasses import dataclass
from unittest.mock import Mock, call
from swpt_login import redis
from swpt_login import utils
from swpt_login import models as m


USER_EMAIL = "test@example.com"
USER_SALT = utils.generate_password_salt()
USER_PASSWORD = "qwerty "
USER_RECOVERY_CODE = utils.generate_recovery_code()


@pytest.fixture(params=[200, 500])
def acitivation_status_code(request):
    return request.param


@pytest.fixture
def user(db_session):
    db_session.add(
        m.UserRegistration(
            user_id="1234",
            email="test@example.com",
            salt=USER_SALT,
            password_hash=utils.calc_crypt_hash(USER_SALT, USER_PASSWORD),
            recovery_code_hash=utils.calc_crypt_hash('', USER_RECOVERY_CODE),
            two_factor_login=True,
        )
    )
    db_session.commit()


@dataclass
class Response:
    status_code: int
    json: Callable = lambda: {}
    raise_for_status = Mock()


def test_signup_flow(mocker, app, db_session, acitivation_status_code):
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

    reservation_session = ReservationMock()
    activation_session = ActivationMock()
    mocker.patch("swpt_login.redis.requests_session", reservation_session)
    mocker.patch("swpt_login.models.requests_session", activation_session)

    # Simulate the initial sign-up screen:
    #
    email = 'email@example.com'
    computer_code = utils.generate_random_secret()
    computer_code_hash = utils.calc_sha256(computer_code)
    r1 = redis.SignUpRequest.create(
        email=email,
        cc=computer_code_hash,
    )

    # Simulate the choose passwoerd screen:
    #
    password = '12345678+abcdefgh'
    assert isinstance(r1.secret, str)
    assert redis.SignUpRequest.from_secret('wrong_secret') is None

    r2 = redis.SignUpRequest.from_secret(r1.secret)
    assert r2 is not None
    assert r2.recover != 'yes'
    assert r2.has_rc != 'yes'

    recovery_code = r2.accept(password)
    assert (
        len(base64.b32decode(recovery_code))
        == len(base64.b32decode(utils.generate_recovery_code()))
    )
    assert r2.user_id == '1234'

    reservation_session.post.assert_has_calls([
        call(
            url='https://resource-server.example.com/debtors/.debtor-reserve',
            json={},
            verify=False,
        ),
    ])
    activation_session.post.assert_has_calls([
        call(
            url='https://resource-server.example.com/debtors/1234/activate',
            json={'reservationId': '456'},
            verify=False,
        ),
    ])

    if acitivation_status_code == 200:
        # Successful activation.
        assert len(m.RegisteredUserSignal.query.all()) == 0
    else:
        # Failed activations create an RegisteredUserSignal.
        users = m.RegisteredUserSignal.query.all()
        assert len(users) == 1
        assert users[0].user_id == '1234'
        assert users[0].reservation_id == '456'


def test_password_recovery_flow(app, db_session, user):
    # Simulate "enter your email" screen:
    #
    computer_code = utils.generate_random_secret()
    computer_code_hash = utils.calc_sha256(computer_code)
    user = m.UserRegistration.query.filter_by(email=USER_EMAIL).one()
    assert user.recovery_code_hash

    r1 = redis.SignUpRequest.create(
        email=USER_EMAIL,
        cc=computer_code_hash,
        recover='yes',
        has_rc='yes',
    )

    # Simulate the choose password screen:
    #
    r2 = redis.SignUpRequest.from_secret(r1.secret)
    assert r2 is not None
    assert r2.recover == 'yes'
    assert r2.has_rc == 'yes'

    assert not r2.is_correct_recovery_code('wrong_recovery_code')
    r2.register_code_failure()

    assert r2.is_correct_recovery_code(USER_RECOVERY_CODE)
    new_password = '12345678+abcdefgh'
    r2.accept(new_password)

    user = m.UserRegistration.query.filter_by(email=USER_EMAIL).one()
    assert user.password_hash == utils.calc_crypt_hash(user.salt, new_password)


def test_password_recovery_flow_failure(app, db_session, user):
    # Simulate "enter your email" screen:
    #
    computer_code = utils.generate_random_secret()
    computer_code_hash = utils.calc_sha256(computer_code)
    user = m.UserRegistration.query.filter_by(email=USER_EMAIL).one()
    assert user.recovery_code_hash

    r1 = redis.SignUpRequest.create(
        email=USER_EMAIL,
        cc=computer_code_hash,
        recover='yes',
        has_rc='yes',
    )

    # Simulate the choose password screen:
    #
    r2 = redis.SignUpRequest.from_secret(r1.secret)
    assert r2 is not None
    assert r2.recover == 'yes'
    assert r2.has_rc == 'yes'

    for _ in range(4):
        r2.register_code_failure()
        r2 = redis.SignUpRequest.from_secret(r1.secret)
        assert r2 is not None

    # We have configured SECRET_CODE_MAX_ATTEMPTS = 5, and this is the
    # 5th failed attempt.
    with pytest.raises(redis.SignUpRequest.ExceededMaxAttempts):
        r2.register_code_failure()
    assert redis.SignUpRequest.from_secret(r1.secret) is None
