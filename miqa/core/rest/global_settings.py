from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from miqa.core.models import GlobalSettings
from miqa.core.tasks import export_data, import_data


class GlobalSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSettings
        exclude = ['id']


class GlobalSettingsViewSet(ViewSet):
    def get_object(self):
        return GlobalSettings.load()

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        else:
            return [IsAdminUser()]

    @swagger_auto_schema(
        method='GET',
        responses={200: GlobalSettingsSerializer()},
    )
    @swagger_auto_schema(
        method='PUT',
        request_body=GlobalSettingsSerializer(),
        responses={200: GlobalSettingsSerializer()},
    )
    @action(
        detail=False,
        url_path='settings',
        methods=['GET', 'PUT'],
    )
    def settings_(self, request):
        serializer = GlobalSettingsSerializer(self.get_object())
        if request.method == 'PUT':
            serializer = GlobalSettingsSerializer(self.get_object(), data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(responses={204: 'Import succeeded.'})
    @action(
        detail=False,
        url_path='import',
        methods=['POST'],
    )
    def import_(self, request, **kwargs):
        import_data('global')
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(responses={204: 'Export succeeded.'})
    @action(
        detail=False,
        url_path='export',
        methods=['POST'],
    )
    def export_(self, request, **kwargs):
        export_data('global')
        return Response(status=status.HTTP_204_NO_CONTENT)
