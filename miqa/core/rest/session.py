from rest_framework import serializers
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.models import Session


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['id', 'name']


class SessionSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['importpath', 'exportpath']

    importpath = serializers.CharField(source='import_path')
    exportpath = serializers.CharField(source='export_path')


class SessionViewSet(ReadOnlyModelViewSet):
    queryset = Session.objects.all()

    permission_classes = [AllowAny]
    serializer_class = SessionSerializer

    @swagger_auto_schema(
        method='GET',
        responses={200: SessionSettingsSerializer()},
    )
    @swagger_auto_schema(
        method='PUT',
        request_body=SessionSettingsSerializer(),
        responses={200: SessionSettingsSerializer()},
    )
    @action(detail=True, url_path='settings', url_name='settings', methods=['GET', 'PUT'])
    def settings_(self, request, **kwargs):
        session: Session = self.get_object()
        if request.method == 'GET':
            serializer = SessionSettingsSerializer(instance=session)
        elif request.method == 'PUT':
            serializer = SessionSettingsSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            session.import_path = serializer.data['importpath']
            session.export_path = serializer.data['exportpath']
            session.save()
        return Response(serializer.data)
