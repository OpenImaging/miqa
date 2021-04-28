from django.db import models
from django_extensions.db.models import CreationDateTimeField

# TODO unused
class ScanNote(models.Model):
    class Meta:
        ordering = ['created']

    created = CreationDateTimeField()
    note = models.TextField(max_length=3000)
    scan = models.ForeignKey('Scan', on_delete=models.CASCADE)
