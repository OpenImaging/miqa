import json
from pathlib import Path
from typing import Dict

from jsonschema import validate

from miqa.core.models import Experiment, Session

data_json_schema = {
    '$schema': 'http://json-schema.org/schema#',
    'title': 'MIQA data import schema',
    'type': 'object',
    'additionalProperties': False,
    'required': ['scans'],
    'properties': {
        'data_root': {'type': 'string'},
        'sites': {
            'type': 'array',
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'required': ['id'],
                'properties': {
                    'id': {'type': 'string'},
                },
            },
        },
        'experiments': {
            'type': 'array',
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'required': ['id'],
                'properties': {
                    'id': {'type': 'string'},
                    'note': {'type': 'string'},
                },
            },
        },
        'scans': {
            'type': 'array',
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'properties': {
                    'experiment_id': {'type': 'string'},
                    'site_id': {'type': 'string'},
                    'path': {'type': 'string'},
                    'id': {'type': 'string'},
                    'type': {'type': 'string'},
                    'decision': {'type': 'string'},
                    'note': {'type': 'string'},
                    'user_fields': {
                        'type': 'object',
                        'additional_properties': True,
                        'required': [],
                        r'\w.*': {'type': 'string'},
                    },
                    'images': {
                        'type': 'array',
                        'items': {'type': 'string'},
                    },
                    'imagePattern': {'type': 'string'},
                },
                'oneOf': [
                    {
                        'required': ['experiment_id', 'path', 'site_id', 'id', 'type', 'images'],
                    },
                    {
                        'required': [
                            'experiment_id',
                            'path',
                            'site_id',
                            'id',
                            'type',
                            'imagePattern',
                        ],
                    },
                ],
            },
        },
    },
}


def import_json(path: Path, session: Session) -> None:
    with open(path, 'rb') as fd:
        data = json.load(fd)
        validate(data, data_json_schema)

    # for site in data.get('sites', []):

    experiments: Dict[str, Experiment] = {}
    for experiment in data.get('experiments', []):
        name = experiment['id']
        note = experiment.get('note', '')
        record, _ = Experiment.objects.get_or_create(
            session=session, name=name, defaults={'note': note}
        )
        experiments[record.name] = record
