# Generated by Django 3.2.6 on 2021-09-01 13:20

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0011_session_archived'),
    ]

    operations = [
        migrations.AlterField(
            model_name='experiment',
            name='lock_owner',
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='experiment_locks',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
