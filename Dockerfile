FROM oryd/hydra:v1.11.10 as hydra-image

FROM python:3.10.14-alpine3.20 AS venv-image
WORKDIR /usr/src/app

ENV POETRY_VERSION="1.8.3"
RUN apk add --no-cache \
    file \
    make \
    build-base \
    curl \
    gcc \
    git \
    musl-dev \
    libffi-dev \
    python3-dev \
    postgresql-dev \
    openssl-dev \
    cargo \
  && curl -sSL https://install.python-poetry.org | python - \
  && ln -s "$HOME/.local/bin/poetry" "/usr/local/bin"

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false --local \
  && python -m venv /opt/venv \
  && source /opt/venv/bin/activate \
  && poetry install --only main --no-interaction


# This is the final app image. Starting from a clean alpine image, it
# copies over the previously created virtual environment.
FROM python:3.10.14-alpine3.20 AS app-image
ARG FLASK_APP=swpt_login

ENV FLASK_APP=$FLASK_APP
ENV APP_ROOT_DIR=/usr/src/app
ENV APP_ASSOCIATED_LOGGERS=swpt_pythonlib.flask_signalbus.signalbus_cli
ENV PYTHONPATH="$APP_ROOT_DIR"
ENV PATH="/opt/venv/bin:$PATH"
ENV WEBSERVER_PORT=8080
ENV GUNICORN_LOGLEVEL=warning
ENV LOG_LEVEL=warn
ENV LOG_FORMAT=text
ENV SQA_OPT_OUT=true
ENV OAUTHLIB_INSECURE_TRANSPORT=1

RUN apk add --no-cache \
    libffi \
    postgresql-libs \
    gettext \
    && addgroup -S "$FLASK_APP" \
    && adduser -S -D -h "$APP_ROOT_DIR" "$FLASK_APP" "$FLASK_APP"
RUN [ -e /etc/nsswitch.conf ] || 'hosts: files dns' > /etc/nsswitch.conf

COPY --from=hydra-image /usr/bin/hydra /usr/bin/hydra
COPY --from=venv-image /opt/venv /opt/venv

WORKDIR /usr/src/app

COPY docker/entrypoint.sh \
     docker/gunicorn.conf.py \
     wsgi.py \
     ./
COPY migrations/ migrations/
COPY $FLASK_APP/ $FLASK_APP/
RUN python -m compileall -x '^\./(migrations|tests)/' . \
    && ! which pybabel || pybabel compile -d $FLASK_APP/translations \
    && rm -f .env \
    && chown -R "$FLASK_APP:$FLASK_APP" .

USER $FLASK_APP
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
CMD ["webserver"]
