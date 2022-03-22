from django.conf import settings
from drf_yasg.utils import no_body, swagger_auto_schema
from guardian.shortcuts import get_objects_for_user, get_users_with_perms
from rest_framework import mixins, serializers, status
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
        fields = ['import_path', 'export_path', 'permissions', 'default_email_recipients']

    permissions = serializers.SerializerMethodField('get_permissions')
    default_email_recipients = serializers.SerializerMethodField('get_default_email_recipients')

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

    def get_default_email_recipients(self, obj):
        if obj.default_email_recipients == '':
            return []
        return obj.default_email_recipients.split('\n')


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

    def get_my_project_role(self, obj):
        return obj.get_user_role(self.context['user'])

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
                obj.get_user_role(scan.decisions.latest('created').creator)
                if scan.decisions.count() > 0
                else 'unreviewed'
            )
            for exp in obj.experiments.all()
            for scan in exp.scans.all()
        }


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'status', 'experiments', 'settings', 'creator']
        ref_name = 'projects'

    status = serializers.SerializerMethodField('get_status')
    experiments = ExperimentSerializer(many=True, required=False)
    settings = serializers.SerializerMethodField('get_settings')
    creator = serializers.SerializerMethodField('get_creator')

    def get_status(self, obj):
        return obj.get_status()

    def get_settings(self, obj):
        return ProjectSettingsSerializer(obj).data

    def get_creator(self, obj):
        return obj.creator.username


class ProjectViewSet(
    ReadOnlyModelViewSet,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectSerializer

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

    def create(self, request, *args, **kwargs):
        if not settings.NORMAL_USERS_CAN_CREATE_PROJECTS and not request.user.is_superuser:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save(creator=request.user)
        project.update_group('tier_2_reviewer', [request.user])
        headers = self.get_success_headers(serializer.data)
        return Response(
            self.get_serializer(project).data, status=status.HTTP_201_CREATED, headers=headers
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
            if not (request.user.is_superuser or request.user == project.creator):
                return Response(status=status.HTTP_401_UNAUTHORIZED)

            # TODO: need help changing the auto schema to expect permissions object

            if 'permissions' in request.data:
                for key, user_list in request.data['permissions'].items():
                    try:
                        project.update_group(key, user_list)
                    except ValueError as e:
                        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

            if 'default_email_recipients' in request.data:
                project.default_email_recipients = "\n".join(
                    request.data['default_email_recipients']
                )

            project.import_path = request.data['import_path']
            project.export_path = request.data['export_path']
            project.full_clean()
            project.save()
        serializer = ProjectSettingsSerializer(project)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=no_body,
        responses={204: 'Import succeeded.'},
    )
    @project_permission_required()
    @action(detail=True, url_path='import', url_name='import', methods=['POST'])
    def import_(self, request, **kwargs):
        project: Project = self.get_object()

        # tasks sent to celery must use serializable arguments
        error_list = import_data(project.id)
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
