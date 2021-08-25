from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from django.db import models
from django_extensions.db.models import TimeStampedModel

if TYPE_CHECKING:
    from miqa.core.models import Experiment


class Image(TimeStampedModel, models.Model):
    class Meta:
        indexes = [models.Index(fields=['scan', 'name'])]
        ordering = ['name']

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    scan = models.ForeignKey('Scan', related_name='images', on_delete=models.CASCADE)
    raw_path = models.CharField(max_length=500, blank=False, unique=True)
    name = models.CharField(max_length=255, blank=False)

    @property
    def path(self) -> Path:
        return Path(self.raw_path)

    @property
    def size(self) -> int:
        return self.path.stat().st_size

    @property
    def experiment(self) -> Experiment:
        return self.scan.experiment
