from uuid import uuid4
from django.db import models


class Artifact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255, blank=False)
    group = models.ForeignKey('Group', on_delete=models.CASCADE)

    def __str__(self):
        return self.name
