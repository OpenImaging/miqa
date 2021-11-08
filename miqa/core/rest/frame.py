from pathlib import Path

from django.http import FileResponse, HttpResponseServerError
from django_filters import rest_framework as filters
from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from miqa.core.models import Evaluation, Frame

from .permissions import UserHoldsExperimentLock


class EvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluation
        fields = ['results', 'evaluation_model']


class FrameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frame
        fields = ['id', 'frame_number', 'frame_evaluation']
        ref_name = 'scan_frame'

    frame_evaluation = EvaluationSerializer()


class FrameViewSet(ListModelMixin, GenericViewSet):
    filter_backends = [filters.DjangoFilterBackend]
    permission_classes = [IsAuthenticated, UserHoldsExperimentLock]
    serializer_class = FrameSerializer

    def get_queryset(self):
        projects = get_objects_for_user(
            self.request.user,
            'core.view_project',
            with_superuser=False,
        )
        return Frame.objects.filter(scan__experiment__project__in=projects)

    @action(detail=True)
    def download(self, request, pk=None, **kwargs):
        frame: Frame = self.get_object()
        path: Path = frame.path

        if not request.user.has_perm('view_project', frame.scan.experiment.project):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        if not path.is_file():
            return HttpResponseServerError('File no longer exists.')

        # send client zarr data instead when client is ready
        # path: Path = frame.zarr_path
        # if not path.exists():
        #     return HttpResponseServerError('File no longer exists.')

        fd = open(path, 'rb')
        resp = FileResponse(fd, filename=str(frame.frame_number))
        resp['Content-Length'] = frame.size
        return resp
