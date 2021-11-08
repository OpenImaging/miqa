from pathlib import Path

from django.http import FileResponse, HttpResponseServerError
from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
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
        fields = ['id', 'frame_number', 'auto_evaluation']
        ref_name = 'scan_frame'

    auto_evaluation = serializers.SerializerMethodField()

    def get_auto_evaluation(self, frame_object):
        try:
            evaluation_object = Evaluation.objects.get(frame=frame_object)
            return EvaluationSerializer(evaluation_object).data
        except Evaluation.DoesNotExist:
            return None


class FrameViewSet(ListModelMixin, GenericViewSet):
    # This ViewSet read-only right now, so we don't need to select_related back to
    # the Project for permission checking.
    queryset = Frame.objects.all()

    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['scan']

    permission_classes = [IsAuthenticated, UserHoldsExperimentLock]

    serializer_class = FrameSerializer

    @action(detail=True)
    def download(self, request, pk=None, **kwargs):
        frame: Frame = self.get_object()
        path: Path = frame.path
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
