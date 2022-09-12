from uuid import uuid4
from django.db import models


class SettingsGroup(models.Model):
    """Models a generic group of items

        Allows one to reference a specific grouping of items.

        It is currently used by Project to select a collection of Artifacts.
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
