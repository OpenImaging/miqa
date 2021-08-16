from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django_extensions.db.models import TimeStampedModel

from miqa.core.models import Experiment


class Task(TimeStampedModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    experiments = models.ManyToManyField(Experiment)

    def __str__(self):
        return self.name
