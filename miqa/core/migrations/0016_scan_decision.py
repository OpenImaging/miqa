# Generated by Django 3.2.8 on 2021-10-22 18:32

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0015_scan_image_relationship'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScanDecision',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                (
                    'decision',
                    models.CharField(
                        choices=[('Good', 'G'), ('Bad', 'B'), ('Other', 'O')], max_length=20
                    ),
                ),
                ('note', models.TextField(blank=True, max_length=3000)),
                (
                    'creator',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'scan',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='decisions',
                        to='core.scan',
                    ),
                ),
            ],
            options={
                'ordering': ['-created'],
            },
        ),
        migrations.RemoveField(
            model_name='scannote',
            name='creator',
        ),
        migrations.RemoveField(
            model_name='scannote',
            name='scan',
        ),
        migrations.DeleteModel(
            name='Annotation',
        ),
        migrations.DeleteModel(
            name='ScanNote',
        ),
        migrations.AddIndex(
            model_name='scandecision',
            index=models.Index(fields=['scan', '-created'], name='core_scande_scan_id_23388a_idx'),
        ),
    ]