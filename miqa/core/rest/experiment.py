from django.contrib.auth.models import User
from django.db import transaction
from django_filters import rest_framework as filters
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Experiment
from miqa.core.rest.session import SessionSerializer, ExperimentSerializer as ExperimentRetrieveSerializer

from .permissions import ArchivedSession, LockContention, UserHoldsExperimentLock


class LockOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']
        ref_name = 'lock_owner'


class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = ['id', 'name', 'note', 'session', 'lock_owner']

    session = SessionSerializer()
    lock_owner = LockOwnerSerializer()


class ExperimentViewSet(ReadOnlyModelViewSet):
    # Our default serializer nests its experiment (not sure why though)
    queryset = Experiment.objects.select_related('session')

    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['session']

    permission_classes = [IsAuthenticated, UserHoldsExperimentLock]

    serializer_class = ExperimentSerializer

    @swagger_auto_schema(
        method='GET',
        responses={200: ExperimentRetrieveSerializer()},
    )
    @action(detail=True, methods=['GET'])
    def deep(self, request, **kwargs):
        experiment: Experiment = self.get_object()
        serializer = ExperimentRetrieveSerializer(experiment)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=no_body,
        responses={
            204: 'Lock acquired.',
            409: 'The lock is held by a different user.',
        },
    )
    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    def lock(self, request, pk=None):
        """Acquire the exclusive write lock on this experiment."""
        with transaction.atomic():
            experiment: Experiment = Experiment.objects.select_for_update().get(pk=pk)

            if experiment.session.archived:
                raise ArchivedSession()

            if experiment.lock_owner is not None and experiment.lock_owner != request.user:
                raise LockContention()

            if experiment.lock_owner is None:
                experiment.lock_owner = request.user
                experiment.save(update_fields=['lock_owner'])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        request_body=no_body,
        responses={
            204: 'Lock released.',
            409: 'The lock is held by a different user.',
        },
    )
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

        return Response(status=status.HTTP_204_NO_CONTENT)
