Swaptacular service that manages OAuth2 login and consent
=========================================================

**IMPORTANT NOTE: The implementation of this service is
provisional. Organizations running Swaptacular debtors and creditors
agents are encouraged to use their own implementations, which take
into account their concrete security and user management policies.**

This project implements user registration, login, and authorization
consent for [Swaptacular]. The ultimate deliverable is a docker image,
which is generated from the project's
[Dockerfile](../master/Dockerfile).


Dependencies
------------

Containers started from the generated docker image must have access to
the following servers:

1. [PostgreSQL] server instance, which stores users' data.

2. [Ory Hydra] [OAuth 2.0] authorization server, which generates and
   verifies access tokens.

3. [Redis] server instance, which stores more or less transient login
   data. For this kind of information, the tolerance for data loss is
   high, but nevertheless, the Redis server instance must be
   configured as persistent (on-disk) database.

To increase security and performance, it is highly recommended that
you configure HTTP reverse-proxy server(s) (like [nginx]) between your
clients and your login and Ory Hydra servers.


Configuration
-------------

The behavior of the running container can be tuned with environment
variables. Here are the most important settings with some random
example values:

```shell
# Set this to the base URL of ORY Hydra's admin API. Note that Ory
# Hydra 2.0 adds an "/admin/" prefix to all endpoints in the admin
# API. Therefore, for Ory Hydra >= 2.0, the value of HYDRA_ADMIN_URL
# would be something like this: "http://hydra:4445/admin/".
HYDRA_ADMIN_URL=http://hydra:4445/

# The prefix added the user ID to form the Oauth2 subject field. Must be
# either "creditors:" or "debtors:". For example, if SUBJECT_PREFIX=creditors:,
# the OAuth2 subject for the user with ID=1234 would be "creditors:1234".
SUBJECT_PREFIX=debtors:

# The specified number of processes ("$WEBSERVER_PROCESSES") will be
# spawned to handle HTTP requests (default 1), each process will run
# "$WEBSERVER_THREADS" threads in parallel (default 3). The container
# will listen for HTTP requests on port "$WEBSERVER_PORT" (default 8080).
WEBSERVER_PORT=8000
WEBSERVER_PROCESSES=1
WEBSERVER_THREADS=3

# Optional path (only the path) to the login page. If not set,
# depending on the value of the SUBJECT_PREFIX variable, the default
# will be either "/creditors-login" or "/debtors-login".
LOGIN_PATH=

# Optional path (only the path) to the consent page. If not set,
# depending on the value of the SUBJECT_PREFIX variable, the default
# will be either "/creditors-consent" or "/debtors-consent".
CONSENT_PATH=

# The URL for the PostgreSQL database that the login and consent apps should use.
SQLALCHEMY_DATABASE_URI=postgresql+psycopg2://swpt_login:swpt_login@localhost:5435/test

# Set this to the URL for the Redis server instance that the login and
# consent apps should use. It is highly recommended that your Redis instance
# is backed by disk storage. If not so, your users might be inconvenienced
# when your Redis instace is restarted.
REDIS_URL=redis://redis:6379/0

# Set this to the name of your site, as it is known to your users.
SITE_TITLE=Demo Debtors Agent

# Set this to an URL that tells more about your site.
ABOUT_URL=https://example.com/about

# Optional URL for a custom CSS style-sheet.
STYLE_URL=

# SMTP server connection parameters. You should set MAIL_SERVER to the
# name of your mail server, and MAIL_PORT to the SMTP port on that
# server. MAIL_DEFAULT_SENDER should be set to the email address from
# which outgoing emails will be sent to users. Do not set
# MAIL_USERNAME and MAIL_PASSWORD if the SMPT server does not
# require username and password. MAIL_USE_SSL detemines whether SSL
# is required from the beginning, and MAIL_USE_TLS determines
# whether the STARTTLS extension should be used after the connection
# to the mail server has bee established.
MAIL_SERVER=my-mail-server
MAIL_PORT=25
MAIL_USE_TLS=False
MAIL_USE_SSL=False
MAIL_USERNAME=smtp_user
MAIL_PASSWORD=smpt_password
MAIL_DEFAULT_SENDER=Demo Debtors Agent <no-reply@example.com>

# Parameters for Google reCAPTCHA 2. You should obtain your own public/private
# key pair from www.google.com/recaptcha, and put it here.
RECAPTCHA_PUBLIC_KEY=6Lc902MUAAAAAJL22lcbpY3fvg3j4LSERDDQYe37
RECAPTCHA_PIVATE_KEY=6Lc902MUAAAAAN--r4vUr8Vr7MU1PF16D9k2Ds9Q

# Parameters that determine how to obtain an user ID from the resource
# server. "$SUPERVISOR_CLIENT_ID" and "$SUPERVISOR_CLIENT_SECRET" are
# used to perform the "Client Credentials" OAuth2 flow against the
# OAuth2 token endpoint ("$API_AUTH2_TOKEN_URL"), so as to get the
# permissions to create new users. New users will be created by
# sending requests to "$API_RESOURCE_SERVER". The timeout for the Web
# API requests will be "$API_TIMEOUT_SECONDS" seconds (default 5).
SUPERVISOR_CLIENT_ID=debtors-supervisor
SUPERVISOR_CLIENT_SECRET=debtors-supervisor
API_AUTH2_TOKEN_URL=https://my-nginx-ingress/debtors-hydra/oauth2/token
API_RESOURCE_SERVER=https://my-nginx-ingress
API_TIMEOUT_SECONDS=5

# Optional URL to go to, after a successful sign-up.
APP_SIGNUP_REDIRECT_URL=

# Set the minimum level of severity for log messages ("info",
# "warning", or "error"). The default is "warning".
APP_LOG_LEVEL=info

# Set format for log messages ("text" or "json"). The default is
# "text".
APP_LOG_FORMAT=text
```

Available commands
------------------

The [entrypoint](../master/docker/entrypoint.sh) of the docker
container allows you to execute the following *documented commands*:

* `configure`

  Initializes a new empty PostgreSQL database for the login Web
  server.

  **IMPORTANT NOTE: This command has to be run only once (at the
  beginning), but running it multiple times should not do any harm.**

* `webserver`

  Starts a login Web server. This command allows you to start as many
  web servers as necessary, to handle the incoming load.

* `flush`

  Starts a process that periodically processes unprocessed rows from
  the *registered_user_signal* table. When some Web server process is
  unexpectedly terminated, some rows in that table may remain
  unprocessed. This command will take care of them.

  **IMPORTANT NOTE: You must start exactly one container with this
  command.**


How to run all services together (production-like)
--------------------------------------------------

This [docker-compose
example](https://github.com/swaptacular/swpt_debtors/blob/master/docker-compose-all.yml)
shows how the generated docker image can be used along with the other
parts of the system.


[Swaptacular]: https://swaptacular.github.io/overview
[ORY Hydra]: https://www.ory.sh/hydra/docs/
[Debtors Agent]: https://github.com/swaptacular/swpt_debtors
[Creditors Agent]: https://github.com/swaptacular/swpt_creditors
[Swaptacular Messaging Protocol]: https://github.com/swaptacular/swpt_accounts/blob/master/protocol.rst
[PostgreSQL]: https://www.postgresql.org/
[nginx]: https://en.wikipedia.org/wiki/Nginx
[OAuth 2.0]: https://oauth.net/2/
[Ory Hydra]: https://www.ory.sh/hydra/
[Redis]: https://redis.io/
