from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin

from miqa.core.models import Scan


class ScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = ['id', 'scan_id', 'scan_type', 'note', 'decision', 'experiment', 'site']

    decision = serializers.ChoiceField(choices=Scan.decision.field.choices)


class ScanViewSet(NestedViewSetMixin, ReadOnlyModelViewSet):
    queryset = Scan.objects.all()

    permission_classes = [AllowAny]
    serializer_class = ScanSerializer
