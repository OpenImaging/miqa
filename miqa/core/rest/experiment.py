from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin

from miqa.core.models import Experiment
from miqa.core.rest.session import SessionSerializer


class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = ['id', 'name', 'note', 'session']

    session = SessionSerializer()


class ExperimentViewSet(NestedViewSetMixin, ReadOnlyModelViewSet):
    queryset = Experiment.objects.all()

    permission_classes = [AllowAny]
    serializer_class = ExperimentSerializer
