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
from composed_configuration._configuration import (
    _BaseConfiguration,
)


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

    @staticmethod
    def before_binding(configuration: ComposedConfiguration) -> None:
        # Register static files as templates so that the index.html built by the client is
        # available as a template.
        # This should be STATIC_ROOT, but that is bound as a property which cannot be evaluated
        # at this point, so we make this assumption about staticfiles instead.
        configuration.TEMPLATES[0]['DIRS'] += [
            str(Path(configuration.BASE_DIR) / 'staticfiles'),
        ]


class HerokuProductionConfiguration(MiqaMixin, HerokuProductionBaseConfiguration):
    pass
