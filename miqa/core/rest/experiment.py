from django.contrib.auth.models import User
from django.db import transaction
from django_filters import rest_framework as filters
from drf_yasg.utils import no_body, swagger_auto_schema
from guardian.shortcuts import get_objects_for_user, get_perms
from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.fields import UUIDField
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Experiment, Project, ScanDecision
from miqa.core.rest.permissions import project_permission_required
from miqa.core.rest.scan import ScanSerializer

from .permissions import ArchivedProject, LockContention, UserHoldsExperimentLock


class LockOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']
        ref_name = 'lock_owner'


class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanDecision
        fields = ['id', 'decision']

    decision = serializers.ChoiceField(choices=ScanDecision.decision.field.choices)


class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = ['id', 'name', 'lock_owner', 'scans', 'project', 'note']
        ref_name = 'project_experiment'

    scans = ScanSerializer(many=True)
    lock_owner = LockOwnerSerializer()
    project = serializers.PrimaryKeyRelatedField(read_only=True, pk_field=UUIDField())


class ExperimentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = ['name', 'project']

    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), pk_field=UUIDField()
    )


class ExperimentViewSet(ReadOnlyModelViewSet, mixins.CreateModelMixin):
    # Our default serializer nests its experiment (not sure why though)

    filter_backends = [filters.DjangoFilterBackend]
    permission_classes = [IsAuthenticated, UserHoldsExperimentLock]
    serializer_class = ExperimentSerializer

    def get_queryset(self):
        projects = get_objects_for_user(
            self.request.user,
            [f'core.{perm}' for perm in Project.get_read_permission_groups()],
            any_perm=True,
        )
        return Experiment.objects.filter(project__in=projects)

    @swagger_auto_schema(
        request_body=ExperimentCreateSerializer(),
        responses={201: ExperimentSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = ExperimentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = Project.objects.get(id=serializer.data['project'])
        if not get_perms(request.user, project):
            Response(status=status.HTTP_401_UNAUTHORIZED)
        experiment = Experiment(
            project=project,
            name=serializer.data['name'],
            lock_owner=None,
        )
        experiment.save()
        return Response(
            ExperimentSerializer(experiment).data,
            status=status.HTTP_201_CREATED,
        )

    @project_permission_required(experiments__pk='pk')
    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    def note(self, request, pk=None):
        experiment_object = self.get_object()
        experiment_object.note = request.data['note']
        experiment_object.save()
        return Response(
            ExperimentSerializer(experiment_object).data, status=status.HTTP_201_CREATED
        )

    @swagger_auto_schema(
        request_body=no_body,
        responses={
            200: 'Lock acquired.',
            204: 'Lock already owned',
            409: 'The lock is held by a different user.',
        },
    )
    @project_permission_required(review_access=True, experiments__pk='pk')
    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    def lock(self, request, pk=None):
        """Acquire the exclusive write lock on this experiment."""
        with transaction.atomic():
            experiment: Experiment = Experiment.objects.select_for_update().get(pk=pk)
            if experiment.project.archived:
                raise ArchivedProject()
            if (
                experiment.lock_owner is not None
                and experiment.lock_owner != request.user
                and not (request.user.is_superuser and 'force' in request.data)
            ):
                raise LockContention()

            previously_locked_experiments = Experiment.objects.filter(lock_owner=request.user)
            for previously_locked_experiment in previously_locked_experiments:
                previously_locked_experiment.lock_owner = None
                previously_locked_experiment.save(update_fields=['lock_owner'])
            experiment.lock_owner = request.user
            experiment.save(update_fields=['lock_owner'])

            return Response(
                ExperimentSerializer(experiment).data,
                status=status.HTTP_200_OK,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        request_body=no_body,
        responses={
            200: 'Lock released.',
            204: 'Lock not yet acquired for release.',
            409: 'The lock is held by a different user.',
        },
    )
    @project_permission_required(review_access=True, experiments__pk='pk')
    @lock.mapping.delete
    def release_lock(self, request, pk=None):
        """Release the exclusive write lock on this experiment."""
        with transaction.atomic():
            experiment: Experiment = Experiment.objects.select_for_update().get(pk=pk)

            if experiment.lock_owner is not None and experiment.lock_owner != request.user:
                raise LockContention()

            if experiment.lock_owner is not None:
                experiment.lock_owner = None
                experiment.save(update_fields=['lock_owner'])

                return Response(
                    ExperimentSerializer(experiment).data,
                    status=status.HTTP_200_OK,
                )
        return Response(status=status.HTTP_204_NO_CONTENT)
