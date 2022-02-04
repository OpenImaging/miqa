from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from django.db import models
from django_extensions.db.models import TimeStampedModel
from s3_file_field import S3FileField

from miqa.core.conversion.nifti_to_zarr_ngff import convert_to_store_path

if TYPE_CHECKING:
    from miqa.core.models import Experiment


class Frame(TimeStampedModel, models.Model):
    class Meta:
        indexes = [models.Index(fields=['scan', 'frame_number'])]
        ordering = ['scan', 'frame_number']

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    scan = models.ForeignKey('Scan', related_name='frames', on_delete=models.CASCADE)
    content = S3FileField(null=True)
    raw_path = models.CharField(max_length=500, blank=False)
    frame_number = models.IntegerField(default=0)

    @property
    def path(self) -> Path:
        return Path(self.raw_path)

    @property
    def zarr_path(self: Frame) -> Path:
        return convert_to_store_path(self.path)

    @property
    def size(self) -> int:
        return self.path.stat().st_size

    @property
    def experiment(self) -> Experiment:
        return self.scan.experiment
