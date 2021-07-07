import json
import os
from pathlib import Path
import re

from jsonschema import validate
from jsonschema.exceptions import ValidationError

from miqa.core.conversion.csv_to_json import csvContentToJsonObject
from miqa.core.models import Experiment, Image, Scan, ScanNote, Site
from miqa.core.schema.data_import import schema


def import_data(user, session):
    if session.import_path.endswith('.csv'):
        with open(session.import_path) as fd:
            csv_content = fd.read()
            try:
                json_content = csvContentToJsonObject(csv_content)
                validate(json_content, schema)  # TODO this should be an internal error
            except (ValidationError, Exception) as e:
                raise ValidationError({'error': f'Invalid CSV file: {str(e)}'})
    elif session.import_path.endswith('.json'):
        with open(session.import_path) as json_file:
            try:
                json_content = json.load(json_file)
                validate(json_content, schema)
            except (ValidationError, Exception) as e:  # TODO this should be an internal error
                raise ValidationError({'error': f'Invalid JSON file: {str(e)}'})
    # else:
    # TODO: Raise an error

    data_root = Path(json_content['data_root'])

    sites = {
        site['name']: Site.objects.get_or_create(name=site['name'], defaults={'creator': user})[0]
        for site in json_content['sites']
    }

    Experiment.objects.filter(session=session).delete()  # cascades to scans -> images, scan_notes

    experiments = {
        e['id']: Experiment(name=e['id'], note=e['note'], session=session)
        for e in json_content['experiments']
    }
    Experiment.objects.bulk_create(experiments.values())

    scans = []
    images = []
    notes = []
    for scan_json in json_content['scans']:
        experiment = experiments[scan_json['experiment_id']]
        site = sites[scan_json['site_id']]
        scan = Scan(
            scan_id=scan_json['id'],
            scan_type=scan_json['type'],
            experiment=experiment,
            site=site,
        )
        scans.append(scan)

        # TODO import notes
        # if scan_json['note']:
        #     notes_json = json.loads(unquote(scan_json['note']))
        #     for note_json in notes_json:
        #         scan_note = ScanNote(
        #             **note_json,
        #             scan=scan,
        #         )
        #         # This forces the modified field to use the value we give it
        #         scan_note.update_modified = False
        #         notes.append(scan_note)

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
    ScanNote.objects.bulk_create(notes)


def export_data(user, session):
    pass
