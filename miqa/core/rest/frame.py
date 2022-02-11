from pathlib import Path

from django.core.exceptions import BadRequest
from django.http import FileResponse, HttpResponseServerError
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from guardian.shortcuts import get_objects_for_user, get_perms
from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from miqa.core.models import Evaluation, Experiment, Frame, Project, Scan
from miqa.core.models.frame import StorageMode
from miqa.core.rest.permissions import project_permission_required

from .permissions import UserHoldsExperimentLock


class EvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluation
        fields = ['results', 'evaluation_model']


class FrameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frame
        fields = [
            'id',
            'frame_number',
            'frame_evaluation',
            'extension',
            'download_url',
        ]
        ref_name = 'scan_frame'

    frame_evaluation = EvaluationSerializer()
    extension = serializers.SerializerMethodField('get_extension')
    download_url = serializers.SerializerMethodField('get_download_url')

    def get_extension(self, obj):
        if obj.content:
            filename = obj.content.name
        else:
            filename = obj.raw_path
        return ''.join(Path(filename).suffixes)

    def get_download_url(self, obj):
        if obj.storage_mode == StorageMode.CONTENT_STORAGE:
            return obj.content.url


def is_valid_experiment(experiment_id):
    try:
        Experiment.objects.get(id=experiment_id)
    except Experiment.DoesNotExist:
        raise serializers.ValidationError(f'Experiment {experiment_id} does not exist.')


class FrameCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frame
        fields = ['content', 'experiment', 'filename']
        extra_kwargs = {'content': {'required': True}}

    experiment = serializers.CharField(required=True, validators=[is_valid_experiment])
    filename = serializers.CharField(required=True)


class FrameContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frame
        fields = ['content', 'scan']


class FrameViewSet(ListModelMixin, GenericViewSet, mixins.CreateModelMixin):
    filter_backends = [filters.DjangoFilterBackend]
    permission_classes = [IsAuthenticated, UserHoldsExperimentLock]
    serializer_class = FrameSerializer

    def get_queryset(self):
        projects = get_objects_for_user(
            self.request.user,
            [f'core.{perm}' for perm in Project.get_read_permission_groups()],
            any_perm=True,
        )
        return Frame.objects.filter(scan__experiment__project__in=projects)

    @swagger_auto_schema(
        request_body=FrameCreateSerializer(),
        responses={201: FrameSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = FrameCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        experiment = Experiment.objects.get(id=serializer.data['experiment'])

        if not get_perms(request.user, experiment.project):
            Response(status=status.HTTP_401_UNAUTHORIZED)

        new_scan = Scan(name=serializer.data['filename'], experiment=experiment)
        new_scan.save()

        content_serializer = FrameContentSerializer(
            data={'content': request.data['content'], 'scan': new_scan.pk}
        )
        content_serializer.is_valid(raise_exception=True)
        new_frame = content_serializer.save()
        return Response(
            FrameSerializer(new_frame).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True)
    @project_permission_required(experiments__scans__frames__pk='pk')
    def download(self, request, pk=None, **kwargs):
        frame: Frame = self.get_object()

        if frame.storage_mode == StorageMode.LOCAL_PATH:
            print(frame.path)
            if not frame.path.is_file():
                return HttpResponseServerError('File no longer exists.')

            fd = open(frame.raw_path, 'rb')
            resp = FileResponse(fd, filename=str(frame.frame_number))
            resp['Content-Length'] = frame.size
            return resp
        raise BadRequest('This endpoint is only valid for local files on the server machine.')
