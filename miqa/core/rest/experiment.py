from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Experiment
from miqa.core.rest.session import SessionSerializer

from .permissions import UserHoldsSessionLock


class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = ['id', 'name', 'note', 'session']

    session = SessionSerializer()


class ExperimentViewSet(ReadOnlyModelViewSet):
    # Our default serializer nests its Session (not sure why though)
    queryset = Experiment.objects.select_related('session')

    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['session']

    permission_classes = [IsAuthenticated, UserHoldsSessionLock]

    serializer_class = ExperimentSerializer
