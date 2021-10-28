from django_filters import rest_framework as filters
from rest_framework import mixins, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from miqa.core.models import Scan, ScanDecision
from miqa.core.rest.user import UserSerializer

from .permissions import UserHoldsExperimentLock, ensure_experiment_lock


class ScanDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanDecision
        fields = ['id', 'decision', 'creator', 'created', 'note']
        read_only_fields = ['created', 'creator']
        ref_name = 'scan_decision'

    creator = UserSerializer()


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

    def create(self, request, *args, **kwargs):
        request_data = request.data
        request_data['scan'] = Scan.objects.get(id=request.data['scan'])
        request_data['creator'] = request.user
        ensure_experiment_lock(request_data['scan'], request_data['creator'])
        new_obj = ScanDecision(**request_data)
        new_obj.save()
        return Response(ScanDecisionSerializer(new_obj).data, status=status.HTTP_201_CREATED)
