FROM python:3.8-slim
# Install system librarires for Python packages:
# * psycopg2
RUN apt-get update && \
  apt-get install --no-install-recommends --yes \
  libpq-dev gcc libc6-dev git-lfs && \
  rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY . /opt/django-project/
RUN pip install /opt/django-project

# Use a directory name which will never be an import name, as isort considers this as first-party.
WORKDIR /opt/django-project
