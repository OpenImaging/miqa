# Generated by Django 3.2 on 2021-05-21 17:49

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_extensions.db.fields


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_default_site'),
    ]

    operations = [
        migrations.CreateModel(
            name='Experiment',
            fields=[
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ('name', models.CharField(max_length=255)),
                ('note', models.TextField(blank=True, max_length=3000)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Scan',
            fields=[
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ('scan_id', models.CharField(max_length=127)),
                ('scan_type', models.CharField(max_length=255)),
                (
                    'decision',
                    models.CharField(
                        choices=[
                            ('NONE', '-'),
                            ('GOOD', 'Good'),
                            ('BAD', 'Bad'),
                            ('USABLE_EXTRA', 'Usable extra'),
                        ],
                        default='NONE',
                        max_length=20,
                    ),
                ),
                (
                    'experiment',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to='core.experiment'
                    ),
                ),
            ],
            options={
                'ordering': ['scan_id'],
            },
        ),
        migrations.CreateModel(
            name='Site',
            fields=[
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ('name', models.CharField(db_index=True, max_length=255, unique=True)),
                (
                    'creator',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Session',
            fields=[
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ('name', models.CharField(max_length=255)),
                ('import_path', models.CharField(max_length=500)),
                ('export_path', models.CharField(max_length=500)),
                (
                    'creator',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ScanNote',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True)),
                ('note', models.TextField(max_length=3000)),
                (
                    'creator',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL
                    ),
                ),
                (
                    'scan',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notes',
                        to='core.scan',
                    ),
                ),
            ],
            options={
                'ordering': ['created'],
            },
        ),
        migrations.AddField(
            model_name='scan',
            name='site',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.site'),
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ('raw_path', models.CharField(max_length=500)),
                ('name', models.CharField(max_length=255)),
                (
                    'scan',
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.scan'),
                ),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='experiment',
            name='session',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.session'),
        ),
        migrations.AddConstraint(
            model_name='scan',
            constraint=models.UniqueConstraint(
                fields=('experiment', 'scan_id', 'scan_type'), name='scan_unique_constraint'
            ),
        ),
        migrations.AddIndex(
            model_name='image',
            index=models.Index(fields=['scan', 'name'], name='core_image_scan_id_4369e2_idx'),
        ),
        migrations.AddIndex(
            model_name='experiment',
            index=models.Index(fields=['session', 'name'], name='core_experi_session_be49ba_idx'),
        ),
        migrations.AddConstraint(
            model_name='experiment',
            constraint=models.UniqueConstraint(
                fields=('session', 'name'), name='experiment_session_name_unique'
            ),
        ),
    ]
