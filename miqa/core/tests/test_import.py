import json
from pathlib import Path
import re

from guardian.shortcuts import get_perms
import pytest
from rest_framework.exceptions import APIException

from miqa.core.conversion.import_export_csvs import IMPORT_CSV_COLUMNS
from miqa.core.models import Frame, GlobalSettings
from miqa.core.tasks import import_data
from miqa.core.tests.helpers import generate_import_csv, generate_import_json


@pytest.mark.django_db
def test_import_empty_csv(tmp_path, user, project_factory, user_api_client):
    csv_file = str(tmp_path / 'import.csv')
    with open(csv_file, 'w') as fd:
        fd.write(','.join(IMPORT_CSV_COLUMNS))

    project = project_factory(name='ucsd', import_path=csv_file)
    user_api_client = user_api_client(project=project)

    resp = user_api_client.post(f'/api/v1/projects/{project.id}/import')
    if get_perms(user, project):
        assert resp.status_code == 204
        project.refresh_from_db()
        assert project.experiments.count() == 0
    else:
        assert resp.status_code == 403


@pytest.mark.django_db
def test_import_csv(tmp_path, user, project_factory, sample_scans, user_api_client):
    csv_file = str(tmp_path / 'import.csv')
    with open(csv_file, 'w') as fd:
        output, _writer = generate_import_csv([scan for scan in sample_scans if 'ucsd' in scan[0]])
        fd.write(output.getvalue())

    project = project_factory(name='ucsd', import_path=csv_file)
    user_api_client = user_api_client(project=project)

    resp = user_api_client.post(f'/api/v1/projects/{project.id}/import')
    if get_perms(user, project):
        assert resp.status_code == 204
        project.refresh_from_db()
        assert project.experiments.count() == 1
        assert project.experiments.all()[0].scans.count() == 1
    else:
        assert resp.status_code == 403


@pytest.mark.django_db
def test_import_csv_optional_columns(user, project_factory, user_api_client):
    csv_file = Path('samples', 'scans_to_review_optional_columns.csv')

    project = project_factory(name='simple-scans', import_path=str(csv_file))
    user_api_client = user_api_client(project=project)

    resp = user_api_client.post(f'/api/v1/projects/{project.id}/import')
    if get_perms(user, project):
        assert resp.status_code == 204
        project.refresh_from_db()
        assert project.experiments.count() == 2
        assert project.experiments.all()[0].scans.count() == 1
        assert project.experiments.all()[1].scans.count() == 1
    else:
        assert resp.status_code == 403


@pytest.mark.django_db(transaction=True)
def test_import_global_csv(tmp_path, user, project_factory, sample_scans, user_api_client):
    csv_file = str(tmp_path / 'import.csv')
    with open(csv_file, 'w') as fd:
        output, _writer = generate_import_csv(sample_scans)
        fd.write(output.getvalue())

    global_settings = GlobalSettings.load()
    global_settings.import_path = csv_file
    global_settings.save()

    # Create projects targeted by the import
    project_ohsu = project_factory(name='ohsu')
    project_ucsd = project_factory(name='ucsd')

    resp = user_api_client().post('/api/v1/global/import')
    assert resp.status_code == 204
    project_ohsu.refresh_from_db()
    project_ucsd.refresh_from_db()
    assert project_ohsu.experiments.count() == 1
    assert project_ohsu.experiments.get().scans.count() == 1
    assert project_ucsd.experiments.count() == 1
    assert project_ucsd.experiments.get().scans.count() == 1


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
        fd.write(
            json.dumps(
                generate_import_json(
                    samples_dir,
                    [scan for scan in sample_scans if 'ucsd' in scan[0]],
                )
            )
        )

    project = project_factory(name='ucsd', import_path=json_file)

    resp = user_api_client(project=project).post(f'/api/v1/projects/{project.id}/import')
    if get_perms(user, project):
        assert resp.status_code == 204
        project.refresh_from_db()
        assert project.experiments.count() == 1
        assert project.experiments.all()[0].scans.count() == 1
    else:
        assert resp.status_code == 403


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
    assert resp.status_code == 204
    # The import should update the correctly named projects, but not the original import project
    project_ohsu.refresh_from_db()
    project_ucsd.refresh_from_db()
    assert project_ohsu.experiments.count() == 1
    assert project_ohsu.experiments.get().scans.count() == 1
    assert project_ucsd.experiments.count() == 1
    assert project_ucsd.experiments.get().scans.count() == 1


@pytest.mark.django_db
def test_import_invalid_extension(user, project_factory):
    invalid_file = '/foo/bar.txt'
    project = project_factory(import_path=invalid_file)
    with pytest.raises(APIException, match=f'Invalid import file {invalid_file}'):
        import_data(project.id)


@pytest.mark.django_db
def test_import_invalid_csv(tmp_path: Path, user, project_factory, sample_scans):
    csv_file = str(tmp_path / 'import.csv')
    output, writer = generate_import_csv([scan for scan in sample_scans if 'ucsd' in scan[0]])

    # deliberately invalidate the data
    writer.writerow(
        {
            'project_name': 'ucsd',
            'experiment_name': 'testExperiment',
            'scan_name': 'testScan',
            'scan_type': 'foobar',
            'frame_number': 0,
            'file_location': '/not/a/real/file.nii.gz',
        }
    )

    with open(csv_file, 'w') as fd:
        fd.write(output.getvalue())

    project = project_factory(name='ucsd', import_path=csv_file)

    error_list = import_data(project.id)
    assert error_list == ['File not found: /not/a/real/file.nii.gz']


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
def test_import_with_relative_path(project_factory):
    rel_import_csv = Path(__file__).parent / 'data' / 'relative_import.csv'
    project = project_factory(name='Guys', import_path=rel_import_csv)
    import_data(project.id)

    frame = Frame.objects.first()
    assert frame.raw_path == str(Path(__file__).parent / 'data' / 'example.nii.gz')


@pytest.mark.django_db
def test_import_s3_preserves_path(project_factory):
    s3_import_csv = Path(__file__).parent / 'data' / 's3_import.csv'
    project = project_factory(name='Guys', import_path=s3_import_csv)
    import_data(project.id)

    frame = Frame.objects.first()
    assert (
        frame.raw_path
        == 's3://miqa-sample/IXI_small/Guys/IXI002/0828-DTI/IXI002-Guys-0828-DTI-00.nii.gz'
    )


@pytest.mark.django_db
def test_import_export_unchanged(
    tmp_path: Path,
    user,
    project_factory,
    samples_dir: Path,
    sample_scans,
    user_api_client,
):
    with open(Path(__file__).parent / 'data' / 'test_import.json') as f:
        json_contents = json.load(f)
    import_file = str(tmp_path / 'import.json')
    export_file = str(tmp_path / 'export.json')
    with open(import_file, 'w') as f:
        json.dump(json_contents, f)

    project = project_factory(name='ucsd', import_path=import_file, export_path=export_file)

    resp = user_api_client(project=project).post(f'/api/v1/projects/{project.id}/import')
    if get_perms(user, project):
        project.refresh_from_db()
        assert project.experiments.count() == 1
        assert project.experiments.all()[0].scans.count() == 1

        user_api_client(project=project).post(f'/api/v1/projects/{project.id}/export')
        with open(export_file) as f:
            export_contents = json.load(f)
            assert export_contents == json_contents

    else:
        assert resp.status_code == 403
