import os
import re
from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.conversion.csv_to_json import csvContentToJsonObject
from miqa.core.models import Scan, Session, Site, Experiment, Image, ScanNote
from miqa.core.models.scan import ScanDecision
from miqa.core.schema.data_import import schema

from jsonschema import validate
from jsonschema.exceptions import ValidationError as JSONValidationError


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

    @swagger_auto_schema(
        request_body=no_body,
        responses={204: 'No Content.'},
    )
    @action(detail=True, url_path='import', url_name='import', methods=['POST'])
    def import_(self, request, **kwargs):
        session: Session = self.get_object()
        with open(session.import_path) as fd:
            csv_content = fd.read()
            try:
                json_content = csvContentToJsonObject(csv_content)
                validate(json_content, schema)
            except (JSONValidationError, Exception) as inst:
                Response({"error": 'Invalid CSV file: {0}'.format(inst.message)})

        print(json_content)
        data_root = json_content['data_root']

        for site in json_content['sites']:
            # TODO a different user will result in a duplicate site
            Site.objects.get_or_create(name=site['id'], session=session, creator=request.user)

        for experiment in json_content['experiments']:
            # TODO a different user or note will result in a duplicate experiment
            Experiment.objects.get_or_create(
                name=experiment['id'],
                note=experiment['note'],
                session=session,
            )
        for scan in json_content['scans']:
            experiment = Experiment.objects.get(name=scan['experiment_id'], session=session)
            site = Site.objects.get(name=scan['site_id'], session=session, creator=request.user)
            decision = ScanDecision.from_rating(scan['decision'])
            scan_model, _created = Scan.objects.get_or_create(
                scan_id=scan['id'],
                scan_type=scan['type'],
                decision=decision,
                note=scan['note'],
                experiment=experiment,
                site=site,
                # TODO session?
            )
            if 'images' in scan:
                # TODO implement this
                raise Exception('use imagePattern for now')
            # TODO change this to image_pattern in the schema
            elif 'imagePattern' in scan:
                image_pattern = re.compile(scan['imagePattern'])
                image_dir = os.path.join(data_root, scan['path'])
                for image_file in os.listdir(image_dir):
                    if image_pattern.fullmatch(image_file):
                        Image.objects.get_or_create(
                            name=image_file,
                            raw_path=os.path.join(image_dir, image_file),
                            scan=scan_model,
                        )
            else:
                # TODO handle gracefully
                raise Exception('No images in scan')
        return Response(status=status.HTTP_204_NO_CONTENT)
