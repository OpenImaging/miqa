import json
import os
from pathlib import Path
import re

from jsonschema import validate
from jsonschema.exceptions import ValidationError

from miqa.core.conversion.csv_to_json import csvContentToJsonObject, find_common_prefix
from miqa.core.conversion.json_to_csv import jsonObjectToCsvContent
from miqa.core.models import Annotation, Decision, Experiment, Image, Scan, ScanNote, Session, Site
from miqa.core.schema.data_import import schema


def import_data(user, session: Session):
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
    annotations = []
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

        if scan_json['decision']:
            annotation = Annotation(
                scan=scan,
                decision=Decision.from_rating(scan_json['decision']),
            )
            annotations.append(annotation)

        if scan_json['note']:
            for note in scan_json['note'].split('\n'):
                initials, note = note.split(':')
                scan_note = ScanNote(
                    initials=initials,
                    note=note,
                    scan=scan,
                )
                notes.append(scan_note)

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
    Annotation.objects.bulk_create(annotations)


def export_data(user, session: Session):
    data_root = None
    experiments = []
    scans = []
    sites = set()

    for experiment in session.experiments.all():
        experiments.append(
            {
                'id': experiment.name,
                'note': experiment.note,
            }
        )
        for scan in experiment.scans.all():
            scan_root = None
            for image in scan.images.all():
                if data_root is None:
                    data_root = image.raw_path
                data_root = find_common_prefix(data_root, image.raw_path)

                if scan_root is None:
                    scan_root = image.raw_path
                scan_root = find_common_prefix(scan_root, image.raw_path)

            if scan_root is None:
                # There were no images in this scan, don't export it
                continue

            decision = scan.decisions.order_by('-created').first()
            if decision:
                decision = Decision.to_rating(decision.decision)
            else:
                decision = ''

            note = '\n'.join(
                [f'{note.initials}:{note.note}' for note in scan.notes.order_by('created').all()]
            )

            scans.append(
                {
                    'id': scan.scan_id,
                    'type': scan.scan_type,
                    'note': note,
                    'experiment_id': experiment.name,
                    'path': scan_root,
                    'image_pattern': r'^image[\d]*\.nii\.gz$',
                    'site_id': scan.site.name,
                    'decision': decision,
                }
            )
            sites.add(scan.site.name)

    # scan.path should omit the data_root prefix, so trim it off now
    for scan in scans:
        scan['path'] = scan['path'][len(data_root) :]

    json_content = {
        'data_root': data_root,
        'experiments': experiments,
        'scans': scans,
        'sites': [{'name': site} for site in sites],
    }

    if session.export_path.endswith('.csv'):
        with open(session.export_path, 'w') as csv_file:
            csv_content = jsonObjectToCsvContent(json_content)
            csv_file.write(csv_content.getvalue())
    elif session.export_path.endswith('.json'):
        with open(session.export_path, 'w') as json_file:
            json_file.write(json.dump(json_content))
