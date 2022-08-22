from uuid import uuid4
from django.db import models


class Group(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255, blank=False)
    description = models.TextField()

    def __str__(self):
        return self.name
