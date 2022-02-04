from django.http import FileResponse, HttpResponseRedirect, HttpResponseServerError
from django_filters import rest_framework as filters
from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from miqa.core.models import Evaluation, Frame, Project
from miqa.core.rest.permissions import project_permission_required

from .permissions import UserHoldsExperimentLock


class EvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluation
        fields = ['results', 'evaluation_model']


class FrameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frame
        fields = ['id', 'frame_number', 'frame_evaluation', 'extension']
        ref_name = 'scan_frame'

    frame_evaluation = EvaluationSerializer()
    extension = serializers.SerializerMethodField('get_extension')

    def get_extension(self, obj):
        return ''.join(obj.path.suffixes)


class FrameContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frame
        fields = ['content']


class FrameViewSet(ListModelMixin, GenericViewSet):
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

    @action(detail=True)
    @project_permission_required(experiments__scans__frames__pk='pk')
    def download_url(self, request, pk=None, **kwargs):
        frame: Frame = self.get_object()

        if frame.is_in_s3:
            return HttpResponseRedirect(frame.s3_download_url)
        else:
            # send client zarr data instead when client is ready
            # path: Path = frame.zarr_path
            # if not path.exists():
            #     return HttpResponseServerError('File no longer exists.')
            if not frame.path.is_file():
                return HttpResponseServerError('File no longer exists.')

            with open(frame.path, 'rb') as fd:
                resp = FileResponse(fd, filename=str(frame.frame_number))
                resp['Content-Length'] = frame.size
                return resp
