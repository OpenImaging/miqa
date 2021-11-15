from django_filters import rest_framework as filters
from guardian.shortcuts import get_objects_for_user, get_perms
from rest_framework import mixins, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from miqa.core.models import Project, Scan, ScanDecision
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
    mixins.ListModelMixin,
    GenericViewSet,
):
    filter_backends = [filters.DjangoFilterBackend]
    permission_classes = [IsAuthenticated, UserHoldsExperimentLock]
    serializer_class = ScanDecisionSerializer

    def get_queryset(self):
        projects = get_objects_for_user(
            self.request.user,
            [f'core.{perm}' for perm in Project.get_read_permission_groups()],
            any_perm=True,
        )
        return ScanDecision.objects.filter(scan__experiment__project__in=projects)

    # cannot use project_permission_required decorator because no pk is provided
    def create(self, request, **kwargs):
        request_data = request.data
        scan = Scan.objects.get(id=request.data['scan'])
        if get_perms(request.user, scan.experiment.project) == []:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        request_data['scan'] = scan
        request_data['creator'] = request.user

        ensure_experiment_lock(request_data['scan'], request_data['creator'])
        new_obj = ScanDecision(**request_data)
        new_obj.save()
        return Response(ScanDecisionSerializer(new_obj).data, status=status.HTTP_201_CREATED)
