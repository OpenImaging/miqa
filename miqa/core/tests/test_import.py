import csv
import io
import json
from pathlib import Path
import re

from guardian.shortcuts import get_perms
import pytest
from rest_framework.exceptions import APIException

from miqa.core.models import Frame, GlobalSettings
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
        # The project name is encoded somewhere in the path
        for potential_name in ['ohsu', 'ucsd']:
            if potential_name in scan_folder:
                project_name = potential_name
        writer.writerow(
            {
                'project_name': project_name,
                'experiment_name': f'{scan_id}_experiment',
                'scan_name': scan_id,
                'scan_type': scan_type,
                'frame_number': 0,
                'file_location': f'{scan_folder}/{scan_id}_{scan_type}/image.nii.gz',
            }
        )

    return output, writer


def generate_import_json(samples_dir: Path, sample_scans):
    projects = {}
    for scan_folder, scan_id, scan_type in sample_scans:
        # The project name is encoded somewhere in the path
        for potential_name in ['ohsu', 'ucsd']:
            if potential_name in scan_folder:
                project_name = potential_name
        experiment_name = f'{scan_id}_experiment'
        projects[project_name] = {
            'experiments': {
                experiment_name: {
                    'scans': {
                        scan_id: {
                            'type': scan_type,
                            'frames': {
                                0: {
                                    'file_location': str(
                                        Path(
                                            scan_folder,
                                            f'{scan_id}_{scan_type}',
                                            'image.nii.gz',
                                        )
                                    )
                                }
                            },
                        }
                    }
                }
            }
        }
    return {'projects': projects}


@pytest.mark.django_db
def test_import_csv(tmp_path, user, project_factory, sample_scans, user_api_client):
    csv_file = str(tmp_path / 'import.csv')
    with open(csv_file, 'w') as fd:
        output, _writer = generate_import_csv(sample_scans)
        fd.write(output.getvalue())

    # The default project will have a name which does not match the import CSV column
    project = project_factory(import_path=csv_file)
    user_api_client = user_api_client(project=project)

    resp = user_api_client.post(f'/api/v1/projects/{project.id}/import')
    if get_perms(user, project):
        assert resp.status_code == 204
        # The import should update the project, even though the names do not match
        project.refresh_from_db()
        assert project.experiments.count() == 2
        assert project.experiments.all()[0].scans.count() == 1
        assert project.experiments.all()[1].scans.count() == 1
    else:
        assert resp.status_code == 401


@pytest.mark.django_db(transaction=True)
def test_import_global_csv(tmp_path, user, project_factory, sample_scans, user_api_client):
    # Generate an import CSV for two projects with the same data
    csv_file = str(tmp_path / 'import.csv')
    with open(csv_file, 'w') as fd:
        output, _writer = generate_import_csv(sample_scans)
        fd.write(output.getvalue())

    global_settings = GlobalSettings.load()
    global_settings.import_path = csv_file
    global_settings.save()

    # Create projects targeted by the import
    project_ohsu = project_factory(import_path=csv_file, name='ohsu')
    project_ucsd = project_factory(import_path=csv_file, name='ucsd')

    resp = user_api_client().post('/api/v1/global/import')
    if user.is_superuser:
        assert resp.status_code == 204
        # The import should update the correctly named projects, but not the original import project
        project_ohsu.refresh_from_db()
        project_ucsd.refresh_from_db()
        assert project_ohsu.experiments.count() == 1
        assert project_ohsu.experiments.get().scans.count() == 1
        assert project_ucsd.experiments.count() == 1
        assert project_ucsd.experiments.get().scans.count() == 1
    else:
        assert resp.status_code == 403


@pytest.mark.django_db
def test_import_json(
    tmp_path: Path,
    user,
    project_factory,
    samples_dir: Path,
    sample_scans,
    user_api_client,
):
    json_file = str(tmp_path / 'import.json')
    with open(json_file, 'w') as fd:
        fd.write(json.dumps(generate_import_json(samples_dir, sample_scans)))

    # The default project will have a name which does not match the project in the JSON
    project = project_factory(import_path=json_file)

    resp = user_api_client(project=project).post(f'/api/v1/projects/{project.id}/import')
    if get_perms(user, project):
        assert resp.status_code == 204
        # The import should update the project, even though the names do not match
        project.refresh_from_db()
        assert project.experiments.count() == 2
        assert project.experiments.all()[0].scans.count() == 1
        assert project.experiments.all()[1].scans.count() == 1
    else:
        assert resp.status_code == 401


@pytest.mark.django_db
def test_import_global_json(
    tmp_path: Path,
    user,
    project_factory,
    samples_dir: Path,
    sample_scans,
    user_api_client,
):
    json_file = str(tmp_path / 'import.json')
    with open(json_file, 'w') as fd:
        fd.write(json.dumps(generate_import_json(samples_dir, sample_scans)))

    global_settings = GlobalSettings.load()
    global_settings.import_path = json_file
    global_settings.save()

    # Create projects targeted by the import
    project_ohsu = project_factory(import_path=json_file, name='ohsu')
    project_ucsd = project_factory(import_path=json_file, name='ucsd')

    resp = user_api_client().post('/api/v1/global/import')
    if user.is_superuser:
        assert resp.status_code == 204
        # The import should update the correctly named projects, but not the original import project
        project_ohsu.refresh_from_db()
        project_ucsd.refresh_from_db()
        assert project_ohsu.experiments.count() == 1
        assert project_ohsu.experiments.get().scans.count() == 1
        assert project_ucsd.experiments.count() == 1
        assert project_ucsd.experiments.get().scans.count() == 1
    else:
        assert resp.status_code == 403


@pytest.mark.django_db
def test_import_invalid_extension(user, project_factory):
    invalid_file = '/foo/bar.txt'
    project = project_factory(import_path=invalid_file)
    with pytest.raises(APIException, match=f'Invalid import file {invalid_file}'):
        import_data(project.id)


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

    with pytest.raises(APIException, match='Could not locate file'):
        import_data(project.id)


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
    json_content['fake_key'] = 'foo'

    with open(json_file, 'w') as fd:
        fd.write(json.dumps(json_content))

    project = project_factory(import_path=json_file)

    with pytest.raises(
        APIException,
        match=re.escape('Invalid format of import file'),
    ):
        import_data(project.id)


@pytest.mark.django_db
def test_import_s3_preserves_path(project_factory):
    s3_import_csv = Path(__file__).parent / 'data' / 's3_import.csv'
    project = project_factory(import_path=s3_import_csv)
    import_data(project.id)

    frame = Frame.objects.first()
    assert (
        frame.raw_path
        == 's3:/miqa-sample/IXI_small/Guys/IXI002/0828-DTI/IXI002-Guys-0828-DTI-00.nii.gz'
    )
