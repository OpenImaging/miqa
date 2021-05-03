from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Site


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ['id', 'name']


class SiteViewSet(ReadOnlyModelViewSet):
    queryset = Site.objects.all()

    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['session']

    permission_classes = [AllowAny]
    serializer_class = SiteSerializer
