swpt_login
==========

Swaptacular micro-service responsible for user's sign up and login


## Configuration

*swpt_login*'s behavior can be tuned with environment variables. Here
are the most important settings with their default values:

``` shell
# The port on which `hydra_login2f` will run.
WEBSERVER_PORT=8000

# The path to the login page (ORY Hydra's `OAUTH2_LOGIN_URL`):
LOGIN_PATH='/login'

# The path to the consent page (ORY Hydra's `OAUTH2_CONSENT_URL`).
CONSENT_PATH='/consent'

# The prefix added the user ID to form the Oauth2 subject field. For
# example, if SUBJECT_PREFIX='user:', the OAuth2 subject for the user
# with ID=1234 would be 'user:1234'.
SUBJECT_PREFIX=''

# Set this to a random, long string. This secret is used only to sign
# the session cookies which guide the users' experience, and therefore it
# IS NOT of critical importance to keep this secret safe.
SECRET_KEY='dummy-secret'

# Set this to the name of your site, as it is known to your users.
SITE_TITLE='My site name'

# Set this to an URL that tells more about your site.
ABOUT_URL='https://github.com/epandurski/swpt_login'

# Optional URL for a custom CSS style-sheet:
STYLE_URL=''

# Set this to the URL for ORY Hydra's admin API.
HYDRA_ADMIN_URL='http://hydra:4445'

# Set this to the URL for your Redis server instance. It is highly
# recommended that your Redis instance is backed by disk storage. If not so,
# your users might be inconvenienced when your Redis instace is restarted.
REDIS_URL='redis://localhost:6379/0'

# Set this to the URL for your SQL database server instance. PostgreSQL
# and MySQL are supported out of the box. Example URLs:
# - postgresql://user:pass@servername/dbname
# - mysql+mysqlconnector://user:pass@servername/dbname
SQLALCHEMY_DATABASE_URI=''

# The size of the database connection pool. If not set, defaults to the
# engine’s default (usually 5).
SQLALCHEMY_POOL_SIZE=None

# Controls the number of connections that can be created after the pool
# reached its maximum size (`SQLALCHEMY_POOL_SIZE`). When those additional
# connections are returned to the pool, they are disconnected and discarded.
SQLALCHEMY_MAX_OVERFLOW=None

# Specifies the connection timeout in seconds for the pool.
SQLALCHEMY_POOL_TIMEOUT=None

# The number of seconds after which a connection is automatically recycled.
# This is required for MySQL, which removes connections after 8 hours idle
# by default. It will be automatically set to 2 hours if MySQL is used.
# Some backends may use a different default timeout value (MariaDB, for
# example).
SQLALCHEMY_POOL_RECYCLE=None

# SMTP server connection parameters. You should set `MAIL_DEFAULT_SENDER`
# to the email address from which you send your outgoing emails to users,
# "My Site Name <no-reply@my-site.com>" for example.
MAIL_SERVER='localhost'
MAIL_PORT=25
MAIL_USE_TLS=False
MAIL_USE_SSL=False
MAIL_USERNAME=None
MAIL_PASSWORD=None
MAIL_DEFAULT_SENDER=None

# Parameters for Google reCAPTCHA 2. You should obtain your own public/private
# key pair from www.google.com/recaptcha, and put it here.
RECAPTCHA_PUBLIC_KEY='6Lc902MUAAAAAJL22lcbpY3fvg3j4LSERDDQYe37'
RECAPTCHA_PIVATE_KEY='6Lc902MUAAAAAN--r4vUr8Vr7MU1PF16D9k2Ds9Q'

# The client ID, the client secret, and the OAuth2 token endpoint, used to
# perform the "Client Credentials OAuth2 flow, so as to obtain the permissions
# to create new users. During testing, it might be necessary to set
# `OAUTHLIB_INSECURE_TRANSPORT=1` as well.
SUPERVISOR_CLIENT_ID='users-supervisor'
SUPERVISOR_CLIENT_SECRET='users-supervisor'
API_AUTH2_TOKEN_URL='https://hydra/oauth2/token'

# Parameters that determine how a new user ID can be obtained from the
# resource server. Note that the `API_RESOURCE_SERVER` value may include a
# port, but MUST NOT include a path or a trailing slash.
API_RESOURCE_SERVER='http://resource-server'
API_RESERVE_USER_ID_PATH='/users/.user-reserve'
API_USER_ID_FIELD_NAME='userId'
API_TIMEOUT_SECONDS=5

# This sets the desired granularity of log outputs. Valid level names
# are: debug, info, warning, error, critical.
GUNICORN_LOGLEVEL='warning'

# This sets the type of workers to use with gunicorn.
GUNICORN_WORKER_CLASS='sync'

# Set this to the number of worker processes for handling requests -- a
# positive integer generally in the 2-4 * $NUM_CORES range.
GUNICORN_WORKERS=2

# Set this to the number of worker threads for handling requests. (Runs
# each worker with the specified number of threads.)
GUNICORN_THREADS=1
```
