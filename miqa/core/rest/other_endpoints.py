import subprocess

from django.conf import settings
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from miqa.core.models.scan_decision import ArtifactState, default_identified_artifacts

MIQA_VERSION = subprocess.run(
    ['git', 'describe', '--tags'],
    capture_output=True,
).stdout.decode()

# Heroku doesn't have access to .git directory, version will be blank
if len(MIQA_VERSION) > 0:
    MIQA_VERSION += (
        ' commit: '
        + subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
        ).stdout.decode()
    )


class MIQAConfigView(APIView):
    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def get(self, request):
        return Response(
            {
                'artifact_options': list(default_identified_artifacts()),
                'auto_artifact_threshold': 0.4,
                'artifact_states': {
                    'PRESENT': ArtifactState.PRESENT.value,
                    'ABSENT': ArtifactState.ABSENT.value,
                    'UNDEFINED': ArtifactState.UNDEFINED.value,
                },
                'version': MIQA_VERSION,
                'S3_SUPPORT': settings.S3_SUPPORT,
                'NORMAL_USERS_CAN_CREATE_PROJECTS': settings.NORMAL_USERS_CAN_CREATE_PROJECTS,
            }
        )
