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
    SmtpEmailMixin,
    TestingBaseConfiguration,
)
from composed_configuration._configuration import _BaseConfiguration
from configurations import values


class MiqaMixin(ConfigMixin):
    WSGI_APPLICATION = 'miqa.wsgi.application'
    ROOT_URLCONF = 'miqa.urls'

    BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

    @staticmethod
    def before_binding(configuration: ComposedConfiguration) -> None:
        # Install local apps first, to ensure any overridden resources are found first
        configuration.INSTALLED_APPS = [
            'miqa.core.apps.CoreConfig',
        ] + configuration.INSTALLED_APPS

        # Install additional apps
        configuration.INSTALLED_APPS += [
            's3_file_field',
        ]

        # oauth session
        configuration.OAUTH2_PROVIDER['ACCESS_TOKEN_EXPIRE_SECONDS'] = 1800  # 30 minutes


class DevelopmentConfiguration(MiqaMixin, DevelopmentBaseConfiguration):
    pass


class TestingConfiguration(MiqaMixin, TestingBaseConfiguration):
    pass


class ProductionConfiguration(MiqaMixin, ProductionBaseConfiguration):
    pass


# TODO include HttpsMixin
class DockerComposeProductionConfiguration(
    MiqaMixin,
    SmtpEmailMixin,
    HttpsMixin,
    _BaseConfiguration,
):
    """For the production deployment using docker-compose."""

    MIQA_URL_PREFIX = values.Value(environ=True, default='/')

    @property
    def STATIC_URL(self):
        """Prepend the MIQA_URL_PREFIX to STATIC_URL."""
        return str(Path(self.MIQA_URL_PREFIX) / 'static') + '/'

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
        """LOGIN_URL also needs to be behing MIQA_URL_PREFIX."""
        return str(Path(self.MIQA_URL_PREFIX) / 'accounts' / 'login') + '/'

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
    pass
