# Generated by Django 3.2.12 on 2022-04-01 17:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_project_email_recipients'),
    ]

    operations = [
        migrations.AddField(
            model_name='scan',
            name='scan_link',
            field=models.TextField(max_length=1000, null=True),
        ),
        migrations.AddField(
            model_name='scan',
            name='session_id',
            field=models.TextField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='scan',
            name='subject_id',
            field=models.TextField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='scan',
            name='scan_type',
            field=models.CharField(
                choices=[
                    ('T1', 'T1'),
                    ('T2', 'T2'),
                    ('FMRI', 'FMRI'),
                    ('MRA', 'MRA'),
                    ('PD', 'PD'),
                    ('DTI', 'DTI'),
                    ('DWI', 'DWI'),
                    ('ncanda-t1spgr-v1', 'ncanda-t1spgr-v1'),
                    ('ncanda-mprage-v1', 'ncanda-mprage-v1'),
                    ('ncanda-t2fse-v1', 'ncanda-t2fse-v1'),
                    ('ncanda-dti6b500pepolar-v1', 'ncanda-dti6b500pepolar-v1'),
                    ('ncanda-dti30b400-v1', 'ncanda-dti30b400-v1'),
                    ('ncanda-dti60b1000-v1', 'ncanda-dti60b1000-v1'),
                    ('ncanda-grefieldmap-v1', 'ncanda-grefieldmap-v1'),
                    ('ncanda-rsfmri-v1', 'ncanda-rsfmri-v1'),
                    ('PET', 'PET'),
                ],
                default='T1',
                max_length=25,
            ),
        ),
    ]
