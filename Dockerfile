FROM oryd/hydra:v1.9.0-alpine as hydra-image

FROM python:3.7.9-alpine3.12 AS venv-image
WORKDIR /usr/src/app

ENV PIP_VERSION="21.0"
ENV POETRY_VERSION="1.1.4"
RUN apk add --no-cache \
    file \
    make \
    curl \
    gcc \
    git \
    musl-dev \
    libffi-dev \
    postgresql-dev \
    supervisor \
  && pip install --upgrade pip==$PIP_VERSION \
  && curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python \
  && ln -s "$HOME/.poetry/bin/poetry" "/usr/local/bin" \
  && python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
  && poetry install --no-dev --no-interaction


# This is the final app image. Starting from a clean alpine image, it
# copies over the previously created virtual environment.
FROM python:3.7.9-alpine3.12 AS app-image
ARG FLASK_APP=swpt_login

ENV FLASK_APP=$FLASK_APP
ENV APP_ROOT_DIR=/usr/src/app
ENV APP_LOGGING_CONFIG_FILE="$APP_ROOT_DIR/$FLASK_APP/logging.conf"
ENV PYTHONPATH="$APP_ROOT_DIR"
ENV PATH="/opt/venv/bin:$PATH"
ENV GUNICORN_WORKERS=2
ENV GUNICORN_THREADS=1
# ENV LOG_LEVEL=warn
# ENV LOG_FORMAT=json
ENV SQA_OPT_OUT=true
ENV OAUTHLIB_INSECURE_TRANSPORT=1

RUN apk add --no-cache \
    libffi \
    postgresql-libs \
    supervisor \
    gettext \
    && addgroup -S "$FLASK_APP" \
    && adduser -S -D -h "$APP_ROOT_DIR" "$FLASK_APP" "$FLASK_APP"
RUN [ ! -e /etc/nsswitch.conf ] && echo 'hosts: files dns' > /etc/nsswitch.conf

COPY --from=hydra-image /usr/bin/hydra /usr/bin/hydra
COPY --from=venv-image /opt/venv /opt/venv

WORKDIR /usr/src/app

COPY docker/hydra.yaml .hydra.yaml
COPY docker/entrypoint.sh \
     docker/gunicorn.conf.py \
     docker/supervisord.conf \
     docker/trigger_supervisor_process.py \
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
CMD ["all"]
