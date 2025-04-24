from os import environ

SUPPORTED_LANGUAGES = {'en': 'English', 'bg': 'Български'}


def _get_language_choices(fallback):
    languages = environ.get('LANGUAGES', fallback)
    languages = [lg.strip() for lg in languages.split(',')]
    return [(lg, SUPPORTED_LANGUAGES[lg]) for lg in languages if lg in SUPPORTED_LANGUAGES]


def _get_default_password_min_length(fallback):
    return 12 if environ.get('USE_RECOVERY_CODE', str(bool(fallback))).lower() == 'true' else 6


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
        annotations = dct.get('__annotations__', {})
        falsy_values = {'false', 'off', 'no', ''}
        for key, value in environ.items():
            if hasattr(cls, key):
                target_type = annotations.get(key) or type(getattr(cls, key))
                if target_type is NoneType:  # pragma: no cover
                    target_type = str

                if target_type is bool:
                    value = value.lower() not in falsy_values
                else:
                    value = target_type(value)

                setattr(cls, key, value)


class Configuration(metaclass=MetaEnvReader):
    VERSION = '0.9.5'

    SECRET_KEY = 'dummy-secret'
    SITE_TITLE = 'Login Test Site'
    LANGUAGES = 'en'  # separated by a comma, for example 'en,bg'
    USE_RECOVERY_CODE = True
    SUBJECT_PREFIX = ''
    ABOUT_URL = 'https://swaptacular.github.io/overview'
    STYLE_URL = ''
    LOGIN_PATH = '/login'
    CONSENT_PATH = '/consent'
    HYDRA_ADMIN_URL = 'http://hydra:4445/'
    REDIS_URL = 'redis://localhost:6379/0'
    SQLALCHEMY_DATABASE_URI = ''
    SQLALCHEMY_POOL_SIZE: int = None
    SQLALCHEMY_POOL_TIMEOUT: int = None
    SQLALCHEMY_POOL_RECYCLE: int = None
    SQLALCHEMY_MAX_OVERFLOW: int = None
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 25
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    MAIL_USERNAME: str = None
    MAIL_PASSWORD: str = None
    MAIL_DEFAULT_SENDER: str = None
    MAIL_MAX_EMAILS: int = None
    MAIL_ASCII_ATTACHMENTS = False
    RECAPTCHA_PUBLIC_KEY = '6Lc902MUAAAAAJL22lcbpY3fvg3j4LSERDDQYe37'
    RECAPTCHA_PIVATE_KEY = '6Lc902MUAAAAAN--r4vUr8Vr7MU1PF16D9k2Ds9Q'
    RECAPTCHA_REQUEST_TIMEOUT_SECONDS = 5

    RECAPTCHA_CHALLENGE_URL = 'https://www.google.com/recaptcha/api.js'
    RECAPTCHA_VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'
    APP_SIGNUP_REDIRECT_URL = ''
    HYDRA_REQUEST_TIMEOUT_SECONDS = 5
    SEND_USER_UPDATE_SIGNAL = False
    SHOW_CAPTCHA_ON_SIGNUP = True
    HIDE_REMEMBER_ME_CHECKBOX = True
    CAPTCHA_RESPONSE_FIELD_NAME = 'g-recaptcha-response'
    LOGIN_VERIFIED_DEVICES_MAX_COUNT = 10
    LOGIN_VERIFICATION_CODE_EXPIRATION_SECONDS = 60 * 60
    MAX_LOGINS_PER_MONTH = 10000
    SECRET_CODE_MAX_ATTEMPTS = 10
    SIGNUP_REQUEST_EXPIRATION_SECONDS = 24 * 60 * 60
    CHANGE_EMAIL_REQUEST_EXPIRATION_SECONDS = 24 * 60 * 60
    CHANGE_RECOVERY_CODE_REQUEST_EXPIRATION_SECONDS = 60 * 60
    LANGUAGE_COOKE_NAME = 'user_lang'
    COMPUTER_CODE_COOKE_NAME = 'user_cc'
    LOGIN_VERIFICATION_COOKE_NAME = 'user_lv'
    PASSWORD_MIN_LENGTH = _get_default_password_min_length(USE_RECOVERY_CODE)
    PASSWORD_MAX_LENGTH = 64
    SEND_FILE_MAX_AGE_DEFAULT = 12096000
    MAX_CONTENT_LENGTH = 1024
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    BABEL_DEFAULT_LOCALE = 'en'
    BABEL_DEFAULT_TIMEZONE = 'UTC'
    LANGUAGE_CHOICES = _get_language_choices(LANGUAGES)

    SUPERVISOR_CLIENT_ID = 'users-supervisor'
    SUPERVISOR_CLIENT_SECRET = 'users-supervisor'
    API_AUTH2_TOKEN_URL = 'https://hydra/oauth2/token'
    API_RESOURCE_SERVER = 'https://resource-server'
    API_RESERVE_USER_ID_PATH = '/users/.user-reserve'
    API_USER_ID_FIELD_NAME = 'userId'
    API_TIMEOUT_SECONDS = 5
