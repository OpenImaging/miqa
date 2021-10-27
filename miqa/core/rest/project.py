from django.contrib.auth.models import User
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Annotation, Evaluation, Experiment, Image, Project, Scan, ScanNote
from miqa.core.tasks import export_data, import_data


class LockOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']
        ref_name = 'lock_owner'


class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotation
        fields = ['id', 'decision']

    decision = serializers.ChoiceField(choices=Annotation.decision.field.choices)


class EvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluation
        fields = ['results', 'evaluation_model']


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ['id', 'frame_number', 'auto_evaluation']
        ref_name = 'scan_image'

    auto_evaluation = serializers.SerializerMethodField()

    def get_auto_evaluation(self, image_object):
        try:
            evaluation_object = Evaluation.objects.get(image=image_object)
            return EvaluationSerializer(evaluation_object).data
        except Evaluation.DoesNotExist:
            return None


class ScanNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanNote
        fields = ['id', 'note', 'created', 'modified']
        ref_name = 'scan_note'

    # Override the default DateTimeFields to disable read_only=True
    created = serializers.DateTimeField()
    modified = serializers.DateTimeField()


class ScanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scan
        fields = ['id', 'name', 'notes', 'decisions', 'images', 'scan_type']
        ref_name = 'experiment_scan'

    notes = ScanNoteSerializer(many=True)
    images = ImageSerializer(many=True)
    decisions = DecisionSerializer(many=True)


class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = ['id', 'name', 'lock_owner', 'scans', 'project', 'note']
        ref_name = 'project_experiment'

    scans = ScanSerializer(many=True)
    lock_owner = LockOwnerSerializer()


class ProjectRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'experiments', 'import_path', 'export_path']
        ref_name = 'project'

    experiments = ExperimentSerializer(many=True)


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name']
        ref_name = 'projects'


class ProjectSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['importPath', 'exportPath']

    importPath = serializers.CharField(source='import_path')  # noqa: N815
    exportPath = serializers.CharField(source='export_path')  # noqa: N815


class ProjectViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.action == 'retrieve':
            return Project.objects.prefetch_related(
                'experiments__scans__images', 'experiments__scans__notes'
            )
        else:
            return Project.objects.all()

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
    @action(
        detail=True,
        url_path='settings',
        url_name='settings',
        methods=['GET', 'PUT'],
        permission_classes=[IsAdminUser],
    )
    def settings_(self, request, **kwargs):
        project: Project = self.get_object()
        if request.method == 'GET':
            serializer = ProjectSettingsSerializer(instance=project)
        elif request.method == 'PUT':
            serializer = ProjectSettingsSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            project.import_path = serializer.data['importPath']
            project.export_path = serializer.data['exportPath']
            project.full_clean()
            project.save()
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=no_body,
        responses={204: 'Import succeeded.'},
    )
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
    @action(detail=True, methods=['POST'])
    def export(self, request, **kwargs):
        project: Project = self.get_object()

        # tasks sent to celery must use serializable arguments
        export_data(project.id)

        return Response(status=status.HTTP_204_NO_CONTENT)
