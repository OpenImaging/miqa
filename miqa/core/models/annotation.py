from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from miqa.core.models import Experiment


class Decision(Enum):
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


class Annotation(models.Model):
    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['scan', '-created']),
        ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    created = models.DateTimeField(default=timezone.now)
    scan = models.ForeignKey('Scan', related_name='decisions', on_delete=models.CASCADE)
    creator = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    decision = models.CharField(
        max_length=20,
        default=Decision.NONE.name,
        choices=[(tag.name, tag.value) for tag in Decision],
    )

    @property
    def experiment(self) -> Experiment:
        return self.scan.experiment
