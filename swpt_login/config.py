import json
from os import environ

SUPPORTED_LANGUAGES = {"en": "English", "bg": "Български"}


def _get_language_choices(fallback):
    languages = environ.get("LANGUAGES", fallback)
    languages = [lg.strip() for lg in languages.split(",")]
    return [
        (lg, SUPPORTED_LANGUAGES[lg]) for lg in languages if lg in SUPPORTED_LANGUAGES
    ]


def _parse_dict(s: str) -> dict:
    try:
        return json.loads(s)
    except ValueError:
        raise ValueError(f"Invalid JSON configuration value: {s}")


class MetaEnvReader(type):
    def __init__(cls, name, bases, dct):
        """MetaEnvReader class initializer.

        This function will get called when a new class which utilizes
        this metaclass is defined, as opposed to when an instance is
        initialized. This function overrides the default configuration
        from environment variables.

        """

        super().__init__(name, bases, dct)
        NoneType = type(None)
        annotations = dct.get("__annotations__", {})
        falsy_values = {"false", "off", "no", ""}
        for key, value in environ.items():
            if hasattr(cls, key):
                target_type = annotations.get(key) or type(getattr(cls, key))
                if target_type is NoneType:
                    target_type = str

                if target_type is bool:
                    value = value.lower() not in falsy_values
                else:
                    value = target_type(value)

                setattr(cls, key, value)


class Configuration(metaclass=MetaEnvReader):
    VERSION = "0.9.5"

    SQLALCHEMY_DATABASE_URI = ""
    SQLALCHEMY_ENGINE_OPTIONS: _parse_dict = _parse_dict('{"pool_size": 0}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    REPLICA_POSTGRES_URL = ""

    SECRET_KEY = "dummy-secret"
    SITE_TITLE = "Login Test Site"
    LANGUAGES = "en"  # separated by a comma, for example 'en,bg'
    SUBJECT_PREFIX = ""
    ABOUT_URL = "https://swaptacular.github.io/overview"
    STYLE_URL = ""
    LOGIN_PATH = "/login"
    CONSENT_PATH = "/consent"
    HYDRA_ADMIN_URL = "http://hydra:4445/"

    REDIS_URL = "redis://localhost:6379/0"
    REDIS_CLUSTER_URL = ""

    MAIL_SERVER = "localhost"
    MAIL_PORT = 25
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    MAIL_USERNAME: str = None
    MAIL_PASSWORD: str = None
    MAIL_DEFAULT_SENDER: str = None
    MAIL_MAX_EMAILS: int = None
    MAIL_ASCII_ATTACHMENTS = False
    RECAPTCHA_PUBLIC_KEY = "6Ledx7wSAAAAAICFw8vB-2ghpDjzGogPRi6-3FCr"
    RECAPTCHA_PIVATE_KEY = "6Ledx7wSAAAAAEskQ7Mbi-oqneHDSFVUkxGitn_y"
    RECAPTCHA_REQUEST_TIMEOUT_SECONDS = 5

    RECAPTCHA_CHALLENGE_URL = "https://www.google.com/recaptcha/api.js"
    RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
    APP_SIGNUP_REDIRECT_URL = ""
    HYDRA_REQUEST_TIMEOUT_SECONDS = 5
    SHOW_CAPTCHA_ON_SIGNUP = True
    SIGNUP_IP_BLOCK_SECONDS = 2 * 60 * 60
    SIGNUP_IP_MAX_REGISTRATIONS = 15
    CAPTCHA_RESPONSE_FIELD_NAME = "g-recaptcha-response"
    LOGIN_VERIFIED_DEVICES_MAX_COUNT = 10
    LOGIN_VERIFICATION_CODE_EXPIRATION_SECONDS = 60 * 60
    MAX_LOGINS_PER_MONTH = 10000
    SECRET_CODE_MAX_ATTEMPTS = 10
    SIGNUP_REQUEST_EXPIRATION_SECONDS = 24 * 60 * 60
    CHANGE_EMAIL_REQUEST_EXPIRATION_SECONDS = 24 * 60 * 60
    CHANGE_RECOVERY_CODE_REQUEST_EXPIRATION_SECONDS = 60 * 60
    LANGUAGE_COOKIE_NAME = "user_lang"
    COMPUTER_CODE_COOKIE_NAME = "user_cc"
    LOGIN_VERIFICATION_COOKIE_NAME = "user_lv"
    PASSWORD_MIN_LENGTH = 12
    PASSWORD_MAX_LENGTH = 64
    SEND_FILE_MAX_AGE_DEFAULT = 12096000
    MAX_CONTENT_LENGTH = 4096
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    BABEL_DEFAULT_LOCALE = "en"
    BABEL_DEFAULT_TIMEZONE = "UTC"
    LANGUAGE_CHOICES = _get_language_choices(LANGUAGES)
    FLUSH_PROCESSES = 1
    FLUSH_PERIOD = 2.0

    SUPERUSER_CLIENT_ID = "users-superuser"
    SUPERUSER_CLIENT_SECRET = "users-superuser"
    API_AUTH2_TOKEN_URL = "https://hydra/oauth2/token"
    API_RESOURCE_SERVER = "https://resource-server"
    API_RESERVE_USER_ID_PATH = "/users/.user-reserve"
    API_USER_ID_FIELD_NAME = "userId"
    API_TIMEOUT_SECONDS = 5

    APP_FLUSH_ACTIVATE_USERS_BURST_COUNT = 5
    APP_FLUSH_DEACTIVATE_USERS_BURST_COUNT = 5
    APP_VERIFY_SSL_CERTIFICATES = True
