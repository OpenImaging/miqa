FROM python:3.8-slim
# Install nodejs + npm for building client library
# Install system libraries for Python packages:
# * psycopg2
RUN apt-get update && \
    apt-get install --no-install-recommends --yes \
    curl && \
    curl -fsSL https://deb.nodesource.com/setup_16.x | bash - && \
    apt-get install --no-install-recommends --yes \
    nodejs && \
    apt-get install --no-install-recommends --yes \
    git && \
    apt-get install --no-install-recommends --yes \
    libpq-dev gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install django project
# These arguments are required to use manage.py
ARG DJANGO_ALLOWED_HOSTS
ARG DJANGO_CONFIGURATION
ARG DJANGO_DATABASE_URL
ARG DJANGO_DEFAULT_FROM_EMAIL
ARG DJANGO_EMAIL_URL
ARG DJANGO_MIQA_URL_PREFIX
ARG DJANGO_SECRET_KEY
COPY ./setup.py /opt/django-project/setup.py
COPY ./manage.py /opt/django-project/manage.py
COPY ./miqa /opt/django-project/miqa
WORKDIR /opt/django-project/
RUN pip install .[learning] && \
    ./manage.py collectstatic

# Web client:
# * Build
# * Copy to staticfiles
# * Remove node_modules, etc.
COPY web_client /opt/vue-client/
WORKDIR /opt/vue-client/
# This is necessary so that the OAuth client knows who it's authenticating with
ARG VUE_APP_OAUTH_API_ROOT
RUN npm install \
    && npm run build \
    && mkdir -p /opt/django-project/staticfiles/ \
    && mv dist/* /opt/django-project/staticfiles/ \
    && rm -rf /opt/vue-client/

# Copy the git folder so we can fetch the version tag at runtime
COPY ./.git /opt/django-project/.git

# Use a directory name which will never be an import name, as isort considers this as first-party.
WORKDIR /opt/django-project
