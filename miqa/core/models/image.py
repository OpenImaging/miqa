from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from django.db import models
from django_extensions.db.models import TimeStampedModel

from miqa.core.conversion.nifti_to_zarr_ngff import convert_to_store_path, nifti_to_zarr_ngff

if TYPE_CHECKING:
    from miqa.core.models import Experiment


class Image(TimeStampedModel, models.Model):
    class Meta:
        indexes = [models.Index(fields=['scan', 'frame_number'])]
        ordering = ['scan', 'frame_number']

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    scan = models.ForeignKey('Scan', related_name='images', on_delete=models.CASCADE)
    raw_path = models.CharField(max_length=500, blank=False, unique=True)
    frame_number = models.IntegerField(default=0)

    def clean(self):
        # celery tasks must receive serializable types; using string raw_path here
        nifti_to_zarr_ngff.delay(str(self.raw_path))
        super().clean()
        return self

    @property
    def path(self) -> Path:
        return Path(self.raw_path)

    @property
    def zarr_path(self: Image) -> Path:
        return convert_to_store_path(self.path)

    @property
    def size(self) -> int:
        return self.path.stat().st_size

    @property
    def experiment(self) -> Experiment:
        return self.scan.experiment
