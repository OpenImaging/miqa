from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

import boto3
from django.conf import settings
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel
from s3_file_field import S3FileField

from miqa.core.conversion.nifti_to_zarr_ngff import convert_to_store_path

if TYPE_CHECKING:
    from miqa.core.models import Experiment


class StorageMode(Enum):
    CONTENT_STORAGE = 1
    LOCAL_PATH = 2
    S3_PATH = 3


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
        return convert_to_store_path(str(self.path))

    @property
    def size(self) -> int:
        return self.path.stat().st_size

    @property
    def experiment(self) -> Experiment:
        return self.scan.experiment

    @property
    def storage_mode(self) -> StorageMode:
        if settings.S3_SUPPORT:
            if self.content:
                return StorageMode.CONTENT_STORAGE
            elif self.raw_path.startswith('s3://'):
                return StorageMode.S3_PATH
        return StorageMode.LOCAL_PATH

    @property
    def s3_download_url(self) -> Optional[str]:
        if self.storage_mode == StorageMode.S3_PATH:
            bucket, key = self.raw_path.strip()[5:].split('/', maxsplit=1)
            client = boto3.client('s3')
            return client.generate_presigned_url(
                'get_object', Params={'Bucket': bucket, 'Key': key}
            )
        return None


# Remove content from storage before deleting frame object
@receiver(pre_delete, sender=Frame)
def delete_content(sender, instance, **kwargs):
    if instance.content:
        instance.content.delete(save=False)
