# Generated by Django 3.2.15 on 2022-09-12 15:53

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_CT_scan_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='SettingsGroup',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.AlterField(
            model_name='scandecision',
            name='user_identified_artifacts',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='Artifact',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='artifacts', to='core.settingsgroup')),
            ],
        ),
        migrations.AddField(
            model_name='project',
            name='artifact_group',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.settingsgroup'),
        ),
    ]
