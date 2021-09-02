import csv
import io
import json
from pathlib import Path
import re

from jsonschema.exceptions import ValidationError
import pytest

from miqa.core.tasks import import_data


def generate_import_csv(sample_scans):
    output = io.StringIO()
    fieldnames = [
        'xnat_experiment_id',
        'nifti_folder',
        'scan_id',
        'scan_type',
        'experiment_note',
        'decision',
        'scan_note',
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, dialect='unix')
    writer.writeheader()
    for scan_folder, scan_id, scan_type in sample_scans:
        writer.writerow(
            {
                'xnat_experiment_id': 'NCANDA_DUMMY',
                'nifti_folder': scan_folder,
                'scan_id': scan_id,
                'scan_type': scan_type,
                'experiment_note': '',
                'decision': '',
                'scan_note': '',
            }
        )

    return output, writer


def generate_import_json(samples_dir: Path, sample_scans):
    scans = []
    for scan_folder, scan_id, scan_type in sample_scans:
        scans.append(
            {
                'id': scan_id,
                'type': scan_type,
                'note': '',
                'experiment_id': 'NCANDA_DUMMY',
                'path': scan_folder,
                'image_pattern': r'^image[\d]*\.nii\.gz$',
                'site_id': 'test_site',
                'decision': '',
            }
        )
    experiments = [
        {
            'id': 'NCANDA_DUMMY',
            'note': '',
        }
    ]
    return {
        'data_root': str(samples_dir),
        'scans': scans,
        'experiments': experiments,
        'sites': [{'name': 'test_site'}],
    }


@pytest.mark.django_db
def test_import_csv(tmp_path, user, session_factory, sample_scans, authenticated_api_client):
    csv_file = str(tmp_path / 'import.csv')
    with open(csv_file, 'w') as fd:
        output, _writer = generate_import_csv(sample_scans)
        fd.write(output.getvalue())

    session = session_factory(import_path=csv_file)

    import_data(user, session)
    # Test that the API import succeeds
    resp = authenticated_api_client.post(f'/api/v1/sessions/{session.id}/import')
    assert resp.status_code == 204


@pytest.mark.django_db
def test_import_json(
    tmp_path: Path,
    user,
    session_factory,
    samples_dir: Path,
    sample_scans,
    authenticated_api_client,
):
    json_file = str(tmp_path / 'import.json')
    with open(json_file, 'w') as fd:
        fd.write(json.dumps(generate_import_json(samples_dir, sample_scans)))

    session = session_factory(import_path=json_file)

    import_data(user, session)

    # Test that the API import succeeds
    resp = authenticated_api_client.post(f'/api/v1/sessions/{session.id}/import')
    assert resp.status_code == 204


@pytest.mark.django_db
def test_import_invalid_extension(user, session_factory, authenticated_api_client):
    invalid_file = '/foo/bar.txt'
    session = session_factory(import_path=invalid_file)
    with pytest.raises(ValidationError, match=f'Invalid import file {invalid_file}'):
        import_data(user, session)


@pytest.mark.django_db
def test_import_invalid_csv(
    tmp_path: Path,
    user,
    session_factory,
    sample_scans,
    authenticated_api_client,
):
    csv_file = str(tmp_path / 'import.csv')
    output, writer = generate_import_csv(sample_scans)

    # deliberately invalidate the data
    writer.writerow(
        {
            'xnat_experiment_id': 'NCANDA_DUMMY',
            # This value with no common prefix with the other scans will cause a ValueError
            'nifti_folder': 'NOT_A_REAL_FOLDER',
            'scan_id': '123',
            'scan_type': 'foobar',
            'experiment_note': '',
            'decision': '',
            'scan_note': '',
        }
    )

    with open(csv_file, 'w') as fd:
        fd.write(output.getvalue())

    session = session_factory(import_path=csv_file)

    with pytest.raises(ValueError, match='empty separator'):
        import_data(user, session)


@pytest.mark.django_db
def test_import_invalid_json(
    tmp_path: Path,
    user,
    session_factory,
    samples_dir: Path,
    sample_scans,
    authenticated_api_client,
):
    json_file = str(tmp_path / 'import.json')
    json_content = generate_import_json(samples_dir, sample_scans)

    # deliberately invalidate the data
    json_content['scans'][0]['site_id'] = 666

    with open(json_file, 'w') as fd:
        fd.write(json.dumps(json_content))

    session = session_factory(import_path=json_file)

    with pytest.raises(
        ValidationError,
        match=re.escape(
            "666 is not of type 'string'\n\nFailed validating 'type' in schema['properties']['scans']['items']['properties']['site_id']:\n    {'type': 'string'}\n\nOn instance['scans'][0]['site_id']:\n    666"  # noqa: E501
        ),
    ):
        import_data(user, session)
