from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Session


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['id', 'name']


class SessionViewSet(ReadOnlyModelViewSet):
    queryset = Session.objects.all()

    permission_classes = [AllowAny]
    serializer_class = SessionSerializer

