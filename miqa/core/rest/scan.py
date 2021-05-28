from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Scan

from .scan_note import ScanNoteSerializer


class ScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = ['id', 'scan_id', 'scan_type', 'notes', 'decision', 'experiment', 'site']

    notes = ScanNoteSerializer(many=True)
    decision = serializers.ChoiceField(choices=Scan.decision.field.choices)


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=Scan.decision.field.choices)


class ScanViewSet(ReadOnlyModelViewSet):
    queryset = Scan.objects.all()

    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['experiment', 'site']

    permission_classes = [AllowAny]
    serializer_class = ScanSerializer

    @swagger_auto_schema(request_body=DecisionSerializer)
    @action(detail=True, methods=['POST'])
    def decision(self, request, **kwargs):
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data['decision']
        scan = self.get_object()

        scan.decision = decision
        scan.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
