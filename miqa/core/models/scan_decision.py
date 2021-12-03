from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from miqa.learning.nn_inference import artifacts

if TYPE_CHECKING:
    from miqa.core.models import Experiment


DECISION_CHOICES = [
    ('U', 'Usable'),
    ('UE', 'Usable-Extra'),
    ('Q?', 'Questionable'),
    ('UN', 'Unusable'),
]


def default_identified_artifacts():
    return {
        (artifact_name if artifact_name != 'full_brain_coverage' else 'partial_brain_coverage'): -1
        for artifact_name in artifacts
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

    @property
    def experiment(self) -> Experiment:
        return self.scan.experiment
