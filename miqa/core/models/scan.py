from enum import Enum

from django.db import models
from django_extensions.db.models import TimeStampedModel


class ScanDecision(Enum):
    NONE = '-'
    GOOD = 'Good'
    BAD = 'Bad'
    USABLE_EXTRA = 'Usable extra'


class Scan(TimeStampedModel, models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['experiment', 'scan_id', 'scan_type'], name='scan_unique_constraint'
            )
        ]
        ordering = ['scan_id']

    experiment = models.ForeignKey('Experiment', on_delete=models.CASCADE)
    site = models.ForeignKey('Site', on_delete=models.PROTECT)

    scan_id = models.CharField(max_length=127, blank=False)
    scan_type = models.CharField(max_length=255, blank=False)
    decision = models.CharField(
        max_length=20, default=ScanDecision.NONE, choices=[(tag, tag.value) for tag in ScanDecision]
    )
