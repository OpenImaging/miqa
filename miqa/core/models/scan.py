from __future__ import annotations

from uuid import uuid4

from django.db import models
from django_extensions.db.models import TimeStampedModel

SCAN_TYPES = [
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
]


class Scan(TimeStampedModel, models.Model):
    class Meta:
        ordering = ['name']

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=127, blank=False)
    experiment = models.ForeignKey('Experiment', related_name='scans', on_delete=models.CASCADE)
    scan_type = models.CharField(max_length=25, choices=SCAN_TYPES, default='T1')
    subject_id = models.TextField(max_length=255, null=True)
    session_id = models.TextField(max_length=255, null=True)
    scan_link = models.TextField(max_length=1000, null=True)
