# Generated by Django 3.2.13 on 2022-09-16 13:55

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_CT_scan_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scandecision',
            name='created',
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
        ),
    ]
