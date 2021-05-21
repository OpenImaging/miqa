from uuid import uuid4

from django.db import models
from django_extensions.db.models import CreationDateTimeField


class ScanNote(models.Model):
    class Meta:
        ordering = ['created']

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    created = CreationDateTimeField()
    note = models.TextField(max_length=3000)
    scan = models.ForeignKey('Scan', related_name='notes', on_delete=models.CASCADE)
