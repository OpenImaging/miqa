from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from miqa.core.models import GlobalSettings
from miqa.core.tasks import export_data, import_data


class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)


class GlobalSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSettings
        exclude = ['id']


class GlobalSettingsViewSet(ViewSet):
    def get_object(self):
        return GlobalSettings.load()

    def get_permissions(self):
        if self.request.method != 'PUT':
            return [IsAuthenticated()]
        else:
            return [IsSuperUser()]

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
        global_settings = self.get_object()
        if request.method == 'PUT':
            global_settings.import_path = request.data['import_path']
            global_settings.export_path = request.data['export_path']
            global_settings.full_clean()
            global_settings.save()
        return Response(GlobalSettingsSerializer(global_settings).data)

    @swagger_auto_schema(responses={204: 'Import succeeded.'})
    @action(
        detail=False,
        url_path='import',
        methods=['POST'],
    )
    def import_(self, request, **kwargs):
        error_list = import_data(None)
        if len(error_list) > 0:
            return Response(
                {
                    'detail': 'The following errors occurred during import. \
                        Objects were still created for missing files, \
                        but these objects will be non-functional until the file is present.',
                    'errors': error_list,
                }
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(responses={204: 'Export succeeded.'})
    @action(
        detail=False,
        url_path='export',
        methods=['POST'],
    )
    def export_(self, request, **kwargs):
        export_data(None)
        return Response(status=status.HTTP_204_NO_CONTENT)
