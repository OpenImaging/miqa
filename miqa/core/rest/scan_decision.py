from django_filters import rest_framework as filters
from rest_framework import mixins, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from miqa.core.models import ScanDecision

from .permissions import UserHoldsExperimentLock, ensure_experiment_lock


class ScanDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanDecision
        fields = ['id', 'decision', 'creator', 'created', 'scan']
        read_only_fields = ['created', 'creator']
        ref_name = 'scan_decision'


class ScanDecisionViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = ScanDecision.objects.select_related('scan__experiment__project')

    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['scan', 'creator']

    permission_classes = [IsAuthenticated, UserHoldsExperimentLock]

    serializer_class = ScanDecisionSerializer

    def perform_create(self, serializer: ScanDecisionSerializer):
        user = self.request.user
        ensure_experiment_lock(serializer.validated_data['scan'], user)
        serializer.save(creator=user)
