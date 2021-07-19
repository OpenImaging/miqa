from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Annotation, Scan

from .scan_note import ScanNoteSerializer


class DecisionSerializer(serializers.Serializer):
    class Meta:
        model = Annotation
        fields = ['id', 'decision']
        ref_name = 'scan_decision'

    decision = serializers.ChoiceField(choices=Annotation.decision.field.choices)


class ScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = ['id', 'scan_id', 'scan_type', 'notes', 'experiment', 'site', 'decisions']

    notes = ScanNoteSerializer(many=True)
    decisions = DecisionSerializer(many=True)


class ScanViewSet(ReadOnlyModelViewSet):
    queryset = Scan.objects.all()

    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['experiment', 'site']

    serializer_class = ScanSerializer

    @swagger_auto_schema(request_body=DecisionSerializer)
    @action(detail=True, methods=['POST'])
    def decision(self, request, **kwargs):
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scan = self.get_object()
        decision = Annotation(
            decision=serializer.validated_data['decision'], creator=request.user, scan=scan
        )

        decision.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
