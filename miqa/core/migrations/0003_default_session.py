# flake8: noqa N806

from django.db import migrations
from django.db.models import Q


def create_default_session(apps, schema_editor):
    Session = apps.get_model('core', 'Session')
    User = apps.get_model('auth', 'User')
    name = 'Default Session'
    if not Session.objects.filter(name=name).exists():
        session = Session(
            name=name,
            creator=User.objects.first(),
            import_path='',
            export_path='',
        )
        session.save()


def reverse_create_default_session(apps, schema_editor):
    # Explicitly do nothing so the migration is still nominally reversible.
    pass


class Migration(migrations.Migration):
    dependencies = [('core', '0002_initial')]
    operations = [migrations.RunPython(create_default_session, reverse_create_default_session)]
