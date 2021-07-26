from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Annotation, Scan

from .permissions import UserHoldsSessionLock
from .scan_note import ScanNoteSerializer


class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotation
        fields = ['id', 'decision', 'created', 'creator']
        ref_name = 'scan_decision'


class ScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = ['id', 'scan_id', 'scan_type', 'notes', 'experiment', 'site', 'decisions']

    notes = ScanNoteSerializer(many=True)
    decisions = DecisionSerializer(many=True)


class ScanViewSet(ReadOnlyModelViewSet):
    queryset = Scan.objects.select_related('experiment__session')

    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['experiment', 'site']

    permission_classes = [IsAuthenticated, UserHoldsSessionLock]

    serializer_class = ScanSerializer
