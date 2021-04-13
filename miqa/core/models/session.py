from django.contrib.auth.models import User
from django.db import models
from django_extensions.db.models import TimeStampedModel


class Session(TimeStampedModel, models.Model):
    creator = models.ForeignKey(User, on_delete=models.PROTECT)
