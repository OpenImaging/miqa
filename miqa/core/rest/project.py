from drf_yasg.utils import no_body, swagger_auto_schema
from guardian.shortcuts import get_objects_for_user, get_users_with_perms
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Project
from miqa.core.rest.experiment import ExperimentSerializer
from miqa.core.rest.permissions import project_permission_required
from miqa.core.tasks import export_data, import_data


class ProjectSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['importPath', 'exportPath', 'permissions']

    importPath = serializers.CharField(source='import_path')  # noqa: N815
    exportPath = serializers.CharField(source='export_path')  # noqa: N815
    permissions = serializers.SerializerMethodField('get_permissions')

    def get_permissions(self, obj):
        return {
            perm_group: [
                user.username for user in get_users_with_perms(obj, only_with_perms_in=[perm_group])
            ]
            for perm_group in Project.get_read_permission_groups()
        }


class ProjectRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'experiments', 'settings']
        ref_name = 'project'

    experiments = ExperimentSerializer(many=True)
    settings = serializers.SerializerMethodField('get_settings')

    def get_settings(self, obj):
        return ProjectSettingsSerializer(obj).data


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name']
        ref_name = 'projects'


class ProjectViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        projects = get_objects_for_user(
            self.request.user,
            [f'core.{perm}' for perm in Project.get_read_permission_groups()],
            any_perm=True,
        )
        if self.action == 'retrieve':
            return projects.prefetch_related(
                'experiments__scans__frames', 'experiments__scans__decisions'
            )
        else:
            return projects.all()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProjectRetrieveSerializer
        else:
            return ProjectSerializer

    @swagger_auto_schema(
        method='GET',
        responses={200: ProjectSettingsSerializer()},
    )
    @swagger_auto_schema(
        method='PUT',
        request_body=ProjectSettingsSerializer(),
        responses={200: ProjectSettingsSerializer()},
    )
    @project_permission_required()
    @action(
        detail=True,
        url_path='settings',
        url_name='settings',
        methods=['GET', 'PUT'],
    )
    def settings_(self, request, **kwargs):
        project: Project = self.get_object()
        if request.method == 'PUT':
            if not request.user.is_superuser:
                return Response(status=status.HTTP_401_UNAUTHORIZED)

            # TODO: need help changing the auto schema to expect permissions object

            if 'permissions' in request.data:
                for key, user_list in request.data['permissions'].items():
                    try:
                        project.update_group(key, user_list)
                    except ValueError as e:
                        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

            project.import_path = request.data['importPath']
            project.export_path = request.data['exportPath']
            project.full_clean()
            project.save()
        serializer = ProjectSettingsSerializer(project)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=no_body,
        responses={204: 'Import succeeded.'},
    )
    @project_permission_required(superuser_access=True)
    @action(detail=True, url_path='import', url_name='import', methods=['POST'])
    def import_(self, request, **kwargs):
        project: Project = self.get_object()

        # tasks sent to celery must use serializable arguments
        import_data(request.user.id, project.id)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        request_body=no_body,
        responses={204: 'Export succeeded.'},
    )
    @project_permission_required(superuser_access=True)
    @action(detail=True, methods=['POST'])
    def export(self, request, **kwargs):
        project: Project = self.get_object()

        # tasks sent to celery must use serializable arguments
        export_data(project.id)

        return Response(status=status.HTTP_204_NO_CONTENT)
