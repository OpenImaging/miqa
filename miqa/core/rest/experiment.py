from django.contrib.auth.models import User
from django.db import transaction
from django_filters import rest_framework as filters
from drf_yasg.utils import no_body, swagger_auto_schema
from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Experiment, ScanDecision
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


class ExperimentViewSet(ReadOnlyModelViewSet):
    # Our default serializer nests its experiment (not sure why though)

    filter_backends = [filters.DjangoFilterBackend]
    permission_classes = [IsAuthenticated, UserHoldsExperimentLock]
    serializer_class = ExperimentSerializer

    def get_queryset(self):
        projects = get_objects_for_user(
            self.request.user,
            'core.view_project',
            with_superuser=False,
        )
        return Experiment.objects.filter(project__in=projects)

    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    def note(self, request, pk=None):
        experiment_object = self.get_object()
        # superusers, reviewers, and collaborators can all edit experiment notes
        if not request.user.has_perm('view_project', experiment_object.project):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

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
    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    def lock(self, request, pk=None):
        """Acquire the exclusive write lock on this experiment."""
        with transaction.atomic():
            experiment: Experiment = Experiment.objects.select_for_update().get(pk=pk)

            # only reviewers and superusers can lock/unlock
            if not request.user.has_perm('submit_reviews', experiment.project):
                return Response(status=status.HTTP_401_UNAUTHORIZED)

            if experiment.project.archived:
                raise ArchivedProject()

            if experiment.lock_owner is not None and experiment.lock_owner != request.user:
                raise LockContention()

            if experiment.lock_owner is None or experiment.lock_owner == request.user:
                previously_locked_experiments = Experiment.objects.filter(lock_owner=request.user)
                for previously_locked_experiment in previously_locked_experiments:
                    previously_locked_experiment.lock_owner = None
                    previously_locked_experiment.save()
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
    @lock.mapping.delete
    def release_lock(self, request, pk=None):
        """Release the exclusive write lock on this experiment."""
        with transaction.atomic():
            experiment: Experiment = Experiment.objects.select_for_update().get(pk=pk)

            # only reviewers and superusers can lock/unlock
            if not request.user.has_perm('submit_reviews', experiment.project):
                return Response(status=status.HTTP_401_UNAUTHORIZED)

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
