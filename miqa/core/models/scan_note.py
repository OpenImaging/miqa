from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django_extensions.db.models import ModificationDateTimeField

if TYPE_CHECKING:
    from miqa.core.models import Session


class ScanNote(models.Model):
    class Meta:
        ordering = ['created']

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    # TimeStampedModel uses CreationDateTimeField, which cannot be disabled
    # We want to set created to arbitrary values during import
    created = models.DateTimeField(default=timezone.now)
    modified = ModificationDateTimeField()
    creator = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    initials = models.CharField(max_length=2)
    note = models.TextField(max_length=3000)
    scan = models.ForeignKey('Scan', related_name='notes', on_delete=models.CASCADE)

    @property
    def session(self) -> Session:
        return self.scan.experiment.session
