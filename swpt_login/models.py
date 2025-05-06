import logging
import requests
from datetime import datetime, timezone
from urllib.parse import urljoin
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import INET
from flask import current_app
from .extensions import db, requests_session


def get_now_utc():
    return datetime.now(tz=timezone.utc)


def _get_api_base_url() -> str:
    api_resource_server = current_app.config["API_RESOURCE_SERVER"]
    api_reserve_user_id_path = current_app.config["API_RESERVE_USER_ID_PATH"]
    api_base_path = api_reserve_user_id_path.split(".")[0]
    return urljoin(api_resource_server, api_base_path)


class classproperty(object):
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)


class UserRegistration(db.Model):
    email = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.String(64), nullable=False)
    salt = db.Column(db.String(32), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    recovery_code_hash = db.Column(db.String(128), nullable=False)
    registered_from_ip = db.Column(INET)
    registered_at = db.Column(
        db.TIMESTAMP(timezone=True), nullable=False, default=get_now_utc,
    )

    __table_args__ = (
        # NOTE: This index is not used in queries, and serves only as
        # as a database constraint. Therefore, if for example, one
        # wants to split the `user_registration` table to several
        # shards (based on the email's hash), this index can be safely
        # removed.
        #
        # However, this index can catch nasty problems. For examle,
        # imagine the case when the user's API object (a debtor or a
        # creditor) has been removed from the system by an admin, but
        # the admin forgot to remove the user's `UserRegistration` row
        # from the login database. Then, when a new user comes and
        # tries to register, and the user ID of the removed user (for
        # which there is still a `UserRegistration` row) is unluckily
        # chosen to be the new user's user ID -- BAM!!!. The result is
        # that two different user credentials (email plus password)
        # would be referencing the same user API object (a debtor or a
        # creditor). The simplest way to avoid this problem is for the
        # admin to not remove user's API objects (debtors/creditors)
        # without removing their corresponding `UserRegistration` rows
        # from the login database.
        db.Index("idx_user_registration_user_id", user_id, unique=True),
        {
            "comment": (
                'Represents a registered user. The columns "salt", '
                '"password_hash", and "recovery_code_hash" are Base64 '
                'encoded. The "salt" column contains the salt used for the '
                'password hash. Salt\'s value may *optionally* have a '
                '"$hashing_method$" prefix, which determines the '
                'hashing method. The salt IS NOT used when calculating the '
                '"recovery_code_hash". The "recovery_code_hash" is always '
                'calculated using the default hashing method (Scrypt N=128, '
                'r=8, p=1, dklen=32), and an empty string as salt.'
            ),
        },
    )


class ActivateUserSignal(db.Model):
    class SendingError(Exception):
        """Failed activation request."""

    user_id = db.Column(db.String(64), primary_key=True)
    reservation_id = db.Column(db.String(100), primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    salt = db.Column(db.String(32), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    recovery_code_hash = db.Column(db.String(128), nullable=False)
    registered_from_ip = db.Column(INET)
    inserted_at = db.Column(
        db.TIMESTAMP(timezone=True), nullable=False, default=get_now_utc
    )

    @classproperty
    def signalbus_burst_count(self):
        return current_app.config["APP_FLUSH_ACTIVATE_USERS_BURST_COUNT"]

    def send_signalbus_message(self):
        """Activate the user reservation, then add a `UserRegistration` row."""

        try:
            response = requests_session.post(
                url=urljoin(_get_api_base_url(), f"{self.user_id}/activate"),
                json={"reservationId": self.reservation_id},
                verify=current_app.config["APP_VERIFY_SSL_CERTIFICATES"],
            )
            status_code = response.status_code

            if status_code == 200:
                user_query = UserRegistration.query.filter_by(email=self.email)
                if not db.session.query(user_query.exists()).scalar():
                    db.session.add(
                        UserRegistration(
                            email=self.email,
                            user_id=self.user_id,
                            salt=self.salt,
                            password_hash=self.password_hash,
                            recovery_code_hash=self.recovery_code_hash,
                            registered_from_ip=self.registered_from_ip,
                            registered_at=self.inserted_at,
                        )
                    )
                    try:
                        db.session.flush()
                    except IntegrityError:
                        raise RuntimeError(
                            "Duplicated email or user ID. This may happen if"
                            " a user has attempted to sign up more than once"
                            " simultaneously, with the same email address"
                            " (duplicated email). In this case, this error is"
                            " a single rare event which does not cause any"
                            " problems. However, this error also occurs when"
                            " an already existing user ID is assigned to a new"
                            " user, which signals that a serious database"
                            " inconsistency has been prevented. If this is"
                            " the case, this error  will continue to show up,"
                            " again and again."
                        )

            elif status_code == 409 or status_code == 422:
                # This should be very rare, and not a big problem. In
                # this case there is nothing we can do, except logging
                # the event.
                logger = logging.getLogger(__name__)
                logger.error(
                    "Reservation %s has expired. As a result, the"
                    " registration of the new user failed",
                    self.reservation_id,
                )

            else:
                raise self.SendingError(
                    f"Unexpected status code ({status_code}) while trying to"
                    " activate an user."
                )

        except (requests.ConnectionError, requests.Timeout):
            raise self.SendingError("connection problem")


class DeactivateUserSignal(db.Model):
    class SendingError(Exception):
        """Failed deactivation request."""

    user_id = db.Column(db.String(64), primary_key=True)
    inserted_at = db.Column(
        db.TIMESTAMP(timezone=True), nullable=False, default=get_now_utc
    )

    @classproperty
    def signalbus_burst_count(self):
        return current_app.config["APP_FLUSH_DEACTIVATE_USERS_BURST_COUNT"]

    def send_signalbus_message(self):
        """Deactivate the user reservation."""

        try:
            response = requests_session.post(
                url=urljoin(_get_api_base_url(), f"{self.user_id}/deactivate"),
                json={"type": current_app.config["API_DACTIVATION_REQUEST_TYPE"]},
                verify=current_app.config["APP_VERIFY_SSL_CERTIFICATES"],
            )
            status_code = response.status_code
            if status_code != 204:
                raise self.SendingError(
                    f"Unexpected status code ({status_code}) while trying to"
                    " deactivate an user."
                )
        except (requests.ConnectionError, requests.Timeout):
            raise self.SendingError("connection problem")
