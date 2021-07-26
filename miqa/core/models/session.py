from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django_extensions.db.models import TimeStampedModel


class Session(TimeStampedModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    creator = models.ForeignKey(User, on_delete=models.PROTECT)
    lock_owner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, default=None, related_name='session_locks'
    )

    import_path = models.CharField(max_length=500)
    export_path = models.CharField(max_length=500)

    def __str__(self):
        return self.name
