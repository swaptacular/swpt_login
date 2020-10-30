from flask import current_app
from swpt_lib.utils import i64_to_u64
from .extensions import db, requests_session


class User(db.Model):
    user_id = db.Column(db.BigInteger, primary_key=True, autoincrement=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    salt = db.Column(db.String(32), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    recovery_code_hash = db.Column(db.String(128), nullable=True)
    two_factor_login = db.Column(db.Boolean, nullable=False)


class UserUpdateSignal(db.Model):
    user_update_signal_id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, nullable=False)
    email = db.Column(db.String(255), nullable=True)

    def send_signalbus_message(self):
        """Inform the other services that user's email has changed."""

        ##############################################
        # Send a message over your message bus here! #
        ##############################################


class RegisteredUserSignal(db.Model):
    registered_user_signal_id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, nullable=False)
    reservation_id = db.Column(db.BigInteger, nullable=False)

    def send_signalbus_message(self):
        api_resource_server = current_app.config['API_RESOURCE_SERVER']
        api_reserve_user_id_path = current_app.config['API_RESERVE_USER_ID_PATH']
        api_base_path = api_reserve_user_id_path.split('.')[0]
        response = requests_session.post(
            url=f'{api_resource_server}{api_base_path}{i64_to_u64(self.user_id)}/activate',
            json={'reservationId': self.reservation_id},
        )
        status_code = response.status_code
        if status_code not in [200, 409, 422]:
            raise RuntimeError(f'Unexpected status code ({status_code}) while trying to activate a user.')
