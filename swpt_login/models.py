from urllib.parse import urljoin
from flask import current_app
from .extensions import db, requests_session


class UserRegistration(db.Model):
    user_id = db.Column(db.String(64), primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)

    # NOTE: The columns "salt", "password_hash", and
    # "recovery_code_hash" are Base64 encoded. The "salt" column
    # contains the salt used for the password hash. Salt's value may
    # optionally have a "$hashing_method$" prefix, which determines
    # the hashing method. The salt IS NOT used when calculating the
    # "recovery_code_hash". The "recovery_code_hash" is always
    # calculated using the default hashing method (Scrypt N=128, r=8,
    # p=1, dklen=32), and an empty string as salt.
    #
    salt = db.Column(db.String(32), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    recovery_code_hash = db.Column(db.String(128), nullable=True)

    two_factor_login = db.Column(db.Boolean, nullable=False)


class UserUpdateSignal(db.Model):
    user_id = db.Column(db.String(64), primary_key=True)
    user_update_signal_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=True)

    def send_signalbus_message(self):  # pragma: nocover
        """Inform the other services that user's email has changed.
        """
        pass


class RegisteredUserSignal(db.Model):
    user_id = db.Column(db.String(64), primary_key=True)
    registered_user_signal_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    reservation_id = db.Column(db.String(255), nullable=False)

    def send_signalbus_message(self):
        api_resource_server = current_app.config['API_RESOURCE_SERVER']
        api_reserve_user_id_path = current_app.config['API_RESERVE_USER_ID_PATH']
        api_base_path = api_reserve_user_id_path.split('.')[0]
        response = requests_session.post(
            url=urljoin(api_resource_server, f'{api_base_path}{self.user_id}/activate'),
            json={'reservationId': self.reservation_id},
            verify=False,
        )
        status_code = response.status_code
        if status_code not in [200, 409, 422]:
            raise RuntimeError(f'Unexpected status code ({status_code}) while trying to activate a user.')
