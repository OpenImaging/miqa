# flake8: noqa N802
from __future__ import annotations

from pathlib import Path

from composed_configuration import (
    ComposedConfiguration,
    ConfigMixin,
    DevelopmentBaseConfiguration,
    HerokuProductionBaseConfiguration,
    HttpsMixin,
    ProductionBaseConfiguration,
    S3StorageMixin,
    SmtpEmailMixin,
    TestingBaseConfiguration,
)
from datetime import timedelta
from composed_configuration._configuration import _BaseConfiguration
from configurations import values


class MiqaMixin(ConfigMixin):
    WSGI_APPLICATION = 'miqa.wsgi.application'
    ROOT_URLCONF = 'miqa.urls'
    HOMEPAGE_REDIRECT_URL = values.Value(environ=True, default=None)

    BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

    # Django logins should only last for 30 minutes, the same as the duration of the OAuth token.
    SESSION_COOKIE_AGE = 1800

    # This is required for the /api/v1/logout/ view to have access to the session cookie.
    CORS_ALLOW_CREDENTIALS = True

    # MIQA-specific settings
    ZARR_SUPPORT = False
    S3_SUPPORT = True

    # Demo mode is for app.miqaweb.io (Do not enable for normal instances)
    DEMO_MODE = values.BooleanValue(environ=True, default=False)
    # It is recommended to enable the following for demo mode:
    NORMAL_USERS_CAN_CREATE_PROJECTS = values.BooleanValue(environ=True, default=False)
    # Enable the following to replace null creation times for scan decisions with import time
    REPLACE_NULL_CREATION_DATETIMES = values.BooleanValue(environ=True, default=False)

    # Override default signup sheet to ask new users for first and last name
    ACCOUNT_FORMS = {'signup': 'miqa.core.rest.accounts.AccountSignupForm'}

    @property
    def CELERY_BEAT_SCHEDULE(self):
        if self.DEMO_MODE:
            return {
                'reset-demo': {
                    'task': 'miqa.core.tasks.reset_demo',
                    'schedule': timedelta(days=1),
                }
            }
        else:
            return {}

    @staticmethod
    def before_binding(configuration: ComposedConfiguration) -> None:
        # Install local apps first, to ensure any overridden resources are found first
        configuration.INSTALLED_APPS = [
            'miqa.core.apps.CoreConfig',
            'auth_style',
        ] + configuration.INSTALLED_APPS

        # Install additional apps
        configuration.INSTALLED_APPS += [
            's3_file_field',
            'guardian',
        ]

        configuration.TEMPLATES[0]['DIRS'] += [
            Path(configuration.BASE_DIR, 'miqa/templates/'),
        ]

        # guardian's authentication backend
        configuration.AUTHENTICATION_BACKENDS += [
            'guardian.backends.ObjectPermissionBackend',
        ]

        # disable guardian anonymous user
        configuration.ANONYMOUS_USER_NAME = None

        # oauth session
        configuration.OAUTH2_PROVIDER['ACCESS_TOKEN_EXPIRE_SECONDS'] = 1800  # 30 minutes

        # drf
        configuration.REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
            'rest_framework.permissions.IsAuthenticated'
        ]
        configuration.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] += [
            'rest_framework.authentication.TokenAuthentication',
        ]
        configuration.REST_FRAMEWORK[
            'EXCEPTION_HANDLER'
        ] = 'miqa.core.rest.exceptions.custom_exception_handler'


class DevelopmentConfiguration(MiqaMixin, DevelopmentBaseConfiguration):
    HOMEPAGE_REDIRECT_URL = values.Value(environ=True, default='http://localhost:8081')


class TestingConfiguration(MiqaMixin, TestingBaseConfiguration):
    # We would like to test that the celery tasks work correctly when triggered from the API
    CELERY_TASK_ALWAYS_EAGER = True


class PyppeteerTestingConfiguration(MiqaMixin, DevelopmentBaseConfiguration):
    # We would like to test that the celery tasks work correctly when triggered from the API
    CELERY_TASK_ALWAYS_EAGER = True


class ProductionConfiguration(MiqaMixin, ProductionBaseConfiguration):
    pass


class DockerComposeProductionConfiguration(
    MiqaMixin,
    SmtpEmailMixin,
    HttpsMixin,
    S3StorageMixin,
    _BaseConfiguration,
):
    """For the production deployment using docker-compose."""

    MIQA_URL_PREFIX = values.Value(environ=True, default='/')

    # Configure connection to S3 bucket by setting the following environment variables:
    # AWS_DEFAULT_REGION
    # AWS_ACCESS_KEY_ID
    # AWS_SECRET_ACCESS_KEY
    # DJANGO_STORAGE_BUCKET_NAME

    # Needed to support the reverse proxy configuration
    USE_X_FORWARDED_HOST = True

    @property
    def STATIC_URL(self):
        """Prepend the MIQA_URL_PREFIX to STATIC_URL."""
        return f'{Path(self.MIQA_URL_PREFIX) / "static"}/'

    @property
    def FORCE_SCRIPT_NAME(self):
        """
        Set FORCE_SCRIPT_NAME to MIQA_URL_PREFIX, a more user-friendly name.

        This is necessary so that {url} blocks in templates include the MIQA_URL_PREFIX.
        Without it, links in the admin console would not have the prefix, and would not resolve.
        """
        return self.MIQA_URL_PREFIX

    # Whitenoise needs to serve the static files from /static/, even though Django needs to think
    # that they are served from {MIQA_URL_PREFIX}/static/. The nginx server will strip away the
    # prefix from incoming requests.
    WHITENOISE_STATIC_PREFIX = '/static/'

    @property
    def LOGIN_URL(self):
        """LOGIN_URL also needs to be behind MIQA_URL_PREFIX."""
        return str(Path(self.MIQA_URL_PREFIX) / 'accounts' / 'login') + '/'

    @property
    def LOGIN_REDIRECT_URL(self):
        """When login is completed without `next` set, redirect to MIQA_URL_PREFIX."""
        return self.MIQA_URL_PREFIX

    # We trust the reverse proxy to redirect HTTP traffic to HTTPS
    SECURE_SSL_REDIRECT = False

    # This must be set when deployed behind a proxy
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # If nginx settings include an upstream definition, then the Host HTTP field may not match the
    # Referrer HTTP field, which causes Django to reject all non-safe HTTP operations as a CSRF
    # safeguard.
    # To circumvent this, include the expected value of the Referrer field in this setting.
    CSRF_TRUSTED_ORIGINS = values.ListValue(environ=True, default=[])

    @staticmethod
    def before_binding(configuration: ComposedConfiguration) -> None:
        # Register static files as templates so that the index.html built by the client is
        # available as a template.
        # This should be STATIC_ROOT, but that is bound as a property which cannot be evaluated
        # at this point, so we make this assumption about staticfiles instead.
        configuration.TEMPLATES[0]['DIRS'] += [
            configuration.BASE_DIR / 'staticfiles',
        ]


class HerokuProductionConfiguration(MiqaMixin, HerokuProductionBaseConfiguration):
    ZARR_SUPPORT = False
