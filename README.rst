swpt_login
==========

Swaptacular service that manages OAuth2 login and consent

This service uses `ORY Hydra`_ to implement the OAuth2 login and
consent. The ultimate deliverable is a docker image, which is
generated from the project's `Dockerfile`_. To find out what processes
can be spawned from the generated image, see the `entrypoint`_. This
`example`_ shows how to use generated image.


.. _`ORY Hydra`: https://www.ory.sh/hydra/docs/
.. _Dockerfile: Dockerfile
.. _entrypoint: docker/entrypoint.sh
.. _`example`: https://github.com/epandurski/swpt_debtors/blob/master/docker-compose-all.yml



Configuration
-------------

The behavior of the service can be tuned with environment
variables. Here are the most important settings with example values:

.. code-block:: shell

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

  # The port on which the login and consent web-apps will run. The number
  # of worker processes and threads.
  WEBSERVER_PORT=8000
  WEBSERVER_WORKERS=1
  WEBSERVER_THREADS=3

  # The URL for the PostgreSQL database that the login and consent apps should use.
  SQLALCHEMY_DATABASE_URI=postgresql://user:pass@servername/login

  # Set this to the URL for the Redis server instance that the login and
  # consent apps should use. It is highly recommended that your Redis instance
  # is backed by disk storage. If not so, your users might be inconvenienced
  # when your Redis instace is restarted.
  REDIS_URL=redis://localhost:6379/0

  # Set this to the URL for ORY Hydra's admin API.
  HYDRA_ADMIN_URL=http://hydra:4445

  # The prefix added the user ID to form the Oauth2 subject field. Should be
  # either "creditors:" or "debtors:". For example, if SUBJECT_PREFIX=creditors:,
  # the OAuth2 subject for the user with ID=1234 would be "creditors:1234".
  SUBJECT_PREFIX=debtors:

  # Set this to the name of your site, as it is known to your users.
  SITE_TITLE=My site name

  # Set this to an URL that tells more about your site.
  ABOUT_URL=https://github.com/epandurski/swpt_login

  # Optional URL for a custom CSS style-sheet:
  STYLE_URL=

  # SMTP server connection parameters. You should set `MAIL_DEFAULT_SENDER`
  # to the email address from which you send your outgoing emails to users,
  # "My Site Name <no-reply@my-site.com>" for example.
  MAIL_SERVER=localhost
  MAIL_PORT=25
  MAIL_USE_TLS=False
  MAIL_USE_SSL=False
  MAIL_USERNAME=None
  MAIL_PASSWORD=None
  MAIL_DEFAULT_SENDER=None

  # Parameters for Google reCAPTCHA 2. You should obtain your own public/private
  # key pair from www.google.com/recaptcha, and put it here.
  RECAPTCHA_PUBLIC_KEY=6Lc902MUAAAAAJL22lcbpY3fvg3j4LSERDDQYe37
  RECAPTCHA_PIVATE_KEY=6Lc902MUAAAAAN--r4vUr8Vr7MU1PF16D9k2Ds9Q

  # Parameters that determine how to obtain an user ID from the resource
  # server. Note that the `API_RESOURCE_SERVER` value may include a port, but
  # MUST NOT include a path or a trailing slash. The client ID, and the client
  # secret are used to perform the "Client Credentials" OAuth2 flow against the
  # OAuth2 token endpoint, so as to get the permissions to create new users.
  SUPERVISOR_CLIENT_ID=users-supervisor
  SUPERVISOR_CLIENT_SECRET=users-supervisor
  API_AUTH2_TOKEN_URL=https://hydra/oauth2/token
  API_RESOURCE_SERVER='http://resource-server'
  API_TIMEOUT_SECONDS=5

  # Parameters that determine the logging configuration for the login and
  # consent web apps.
  APP_LOG_LEVEL=warning
  APP_LOG_FORMAT=text
