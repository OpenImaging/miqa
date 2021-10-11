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
        'project_name',
        'experiment_name',
        'scan_name',
        'scan_type',
        'frame_number',
        'file_location',
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, dialect='unix')
    writer.writeheader()
    for scan_folder, scan_id, scan_type in sample_scans:
        print(scan_folder, scan_id, scan_type)
        writer.writerow(
            {
                'project_name': 'testProject',
                'experiment_name': 'testExperiment',
                'scan_name': scan_id,
                'scan_type': scan_type,
                'frame_number': 0,
                'file_location': f'{scan_folder}/{scan_id}_{scan_type}/image.nii.gz',
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
def test_import_csv(tmp_path, user, project_factory, sample_scans, authenticated_api_client):
    csv_file = str(tmp_path / 'import.csv')
    with open(csv_file, 'w') as fd:
        output, _writer = generate_import_csv(sample_scans)
        fd.write(output.getvalue())

    project = project_factory(import_path=csv_file)

    import_data(user.id, project.id)
    # Test that the API import succeeds
    resp = authenticated_api_client.post(f'/api/v1/projects/{project.id}/import')
    assert resp.status_code == 204


@pytest.mark.django_db
def test_import_json(
    tmp_path: Path,
    user,
    project_factory,
    samples_dir: Path,
    sample_scans,
    authenticated_api_client,
):
    json_file = str(tmp_path / 'import.json')
    with open(json_file, 'w') as fd:
        fd.write(json.dumps(generate_import_json(samples_dir, sample_scans)))

    project = project_factory(import_path=json_file)

    with pytest.raises(
        ValidationError,
        match=re.escape("Invalid import file"),
    ):
        import_data(user.id, project.id)

    # Test that the API import succeeds
    # resp = authenticated_api_client.post(f'/api/v1/projects/{project.id}/import')
    # assert resp.status_code == 204


@pytest.mark.django_db
def test_import_invalid_extension(user, project_factory):
    invalid_file = '/foo/bar.txt'
    project = project_factory(import_path=invalid_file)
    with pytest.raises(ValidationError, match=f'Invalid import file {invalid_file}'):
        import_data(user.id, project.id)


@pytest.mark.django_db
def test_import_invalid_csv(tmp_path: Path, user, project_factory, sample_scans):
    csv_file = str(tmp_path / 'import.csv')
    output, writer = generate_import_csv(sample_scans)

    # deliberately invalidate the data
    writer.writerow(
        {
            'project_name': 'testProject',
            'experiment_name': 'testExperiment',
            'scan_name': 'testScan',
            'scan_type': 'foobar',
            'frame_number': 0,
            'file_location': '/not/a/real/file.nii.gz',
        }
    )

    with open(csv_file, 'w') as fd:
        fd.write(output.getvalue())

    project = project_factory(import_path=csv_file)

    with pytest.raises(ValidationError, match='Could not locate file'):
        import_data(user.id, project.id)


@pytest.mark.django_db
def test_import_invalid_json(
    tmp_path: Path,
    user,
    project_factory,
    samples_dir: Path,
    sample_scans,
):
    json_file = str(tmp_path / 'import.json')
    json_content = generate_import_json(samples_dir, sample_scans)

    # deliberately invalidate the data
    json_content['scans'][0]['site_id'] = 666

    with open(json_file, 'w') as fd:
        fd.write(json.dumps(json_content))

    project = project_factory(import_path=json_file)

    with pytest.raises(
        ValidationError,
        match=re.escape("Invalid import file"),
        # ValidationError,
        # match=re.escape(
        #     "666 is not of type 'string'\n\nFailed validating 'type' in schema['properties']['scans']['items']['properties']['site_id']:\n    {'type': 'string'}\n\nOn instance['scans'][0]['site_id']:\n    666"  # noqa: E501
        # ),
    ):
        import_data(user.id, project.id)
