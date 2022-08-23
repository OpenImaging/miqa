from uuid import uuid4
from django.db import models


class Artifact(models.Model):
    """Models an individual artifact

        Artifacts are either (1) a visible alteration to an image (not part of the object imaged)
        or (2) an unexpected deviation from the normative appearance of an object imaged.
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255, blank=False)
    group = models.ForeignKey('Group', on_delete=models.CASCADE)

    def __str__(self):
        return self.name
