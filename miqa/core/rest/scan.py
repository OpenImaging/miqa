from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Scan, ScanDecision
from miqa.core.rest.image import ImageSerializer
from miqa.core.rest.permissions import UserHoldsExperimentLock
from miqa.core.rest.scan_decision import ScanDecisionSerializer


class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanDecision
        fields = ['id', 'decision', 'created', 'creator']
        ref_name = 'scan_decision'


class ScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = ['id', 'name', 'decisions', 'images', 'scan_type']
        ref_name = 'experiment_scan'

    images = ImageSerializer(many=True)
    decisions = ScanDecisionSerializer(many=True)


class ScanViewSet(ReadOnlyModelViewSet):
    queryset = Scan.objects.select_related('experiment__project')

    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['experiment', 'scan_type']

    permission_classes = [IsAuthenticated, UserHoldsExperimentLock]

    serializer_class = ScanSerializer
