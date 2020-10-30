import threading
import requests
from werkzeug.local import Local
from flask import current_app
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient

_local = Local()


class CreditorsAPIAdapter(HTTPAdapter):
    __access_token = None
    __access_token_lock = threading.Lock()

    def send(self, request, *args, **kw):
        while True:
            access_token, is_new_access_token = self.__get_access_token()
            request.headers['Authorization'] = f'Bearer {access_token}'
            response = super().send(request, *args, **kw)

            # If unauthorized, try to get a new access token.
            if response.status_code == 401:
                self.__invalidate_access_token(access_token)
                if not is_new_access_token:
                    continue

            return response

    @classmethod
    def __get_access_token(cls):
        access_token = cls.__access_token
        is_new_access_token = False

        if access_token is None:
            with cls.__access_token_lock:
                access_token = cls.__access_token
                if access_token is None:
                    token_info = cls.__obtain_new_access_token()
                    access_token = cls.__access_token = token_info['access_token']
                    is_new_access_token = True

        return access_token, is_new_access_token

    @classmethod
    def __obtain_new_access_token(cls):
        client_id = current_app.config['SUPERVISOR_CLIENT_ID']
        client_secret = current_app.config['SUPERVISOR_CLIENT_SECRET']
        token_url = current_app.config['API_AUTH2_TOKEN_URL']

        auth = HTTPBasicAuth(client_id, client_secret)
        client = BackendApplicationClient(client_id=client_id)
        oauth = OAuth2Session(client=client)
        token = oauth.fetch_token(token_url=token_url, auth=auth, scope=['activate'])

        return token

    @classmethod
    def __invalidate_access_token(cls, access_token):
        if cls.__access_token == access_token:
            with cls.__access_token_lock:
                if cls.__access_token == access_token:
                    cls.__access_token = None


def create_requests_session():
    creditors_resource_server = current_app.config['API_RESOURCE_SERVER']
    session = requests.Session()
    session.timeout = float(current_app.config['API_TIMEOUT_SECONDS'])
    session.mount(creditors_resource_server, CreditorsAPIAdapter())

    return session


def get_requests_session():
    if not hasattr(_local, 'requests_session'):
        _local.requests_session = create_requests_session()

    return _local.requests_session
