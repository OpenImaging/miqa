from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Annotation, Scan

from miqa.core.rest.permissions import UserHoldsExperimentLock
from miqa.core.rest.scan_note import ScanNoteSerializer
from miqa.core.rest.image import ImageSerializer


class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotation
        fields = ['id', 'decision', 'created', 'creator']
        ref_name = 'scan_decision'


class ScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = ['id', 'name', 'notes', 'decisions', 'images', 'scan_type']
        ref_name = 'experiment_scan'

    notes = ScanNoteSerializer(many=True)
    images = ImageSerializer(many=True)
    decisions = DecisionSerializer(many=True)


class ScanViewSet(ReadOnlyModelViewSet):
    queryset = Scan.objects.select_related('experiment__project')

    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['experiment', 'scan_type']

    permission_classes = [IsAuthenticated, UserHoldsExperimentLock]

    serializer_class = ScanSerializer
