import logging
import re
import time
import hashlib
import base64
from sqlalchemy import select
from typing import Optional
from urllib.parse import urljoin
from sqlalchemy.exc import IntegrityError
from flask import current_app
from . import utils
from .models import UserRegistration, ActivateUserSignal
from .extensions import db, redis_store, requests_session

USER_ID_REGEX_PATTERN = re.compile(r"^[0-9A-Za-z_=-]{1,64}$")


def _query_recovery_code_hash(email):
    return db.session.execute(
        select(UserRegistration.recovery_code_hash)
        .where(UserRegistration.email == email),
        bind_arguments={"bind": db.engines["replica"]},
    ).scalar()


def _get_user_verification_code_failures_redis_key(user_id):
    return "vcfails:" + str(user_id)


def _reserve_user_id():
    api_resource_server = current_app.config["API_RESOURCE_SERVER"]
    api_reserve_user_id_path = current_app.config["API_RESERVE_USER_ID_PATH"]
    api_user_id_field_name = current_app.config["API_USER_ID_FIELD_NAME"]

    response = requests_session.post(
        url=urljoin(api_resource_server, f"{api_reserve_user_id_path}"),
        json={},
        verify=current_app.config["APP_VERIFY_SSL_CERTIFICATES"],
    )
    response.raise_for_status()
    response_json = response.json()
    user_id = str(response_json[api_user_id_field_name])
    if not USER_ID_REGEX_PATTERN.match(user_id):
        raise RuntimeError("Unvalid user ID.")
    reservation_id = response_json["reservationId"]

    return user_id, reservation_id


def _register_user_verification_code_failure(user_id):
    expiration_seconds = max(
        current_app.config["LOGIN_VERIFICATION_CODE_EXPIRATION_SECONDS"], 24 * 60 * 60
    )
    key = _get_user_verification_code_failures_redis_key(user_id)
    with redis_store.pipeline() as p:
        p.incrby(key)
        p.expire(key, expiration_seconds)
        num_failures = int(p.execute()[0] or "0")
    return num_failures


def _clear_user_verification_code_failures(user_id):
    redis_store.delete(_get_user_verification_code_failures_redis_key(user_id))


class UserLoginsHistory:
    """Contain identification codes from the last logins of a given user."""

    REDIS_PREFIX = "cc:"

    def __init__(self, user_id):
        self.max_count = current_app.config["LOGIN_VERIFIED_DEVICES_MAX_COUNT"]
        self.key = self.REDIS_PREFIX + str(user_id)
        self.expiration_seconds = (
            86400 * current_app.config["LOGIN_HISTORY_EXPIRATION_DAYS"]
        )

    @staticmethod
    def calc_hash(s: str) -> str:
        return base64.a85encode(
            hashlib.sha224(s.encode("ascii")).digest()
        ).decode("ascii")

    def contains(self, element):
        emement_hash = self.calc_hash(element)
        return emement_hash in redis_store.zrevrange(self.key, 0, self.max_count - 1)

    def add(self, element):
        emement_hash = self.calc_hash(element)
        with redis_store.pipeline() as p:
            p.zremrangebyrank(self.key, 0, -self.max_count)
            p.zadd(self.key, {emement_hash: time.time()})
            p.expire(self.key, self.expiration_seconds)
            p.execute()

    def clear(self):
        redis_store.delete(self.key)


class RedisSecretHashRecord:
    class ExceededMaxAttempts(Exception):
        """Too many failed attempts to enter the correct code."""

    @property
    def key(self):
        return self.REDIS_PREFIX + self.secret

    @classmethod
    def create(cls, _secret=None, **data):
        instance = cls()
        instance.secret = _secret or utils.generate_random_secret()
        instance._data = data
        with redis_store.pipeline() as p:
            p.hset(instance.key, mapping=data)
            p.expire(
                instance.key, current_app.config[cls.EXPIRATION_SECONDS_CONFIG_FIELD]
            )
            p.execute()
        return instance

    @classmethod
    def from_secret(cls, secret):
        instance = cls()
        instance.secret = secret
        instance._data = dict(
            zip(cls.ENTRIES, redis_store.hmget(instance.key, cls.ENTRIES))
        )
        return instance if instance._data.get(cls.ENTRIES[0]) is not None else None

    def delete(self):
        redis_store.delete(self.key)

    def __getattr__(self, name):
        return self._data[name]


def increment_key_with_limit(key, limit=None, period_seconds=1):
    if redis_store.ttl(key) < 0:
        redis_store.set(key, "1", ex=period_seconds)
        value = 1
    else:
        value = redis_store.incrby(key)
    if limit is not None and int(value) > limit:
        raise ExceededValueLimitError()
    return value


class ExceededValueLimitError(Exception):
    """The maximum value of a key has been exceeded."""


class LoginVerificationRequest(RedisSecretHashRecord):
    EXPIRATION_SECONDS_CONFIG_FIELD = "LOGIN_VERIFICATION_CODE_EXPIRATION_SECONDS"
    REDIS_PREFIX = "vcode:"
    ENTRIES = ["user_id", "code", "challenge_id", "email"]

    @classmethod
    def create(cls, **data):
        # We register a "code failure" after the creation of each
        # login verification request. This prevents maliciously
        # creating huge numbers of them.
        instance = super().create(**data)
        instance.register_code_failure()
        return instance

    def is_correct_recovery_code(self, recovery_code):
        normalized_recovery_code = utils.normalize_recovery_code(recovery_code)
        return _query_recovery_code_hash(self.email) == utils.calc_crypt_hash(
            "", normalized_recovery_code
        )

    def register_code_failure(self):
        num_failures = _register_user_verification_code_failure(self.user_id)
        if num_failures > current_app.config["SECRET_CODE_MAX_ATTEMPTS"]:
            self.delete()
            raise self.ExceededMaxAttempts()

    def accept(self):
        self.delete()


class SignUpRequest(RedisSecretHashRecord):
    EXPIRATION_SECONDS_CONFIG_FIELD = "SIGNUP_REQUEST_EXPIRATION_SECONDS"
    REDIS_PREFIX = "signup:"
    ENTRIES = ["email", "cc", "recover"]

    def is_correct_recovery_code(self, recovery_code):
        normalized_recovery_code = utils.normalize_recovery_code(recovery_code)
        return _query_recovery_code_hash(self.email) == utils.calc_crypt_hash(
            "", normalized_recovery_code
        )

    def register_code_failure(self):
        num_failures = int(redis_store.hincrby(self.key, "fails"))
        if num_failures >= current_app.config["SECRET_CODE_MAX_ATTEMPTS"]:
            self.delete()
            raise self.ExceededMaxAttempts()

    def accept(self, password: str, registered_from_ip: str = None) -> Optional[str]:
        self.delete()

        if self.recover:
            # Change the user's password.
            user = UserRegistration.query.filter_by(email=self.email).one()
            user.password_hash = utils.calc_crypt_hash(user.salt, password)

            # After changing the password, we "forget" past login
            # verification failures, thus guaranteeing that the user
            # will be able to log in immediately.
            _clear_user_verification_code_failures(user.user_id)

            db.session.commit()
            self.user_id = user.user_id
            return None

        else:
            # Reserve a user ID, which we need to activate.
            user_id, reservation_id = _reserve_user_id()

            # Before we try to activate the reserved user ID, we need
            # to make sure that a new row is added and committed to
            # the `activate_user_signal` table. This table is
            # periodically scanned for left-over rows, so that if the
            # immediate activation attempt fails, activation attempts
            # will continue automatically.
            recovery_code = utils.generate_recovery_code()
            salt = utils.generate_password_salt()
            db.session.add(
                ActivateUserSignal(
                    user_id=user_id,
                    reservation_id=reservation_id,
                    email=self.email,
                    salt=salt,
                    password_hash=utils.calc_crypt_hash(salt, password),
                    recovery_code_hash=utils.calc_crypt_hash("", recovery_code),
                    registered_from_ip=registered_from_ip,
                )
            )
            db.session.commit()

            # Try to immediately activate the user.
            if activate_user_signal := (
                ActivateUserSignal.query
                .filter_by(user_id=user_id, reservation_id=reservation_id)
                .with_for_update(skip_locked=True)
                .one_or_none()
            ):
                try:
                    activate_user_signal.send_signalbus_message()
                    db.session.delete(activate_user_signal)
                except activate_user_signal.SendingError:
                    logger = logging.getLogger(__name__)
                    logger.error(
                        "SendingError occurred while trying to activate a"
                        " user registration: user ID %s, reservation ID %s.",
                        user_id,
                        reservation_id,
                    )

            db.session.commit()
            self.user_id = user_id
            return recovery_code


class ChangeEmailRequest(RedisSecretHashRecord):
    EXPIRATION_SECONDS_CONFIG_FIELD = "CHANGE_EMAIL_REQUEST_EXPIRATION_SECONDS"
    REDIS_PREFIX = "setemail:"
    ENTRIES = ["email", "old_email", "user_id"]

    class EmailAlredyRegistered(Exception):
        """The new email is already registered."""

    def accept(self):
        self.delete()
        user_id = self.user_id
        user = UserRegistration.query.filter_by(
            user_id=user_id, email=self.old_email
        ).one()
        user.email = self.email

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise self.EmailAlredyRegistered()

        # After changing the email address, we "forget" past login
        # verification failures, thus guaranteeing that the user will
        # be able to log in immediately.
        _clear_user_verification_code_failures(user.user_id)


class ChangeRecoveryCodeRequest(RedisSecretHashRecord):
    EXPIRATION_SECONDS_CONFIG_FIELD = "CHANGE_RECOVERY_CODE_REQUEST_EXPIRATION_SECONDS"
    REDIS_PREFIX = "changerc:"
    ENTRIES = ["email"]

    def accept(self) -> str:
        self.delete()
        recovery_code = utils.generate_recovery_code()
        user = UserRegistration.query.filter_by(email=self.email).one()
        user.recovery_code_hash = utils.calc_crypt_hash("", recovery_code)
        db.session.commit()
        return recovery_code
