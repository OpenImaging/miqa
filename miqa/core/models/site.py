from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django_extensions.db.models import TimeStampedModel


class Site(TimeStampedModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True, unique=True, blank=False)
    creator = models.ForeignKey(User, on_delete=models.PROTECT)

    def __str__(self):
        return self.name
