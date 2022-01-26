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
        if request.method == 'PUT':
            global_settings = self.get_object()
            global_settings.import_path = request.data['importPath']
            global_settings.export_path = request.data['exportPath']
            global_settings.full_clean()
            global_settings.save()
        return Response(GlobalSettingsSerializer(self.get_object()).data, status=status.HTTP_200_OK)

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
