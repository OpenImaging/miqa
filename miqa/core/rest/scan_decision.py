from django_filters import rest_framework as filters
from rest_framework import mixins, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from guardian.shortcuts import get_objects_for_user

from miqa.core.models import Experiment, Scan, ScanDecision
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
            'core.view_project',
            with_superuser=False,
        )
        experiments = Experiment.objects.filter(project__in=projects)
        scans = Scan.objects.filter(experiment__in=experiments)
        return ScanDecision.objects.filter(scan__in=scans)

    def create(self, request, *args, **kwargs):
        request_data = request.data
        scan = Scan.objects.get(id=request.data['scan'])
        request_data['scan'] = scan
        request_data['creator'] = request.user

        if not request.user.has_perm('submit_reviews', scan.experiment.project):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        ensure_experiment_lock(request_data['scan'], request_data['creator'])
        new_obj = ScanDecision(**request_data)
        new_obj.save()
        return Response(ScanDecisionSerializer(new_obj).data, status=status.HTTP_201_CREATED)
