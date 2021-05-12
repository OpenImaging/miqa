import os
from pathlib import Path
import re

from drf_yasg.utils import no_body, swagger_auto_schema
from jsonschema import validate
from jsonschema.exceptions import ValidationError as JSONValidationError
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from miqa.core.conversion.csv_to_json import csvContentToJsonObject
from miqa.core.models import Experiment, Image, Scan, Session, Site
from miqa.core.models.scan import ScanDecision
from miqa.core.schema.data_import import schema


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
        responses={204: 'Import succeeded.'},
    )
    @action(detail=True, url_path='import', url_name='import', methods=['POST'])
    def import_(self, request, **kwargs):
        session: Session = self.get_object()
        with open(session.import_path) as fd:
            csv_content = fd.read()
            try:
                json_content = csvContentToJsonObject(csv_content)
                validate(json_content, schema)  # TODO this should be an internal error
            except (JSONValidationError, Exception) as e:
                raise ValidationError({'error': f'Invalid CSV file: {str(e)}'})

        data_root = Path(json_content['data_root'])

        sites = {
            site['name']: Site.objects.get_or_create(
                name=site['name'], defaults={'creator': request.user}
            )[0]
            for site in json_content['sites']
        }

        Experiment.objects.filter(session=session).delete()  # cascades to scans -> images

        experiments = {
            e['id']: Experiment(name=e['id'], note=e['note'], session=session)
            for e in json_content['experiments']
        }
        Experiment.objects.bulk_create(experiments.values())

        scans = []
        images = []
        for scan_json in json_content['scans']:
            experiment = experiments[scan_json['experiment_id']]
            site = sites[scan_json['site_id']]
            scan = Scan(
                scan_id=scan_json['id'],
                scan_type=scan_json['type'],
                decision=ScanDecision.from_rating(scan_json['decision']),
                note=scan_json['note'],
                experiment=experiment,
                site=site,
            )
            scans.append(scan)

            if 'images' in scan_json:
                # TODO implement this
                raise Exception('use image_pattern for now')
            elif 'image_pattern' in scan_json:
                image_pattern = re.compile(scan_json['image_pattern'])
                image_dir = data_root / scan_json['path']
                for image_file in os.listdir(image_dir):
                    if image_pattern.fullmatch(image_file):
                        images.append(
                            Image(
                                name=image_file,
                                raw_path=image_dir / image_file,
                                scan=scan,
                            )
                        )

        Scan.objects.bulk_create(scans)
        Image.objects.bulk_create(images)

        return Response(status=status.HTTP_204_NO_CONTENT)
