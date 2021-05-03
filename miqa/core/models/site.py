from django.contrib.auth.models import User
from django.db import models
from django_extensions.db.models import TimeStampedModel


class Site(TimeStampedModel, models.Model):
    name = models.CharField(max_length=255, db_index=True, unique=True, blank=False)
    creator = models.ForeignKey(User, on_delete=models.PROTECT)
    session = models.ForeignKey('Session', on_delete=models.CASCADE)

    def __str__(self):
        return self.name
