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
]


class Scan(TimeStampedModel, models.Model):
    class Meta:
        ordering = ['name', 'scan_type']

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=127, blank=False)
    experiment = models.ForeignKey('Experiment', related_name='scans', on_delete=models.CASCADE)
    scan_type = models.CharField(max_length=10, choices=SCAN_TYPES, default='T1')
