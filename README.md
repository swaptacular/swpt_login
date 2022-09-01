Swaptacular service that manages OAuth2 login and consent
=========================================================

**IMPORTANT NOTE: The implementation of this service is
provisional. Organizations running Swaptacular debtors and creditors
agents are encouraged to use their own implementations, which take
into account their concrete security and user management policies.**

This service provides user registration, login, and authorization
consent for [Swaptacular]. Internally, it uses the [ORY Hydra] OAuth
2.0 authorization server. The ultimate deliverable is a docker image,
which is generated from the project's
[Dockerfile](../master/Dockerfile). To find out what processes can be
spawned from the generated image, see the
[entrypoint](../master/docker/entrypoint.sh). This
[example](https://github.com/swaptacular/swpt_debtors/blob/master/docker-compose-all.yml)
shows how to use the generated image.


Configuration
-------------

The behavior of the running container can be tuned with environment
variables. Here are the most important settings with some random
example values:

```shell
# The URL for the PostgreSQL database that ORY Hydra should use.
HYDRA_DSN=postgres://hydra_debtors:hydra_debtors@pg/hydra

# Hydra configuration settings. See ORY Hydra's configuration docs.
SERVE_PUBLIC_PORT=4444
SERVE_ADMIN_PORT=4445
SERVE_TLS_ALLOW_TERMINATION_FROM=0.0.0.0/0
TTL_ACCESS_TOKEN=24h
TTL_REFRESH_TOKEN=720h
SECRETS_SYSTEM=keep-this-secret
URLS_SELF_ISSUER=https://example.com/debtors-hydra/
URLS_LOGIN=https://example.com/debtors-login/
URLS_CONSENT=https://example.com/debtors-consent/
URLS_ERROR=https://example.com/auth-error

# Parameters that determine the logging configuration for ORY Hydra.
HYDRA_LOG_LEVEL=warning
HYDRA_LOG_FORMAT=json

# Set this to the URL for ORY Hydra's admin API.
HYDRA_ADMIN_URL=http://hydra:4445

# The prefix added the user ID to form the Oauth2 subject field. Should be
# either "creditors:" or "debtors:". For example, if SUBJECT_PREFIX=creditors:,
# the OAuth2 subject for the user with ID=1234 would be "creditors:1234".
SUBJECT_PREFIX=debtors:

# The port on which the login and consent web-apps will run, also the
# number of worker processes, and running threads in each process.
WEBSERVER_PORT=8000
WEBSERVER_PROCESSES=1
WEBSERVER_THREADS=3

# Optional path (only the path) to the login page. If not set, the value of
# the URLS_LOGIN variable will be used to guess the login path.
LOGIN_PATH=

# Optional path (only the path) to the consetn page. If not set, the value of
# the URLS_CONSENT variable will be used to guess the consent path.
CONSENT_PATH=

# The URL for the PostgreSQL database that the login and consent apps should use.
SQLALCHEMY_DATABASE_URI=postgresql://user:pass@servername/login

# Set this to the URL for the Redis server instance that the login and
# consent apps should use. It is highly recommended that your Redis instance
# is backed by disk storage. If not so, your users might be inconvenienced
# when your Redis instace is restarted.
REDIS_URL=redis://redis:6379/0

# Set this to the name of your site, as it is known to your users.
SITE_TITLE=Demo Debtors Agent

# Set this to an URL that tells more about your site.
ABOUT_URL=https://example.com/about

# Optional URL to go after a successful sign-up:
APP_SIGNUP_REDIRECT_URL=

# Optional URL for a custom CSS style-sheet:
STYLE_URL=

# SMTP server connection parameters. You should set
# `MAIL_DEFAULT_SENDER` to the email address from which you send your
# outgoing emails to users, "My Site Name <no-reply@my-site.com>" for
# example. Do not set `MAIL_USERNAME` and `MAIL_PASSWORD` if the SMPT
# server does not require username and password.
MAIL_SERVER=mail
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
# server. The client ID, and the client secret are used to perform the
# "Client Credentials" OAuth2 flow against the OAuth2 token endpoint,
# so as to get the permissions to create new users. New users will be
# created by sending requests to `API_RESOURCE_SERVER`.
SUPERVISOR_CLIENT_ID=users-supervisor
SUPERVISOR_CLIENT_SECRET=users-supervisor
API_AUTH2_TOKEN_URL=https://nginx-proxy/debtors-hydra/oauth2/token
API_RESOURCE_SERVER=https://nginx-proxy
API_TIMEOUT_SECONDS=5

# Parameters that determine the logging configuration for the login and
# consent web apps.
APP_LOG_LEVEL=warning
APP_LOG_FORMAT=text
```


TODO:
-----

Currently, the activation of each user is done by making an
HTTP POST request to the "activate" endpoint. When the users are
stored on several database servers (sharding), this method of
activation can be fragile, because it assumes that the reverse-proxy
server will always forward the request to the correct Web server among
many. A more reliable method of activation would be to send the
activation command via a RabbitMQ message. In this case, even if the
reverse-proxy and the RabbitMQ broker temporarily route the same
creditor ID to different database servers, this would not result in a
disaster. Both [Debtors Agent] and [Creditors Agent] reference
implementations, as an extension to the [Swaptacular Messaging
Protocol], support `ActivateDebtor` and `ActivateCreditor` messages
types respectively. The user registration logic should be re-written
to send these messages to activate users, instead of making HTTP POST
requests.



[Swaptacular]: https://swaptacular.github.io/overview
[ORY Hydra]: https://www.ory.sh/hydra/docs/
[Debtors Agent]: https://github.com/swaptacular/swpt_debtors
[Creditors Agent]: https://github.com/swaptacular/swpt_creditors
[Swaptacular Messaging Protocol]: https://github.com/swaptacular/swpt_accounts/blob/master/protocol.rst
