from django_filters import rest_framework as filters
from rest_framework import mixins, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from miqa.core.models import Annotation


class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotation
        fields = ['id', 'decision', 'creator', 'created', 'scan']
        read_only_fields = ['created', 'creator']
        ref_name = 'annotation_decision'


class AnnotationViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Annotation.objects.select_related('scan__experiment__session')

    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['scan', 'creator']

    permission_classes = [IsAuthenticated]

    serializer_class = DecisionSerializer

    def perform_create(self, serializer: DecisionSerializer):
        user = self.request.user
        # ensure_session_lock(serializer.validated_data['scan'], user)
        serializer.save(creator=user)
