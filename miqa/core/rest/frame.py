from pathlib import Path
from typing import Optional

from django.core.exceptions import BadRequest
from django.http import FileResponse, HttpResponseServerError
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from guardian.shortcuts import get_objects_for_user, get_perms
from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from miqa.core.models import Evaluation, Experiment, Frame, Project, Scan
from miqa.core.models.frame import StorageMode
from miqa.core.rest.permissions import project_permission_required
from miqa.core.tasks import evaluate_frame_content

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

    def get_download_url(self, obj: Frame) -> Optional[str]:
        if obj.storage_mode == StorageMode.CONTENT_STORAGE:
            return obj.content.url
        if obj.storage_mode == StorageMode.S3_PATH:
            return obj.s3_download_url
        return None


def is_valid_experiment(experiment_id):
    try:
        Experiment.objects.get(id=experiment_id)
    except Experiment.DoesNotExist:
        raise serializers.ValidationError(f'Experiment {experiment_id} does not exist.')


def is_valid_scan(scan_id):
    try:
        Scan.objects.get(id=scan_id)
    except Scan.DoesNotExist:
        raise serializers.ValidationError(f'Scan {scan_id} does not exist.')


class FrameCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frame
        fields = ['content', 'experiment', 'scan', 'filename', 'frame_number']
        extra_kwargs = {'content': {'required': True}}

    experiment = serializers.CharField(required=False, validators=[is_valid_experiment])
    scan = serializers.CharField(required=False, validators=[is_valid_scan])
    filename = serializers.CharField(required=True)


class FrameContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frame
        fields = ['content', 'scan', 'frame_number']


class FrameViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    filter_backends = [filters.DjangoFilterBackend]
    permission_classes = [IsAuthenticated, UserHoldsExperimentLock]
    serializer_class = FrameSerializer

    def get_queryset(self):
        projects = get_objects_for_user(
            self.request.user,
            [f'core.{perm}' for perm in Project().get_read_permission_groups()],
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
        scan = None
        if 'experiment' in serializer.data:
            experiment = Experiment.objects.get(id=serializer.data['experiment'])

            if not get_perms(request.user, experiment.project):
                Response(status=status.HTTP_403_FORBIDDEN)

            scan = Scan(name=serializer.data['filename'], experiment=experiment)
            scan.save()
        elif 'scan' in serializer.data:
            scan = Scan.objects.get(id=serializer.data['scan'])
            if not scan:
                raise APIException(
                    'Could not create new Frame.', status_code=status.HTTP_400_BAD_REQUEST
                )
            if not get_perms(request.user, scan.experiment.project):
                Response(status=status.HTTP_403_FORBIDDEN)
        else:
            raise APIException(
                'Provide either a parent scan or grandparent experiment for this frame.'
            )

        if not scan:
            raise APIException(
                'Could not create new Frame.', status_code=status.HTTP_400_BAD_REQUEST
            )
        content_serializer = FrameContentSerializer(data=dict(request.data, scan=scan.id))
        content_serializer.is_valid(raise_exception=True)
        new_frame = content_serializer.save()
        evaluate_frame_content.delay(str(new_frame.id))
        return Response(
            FrameSerializer(new_frame).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True)
    @project_permission_required(experiments__scans__frames__pk='pk')
    def download(self, request, pk=None, **kwargs):
        frame: Frame = self.get_object()

        if frame.storage_mode == StorageMode.LOCAL_PATH:
            if not frame.path.is_file():
                return HttpResponseServerError('File no longer exists.')

            fd = open(frame.raw_path, 'rb')
            resp = FileResponse(fd, filename=str(frame.frame_number))
            resp['Content-Length'] = frame.size
            return resp
        raise BadRequest('This endpoint is only valid for local files on the server machine.')
