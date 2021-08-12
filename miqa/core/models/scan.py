from __future__ import annotations

from uuid import uuid4

from django.db import models
from django_extensions.db.models import TimeStampedModel


class Scan(TimeStampedModel, models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['experiment', 'scan_id', 'scan_type'], name='scan_unique_constraint'
            )
        ]
        ordering = ['scan_id']

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    experiment = models.ForeignKey('Experiment', related_name='scans', on_delete=models.CASCADE)
    site = models.ForeignKey('Site', on_delete=models.PROTECT)

    scan_id = models.CharField(max_length=127, blank=False)
    scan_type = models.CharField(max_length=255, blank=False)
