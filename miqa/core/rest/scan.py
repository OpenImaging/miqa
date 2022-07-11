from django_filters import rest_framework as filters
from guardian.shortcuts import get_objects_for_user
from rest_framework import mixins, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from miqa.core.models import Experiment, Project, Scan
from miqa.core.rest.frame import FrameSerializer
from miqa.core.rest.permissions import UserHoldsExperimentLock
from miqa.core.rest.scan_decision import ScanDecisionSerializer


class ScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = [
            'id',
            'name',
            'decisions',
            'frames',
            'scan_type',
            'subject_id',
            'session_id',
            'scan_link',
            'experiment',
        ]
        ref_name = 'experiment_scan'

    frames = FrameSerializer(many=True, read_only=True)
    decisions = ScanDecisionSerializer(many=True, read_only=True)
    experiment = serializers.SlugRelatedField(queryset=Experiment.objects.all(), slug_field='id')


class ScanViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    filter_backends = [filters.DjangoFilterBackend]
    permission_classes = [IsAuthenticated, UserHoldsExperimentLock]
    serializer_class = ScanSerializer

    def get_queryset(self):
        projects = get_objects_for_user(
            self.request.user,
            [f'core.{perm}' for perm in Project().get_read_permission_groups()],
            any_perm=True,
        )
        return Scan.objects.filter(experiment__project__in=projects)
