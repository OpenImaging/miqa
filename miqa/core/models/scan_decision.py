from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from miqa.core.models import Artifact

if TYPE_CHECKING:
    from miqa.core.models import Experiment

DECISION_CHOICES = [
    ('U', 'Usable'),
    ('UE', 'Usable-Extra'),
    ('Q?', 'Questionable'),
    ('UN', 'Unusable'),
]


class ArtifactState(Enum):
    PRESENT = 1
    ABSENT = 0
    UNDEFINED = -1

def default_identified_artifacts(scan_project_artifacts = ''):
    if scan_project_artifacts != '':
        artifact_objects = Artifact.objects.filter(group__id=scan_project_artifacts)
        artifacts = [getattr(artifact, "name") for artifact in artifact_objects]
    else:
        artifacts = settings.DEFAULT_ARTIFACTS

    return {
        (
            artifact_name if artifact_name != 'full_brain_coverage' else 'partial_brain_coverage'
        ): ArtifactState.UNDEFINED.value
        for artifact_name in artifacts
        if artifact_name != 'normal_variants'
    }


class ScanDecision(models.Model):
    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['scan', '-created']),
        ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    created = models.DateTimeField(default=timezone.now)
    scan = models.ForeignKey('Scan', related_name='decisions', on_delete=models.CASCADE)
    creator = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    decision = models.CharField(max_length=2, choices=DECISION_CHOICES, blank=False)
    note = models.TextField(max_length=3000, blank=True)
    user_identified_artifacts = models.JSONField(null=True, blank=True)
    location = models.JSONField(default=dict)

    @property
    def experiment(self) -> Experiment:
        return self.scan.experiment
