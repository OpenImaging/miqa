from uuid import uuid4

from django.db import models
from django_extensions.db.models import TimeStampedModel


class Experiment(TimeStampedModel, models.Model):
    class Meta:
        indexes = [models.Index(fields=['session', 'name'])]
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'name'], name='experiment_session_name_unique'
            ),
        ]
        ordering = ['name']

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255, blank=False)
    note = models.TextField(max_length=3000, blank=True)
    session = models.ForeignKey('Session', related_name='experiments', on_delete=models.CASCADE)

    def __str__(self):
        return self.name
