from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from guardian.shortcuts import get_objects_for_user

from miqa.core.models import Scan
from miqa.core.rest.frame import FrameSerializer
from miqa.core.rest.permissions import UserHoldsExperimentLock
from miqa.core.rest.scan_decision import ScanDecisionSerializer


class ScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = ['id', 'name', 'decisions', 'frames', 'scan_type']
        ref_name = 'experiment_scan'

    frames = FrameSerializer(many=True)
    decisions = ScanDecisionSerializer(many=True)


class ScanViewSet(ReadOnlyModelViewSet):
    filter_backends = [filters.DjangoFilterBackend]
    permission_classes = [IsAuthenticated, UserHoldsExperimentLock]
    serializer_class = ScanSerializer

    def get_queryset(self):
        projects = get_objects_for_user(
            self.request.user,
            'core.view_project',
            with_superuser=False,
        )
        return Scan.objects.filter(experiment__project__in=projects)
