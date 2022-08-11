from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from miqa.core.models import GlobalSettings

if TYPE_CHECKING:
    from miqa.core.models import Experiment

# artifacts = [
#     'normal_variants',
#     'lesions',
#     'full_brain_coverage',
#     'misalignment',
#     'swap_wraparound',
#     'ghosting_motion',
#     'inhomogeneity',
#     'susceptibility_metal',
#     'flow_artifact',
#     'truncation_artifact',
# ]

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


def default_identified_artifacts():
    from .project import Project
    from .artifact import Artifact
    try:
        artifact_group = Project.artifact_group
        if artifact_group:
            artifacts = Artifact.objects.filter(group__artifact__id=artifact_group)

    except:
        artifacts = GlobalSettings.default_artifacts

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
    user_identified_artifacts = models.JSONField(default=default_identified_artifacts)
    location = models.JSONField(default=dict)

    @property
    def experiment(self) -> Experiment:
        return self.scan.experiment
