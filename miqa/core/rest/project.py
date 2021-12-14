from drf_yasg.utils import no_body, swagger_auto_schema
from guardian.shortcuts import get_objects_for_user, get_users_with_perms, get_perms
from rest_framework import serializers, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Project
from miqa.core.rest.experiment import ExperimentSerializer
from miqa.core.rest.permissions import project_permission_required
from miqa.core.rest.user import UserSerializer
from miqa.core.tasks import export_data, import_data


class ProjectSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['importPath', 'exportPath', 'globalImportExport', 'permissions']

    importPath = serializers.CharField(source='import_path')  # noqa: N815
    exportPath = serializers.CharField(source='export_path')  # noqa: N815
    globalImportExport = serializers.BooleanField(source='global_import_export')  # noqa: N815
    permissions = serializers.SerializerMethodField('get_permissions')

    def get_permissions(self, obj):
        permissions = {
            perm_group: [
                UserSerializer(user).data
                for user in get_users_with_perms(obj, only_with_perms_in=[perm_group])
            ]
            for perm_group in Project.get_read_permission_groups()
        }
        permissions['collaborator'] = [
            x
            for x in permissions['collaborator']
            if x not in permissions['tier_1_reviewer'] and x not in permissions['tier_2_reviewer']
        ]
        permissions['tier_1_reviewer'] = [
            x for x in permissions['tier_1_reviewer'] if x not in permissions['tier_2_reviewer']
        ]

        return permissions


class ProjectTaskOverviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['total_experiments', 'total_scans', 'my_project_role', 'scan_states']

    total_experiments = serializers.SerializerMethodField('get_total_experiments')
    total_scans = serializers.SerializerMethodField('get_total_scans')
    my_project_role = serializers.SerializerMethodField('get_my_project_role')
    scan_states = serializers.SerializerMethodField('get_scan_states')

    def get_total_experiments(self, obj):
        return obj.experiments.count()

    def get_total_scans(self, obj):
        return sum([exp.scans.count() for exp in obj.experiments.all()])

    def get_highest_perm(self, user, project):
        perm_order = Project.get_read_permission_groups()
        return sorted(
            get_perms(user, project),
            key=lambda perm: perm_order.index(perm) if perm in perm_order else -1,
        )[-1]

    def get_my_project_role(self, obj):
        return self.get_highest_perm(self.context['user'], obj)

    def get_scan_states(self, obj):
        def convert_state_string(last_reviewer_role):
            if last_reviewer_role == 'tier_2_reviewer':
                return 'complete'
            elif last_reviewer_role == 'tier_1_reviewer':
                return 'needs tier 2 review'
            else:
                return last_reviewer_role

        return {
            str(scan.id): convert_state_string(
                self.get_highest_perm(scan.decisions.latest('created').creator, obj)
                if scan.decisions.count() > 0
                else 'unreviewed'
            )
            for exp in obj.experiments.all()
            for scan in exp.scans.all()
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


class ProjectViewSet(
    ReadOnlyModelViewSet,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
):
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save(creator=request.user)
        headers = self.get_success_headers(serializer.data)
        return Response(
            ProjectRetrieveSerializer(project).data, status=status.HTTP_201_CREATED, headers=headers
        )

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
            project.global_import_export = request.data['globalImportExport']
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
    @project_permission_required()
    @action(detail=True, methods=['POST'])
    def export(self, request, **kwargs):
        project: Project = self.get_object()

        # tasks sent to celery must use serializable arguments
        export_data(project.id)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        request_body=no_body,
        responses={200: ProjectTaskOverviewSerializer()},
    )
    @project_permission_required()
    @action(detail=True, methods=['GET'])
    def task_overview(self, request, **kwargs):
        project: Project = self.get_object()
        return Response(
            ProjectTaskOverviewSerializer(project, context={'user': request.user}).data,
            status=status.HTTP_200_OK,
        )
