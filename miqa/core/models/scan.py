from enum import Enum

from django.db import models
from django_extensions.db.models import TimeStampedModel


class ScanDecision(Enum):
    NONE = '-'
    GOOD = 'Good'
    BAD = 'Bad'
    USABLE_EXTRA = 'Usable extra'

    @classmethod
    def from_rating(cls, rating: str) -> str:
        return {
            '': cls.NONE.name,
            '0': cls.BAD.name,
            '1': cls.GOOD.name,
            '2': cls.USABLE_EXTRA.name,
        }[rating]

    @classmethod
    def to_rating(cls, decision: str) -> str:
        return {
            cls.NONE.name: '',
            cls.BAD.name: '0',
            cls.GOOD.name: '1',
            cls.USABLE_EXTRA.name: '2',
        }[decision]


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
        max_length=20,
        default=ScanDecision.NONE.name,
        choices=[(tag.name, tag.value) for tag in ScanDecision],
    )
    note = models.TextField(max_length=3000, blank=True)
