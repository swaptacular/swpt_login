FROM python:3.7.8-alpine3.12 AS venv-image
WORKDIR /usr/src/app

ENV PIP_VERSION="20.2"
ENV POETRY_VERSION="1.0.10"
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
FROM python:3.7.3-alpine3.9 AS app-image
ARG FLASK_APP=swpt_login

ENV FLASK_APP=$FLASK_APP
ENV APP_ROOT_DIR=/usr/src/app
ENV APP_LOGGING_CONFIG_FILE="$APP_ROOT_DIR/$FLASK_APP/logging.conf"
ENV PYTHONPATH="$APP_ROOT_DIR"
ENV PATH="/opt/venv/bin:$PATH"
ENV GUNICORN_WORKERS=2
ENV GUNICORN_THREADS=1

RUN apk add --no-cache \
    libffi \
    postgresql-libs \
    supervisor \
    gettext \
    && addgroup -S "$FLASK_APP" \
    && adduser -S -D -h "$APP_ROOT_DIR" "$FLASK_APP" "$FLASK_APP"

COPY --from=venv-image /opt/venv /opt/venv

WORKDIR /usr/src/app

COPY docker/entrypoint.sh \
     docker/gunicorn.conf \
     docker/supervisord.conf \
     docker/trigger_supervisor_process.py \
     wsgi.py \
     ./
COPY migrations/ migrations/
COPY $FLASK_APP/ $FLASK_APP/
RUN python -m compileall -x '^\./(migrations|tests)/' . \
    && rm -f .env \
    && chown -R "$FLASK_APP:$FLASK_APP" . \
    && ! which pybabel || pybabel compile -d $FLASK_APP/translations

USER $FLASK_APP
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
CMD ["serve"]
