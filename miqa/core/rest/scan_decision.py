from django_filters import rest_framework as filters
from guardian.shortcuts import get_objects_for_user
from rest_framework import mixins, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from miqa.core.models import Project, Scan, ScanDecision
from miqa.core.rest.user import UserSerializer
from miqa.core.rest.permissions import project_permission_required

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
        )
        return ScanDecision.objects.filter(scan__experiment__project__in=projects)

    @project_permission_required(review_access=True, experiments__scans__decisions__pk='pk')
    def create(self, request, *args, **kwargs):
        request_data = request.data
        scan = Scan.objects.get(id=request.data['scan'])
        request_data['scan'] = scan
        request_data['creator'] = request.user

        ensure_experiment_lock(request_data['scan'], request_data['creator'])
        new_obj = ScanDecision(**request_data)
        new_obj.save()
        return Response(ScanDecisionSerializer(new_obj).data, status=status.HTTP_201_CREATED)
