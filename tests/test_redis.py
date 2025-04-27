import pytest
import base64
from typing import Callable
from dataclasses import dataclass
from unittest.mock import Mock, call
from swpt_login import redis
from swpt_login import utils
from swpt_login import models as m


USER_ID = '1234'
USER_EMAIL = "test@example.com"
USER_SALT = utils.generate_password_salt()
USER_PASSWORD = "qwerty"
USER_RECOVERY_CODE = utils.generate_recovery_code()


@pytest.fixture(params=[200, 500])
def acitivation_status_code(request):
    return request.param


@pytest.fixture
def user(db_session):
    redis.UserLoginsHistory(USER_ID).clear()
    redis._clear_user_verification_code_failures(USER_ID)
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
    # Simulate the "enter your email" screen:
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
    # Simulate the "enter your email" screen:
    #
    computer_code = utils.generate_random_secret()
    computer_code_hash = utils.calc_sha256(computer_code)
    user = m.UserRegistration.query.filter_by(email=USER_EMAIL).one()

    r1 = redis.SignUpRequest.create(
        email=USER_EMAIL,
        cc=computer_code_hash,
        recover='yes',
        has_rc='yes',
    )

    # Simulate the choose password screen:
    #
    r2 = redis.SignUpRequest.from_secret(r1.secret)
    for _ in range(4):
        r2.register_code_failure()
        r2 = redis.SignUpRequest.from_secret(r1.secret)
        assert r2 is not None

    # We have configured SECRET_CODE_MAX_ATTEMPTS = 5, and this is the
    # 5th failed attempt.
    with pytest.raises(redis.SignUpRequest.ExceededMaxAttempts):
        r2.register_code_failure()
    assert redis.SignUpRequest.from_secret(r1.secret) is None


def test_login_flow(app, db_session, user):
    # Simulate successfully entering user's email and password:
    #
    challenge_id = '45678'

    computer_code = utils.generate_random_secret()
    computer_code_hash = utils.calc_sha256(computer_code)
    user_logins_history = redis.UserLoginsHistory(USER_ID)
    assert not user_logins_history.contains(computer_code_hash)

    verification_code = utils.generate_verification_code()
    verification_cookie = utils.generate_random_secret()
    verification_cookie_hash = utils.calc_sha256(verification_cookie)

    redis.LoginVerificationRequest.create(
        _secret=verification_cookie_hash,
        user_id=USER_ID,
        email=USER_EMAIL,
        code=verification_code,
        remember_me='no',
        challenge_id=challenge_id,
    )

    # Simulate entering the verification code:
    #
    lvr = redis.LoginVerificationRequest.from_secret(verification_cookie_hash)
    assert lvr.user_id == USER_ID
    assert lvr.email == USER_EMAIL
    assert lvr.code == verification_code
    assert lvr.remember_me == 'no'
    assert lvr.challenge_id == challenge_id
    lvr.register_code_failure()

    lvr.accept()
    redis.UserLoginsHistory(USER_ID).add(computer_code_hash)
    assert user_logins_history.contains(computer_code_hash)


def test_login_flow_failure(app, db_session, user):
    # Simulate successfully entering user's email and password:
    #
    challenge_id = '45678'
    verification_code = utils.generate_verification_code()
    verification_cookie = utils.generate_random_secret()
    verification_cookie_hash = utils.calc_sha256(verification_cookie)

    redis.LoginVerificationRequest.create(
        _secret=verification_cookie_hash,
        user_id=USER_ID,
        email=USER_EMAIL,
        code=verification_code,
        remember_me='no',
        challenge_id=challenge_id,
    )

    # Simulate entering the verification code:
    #
    lvr = redis.LoginVerificationRequest.from_secret(verification_cookie_hash)
    for _ in range(4):
        lvr.register_code_failure()
        lvr = redis.LoginVerificationRequest.from_secret(verification_cookie_hash)
        assert lvr is not None

    with pytest.raises(lvr.ExceededMaxAttempts):
        lvr.register_code_failure()
    assert redis.LoginVerificationRequest.from_secret(verification_cookie_hash) is None


def test_change_email_flow(app, db_session, user):
    # Simulate successfully entering user's old email and password:
    #
    challenge_id = '45678'

    lvr1 = redis.LoginVerificationRequest.create(
        user_id=USER_ID,
        email=USER_EMAIL,
        challenge_id=challenge_id,
    )

    # Simulate the "choose new email" dialog:
    #
    assert redis.LoginVerificationRequest.from_secret('wrong_secret') is None

    lvr2 = redis.LoginVerificationRequest.from_secret(lvr1.secret)
    assert lvr2 is not None
    assert not lvr2.is_correct_recovery_code(utils.generate_recovery_code())

    new_email = "new-email@example.com"
    assert lvr2.is_correct_recovery_code(USER_RECOVERY_CODE)
    lvr2.accept()
    assert redis.LoginVerificationRequest.from_secret(lvr1.secret) is None

    cer = redis.ChangeEmailRequest.create(
        user_id=USER_ID,
        email=new_email,
        old_email=USER_EMAIL,
    )

    # Simulate the "change email_address" password assertion dialog:
    #
    assert redis.ChangeEmailRequest.from_secret("wrong_secret") is None

    cer2 = redis.ChangeEmailRequest.from_secret(cer.secret)
    assert cer2 is not None
    cer2.accept()
    assert redis.ChangeEmailRequest.from_secret(cer.secret) is None
    assert m.UserRegistration.query.filter_by(user_id=USER_ID, email=new_email).one_or_none()


def test_change_email_flow_failure(app, db_session, user):
    new_email = "new-email@example.com"
    salt = utils.generate_password_salt()
    db_session.add(
        m.UserRegistration(
            user_id="567890",
            email=new_email,
            salt=salt,
            password_hash=utils.calc_crypt_hash(salt, 'some password'),
            recovery_code_hash=utils.calc_crypt_hash('', utils.generate_recovery_code()),
            two_factor_login=True,
        )
    )
    db_session.commit()

    # Simulate successfully entering user's old email and password:
    #
    challenge_id = '45678'

    lvr1 = redis.LoginVerificationRequest.create(
        user_id=USER_ID,
        email=USER_EMAIL,
        challenge_id=challenge_id,
    )

    # Simulate the "choose new email" dialog:
    #
    lvr2 = redis.LoginVerificationRequest.from_secret(lvr1.secret)
    lvr2.accept()

    cer = redis.ChangeEmailRequest.create(
        user_id=USER_ID,
        email=new_email,
        old_email=USER_EMAIL,
    )

    # Simulate the "change email_address" password assertion dialog:
    #
    cer2 = redis.ChangeEmailRequest.from_secret(cer.secret)
    with pytest.raises(cer2.EmailAlredyRegistered):
        cer2.accept()
    assert m.UserRegistration.query.filter_by(user_id=USER_ID, email=USER_EMAIL).one_or_none()


def test_change_recovery_code_flow(app, db_session, user):
    # Simulate the "change recovery code" dialog:
    #
    crcr1 = redis.ChangeRecoveryCodeRequest.create(email=USER_EMAIL)

    # Simulate the "generate recovery code" page:
    #
    assert redis.ChangeRecoveryCodeRequest.from_secret("wrong_secret") is None

    crcr2 = redis.ChangeRecoveryCodeRequest.from_secret(crcr1.secret)
    new_recovery_code = crcr2.accept()
    assert redis.ChangeRecoveryCodeRequest.from_secret(crcr1.secret) is None
    assert m.UserRegistration.query.filter_by(
        user_id=USER_ID,
        recovery_code_hash=utils.calc_crypt_hash('', new_recovery_code),
    ).one_or_none()


def test_increment_key_with_limit(app):
    key = utils.generate_random_secret()
    assert redis.increment_key_with_limit(
        key, limit=3, period_seconds=1000000
    ) == 1
    assert redis.increment_key_with_limit(
        key, limit=3, period_seconds=1000000
    ) == 2
    assert redis.increment_key_with_limit(
        key, limit=3, period_seconds=1000000
    ) == 3

    with pytest.raises(redis.ExceededValueLimitError):
        redis.increment_key_with_limit(key, limit=3, period_seconds=1000000)


def test_user_logins_history(app):
    ulh = redis.UserLoginsHistory(USER_ID)
    assert not ulh.contains('1')
    assert not ulh.contains('2')
    ulh.add('1')
    assert ulh.contains('1')
    assert not ulh.contains('2')

    ulh.add('2')
    ulh.add('3')
    assert ulh.contains('1')
    assert ulh.contains('2')
    assert ulh.contains('3')
    assert not ulh.contains('4')

    ulh.add('4')
    assert not ulh.contains('1')
    assert ulh.contains('2')
    assert ulh.contains('3')
    assert ulh.contains('4')

    ulh.add('5')
    assert not ulh.contains('1')
    assert not ulh.contains('2')
    assert ulh.contains('3')
    assert ulh.contains('4')
    assert ulh.contains('5')

    ulh.clear()
    assert not ulh.contains('1')
    assert not ulh.contains('2')
    assert not ulh.contains('3')
    assert not ulh.contains('4')
    assert not ulh.contains('5')
