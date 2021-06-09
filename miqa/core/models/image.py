from pathlib import Path
from uuid import uuid4

from django.db import models
from django_extensions.db.models import TimeStampedModel


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
