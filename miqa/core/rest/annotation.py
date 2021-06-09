from django.contrib.auth.models import User
from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ModelViewSet

from miqa.core.models import Annotation


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        ref_name = 'annotation_user'


class DecisionSerializer(serializers.Serializer):
    class Meta:
        model = Annotation
        fields = ['id', 'decision', 'creator', 'created']
        ref_name = 'annotation_decision'

    decision = serializers.ChoiceField(choices=Annotation.decision.field.choices)
    created = serializers.DateTimeField()
    creator = UserSerializer()


class AnnotationViewSet(ModelViewSet):
    queryset = Annotation.objects.all()

    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['scan', 'creator']

    permission_classes = [AllowAny]
    serializer_class = DecisionSerializer
