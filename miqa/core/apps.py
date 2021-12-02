from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'miqa.core'
    verbose_name = 'MIQA: Core'

    def ready(self):
        from miqa.core import signals
