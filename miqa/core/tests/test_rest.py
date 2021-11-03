import pytest

from .fuzzy import PATH_RE


@pytest.mark.django_db
def test_projects_list(authenticated_api_client, project):
    resp = authenticated_api_client.get('/api/v1/projects')
    assert resp.status_code == 200
    assert resp.data == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [{'id': project.id, 'name': project.name}],
    }


@pytest.mark.django_db
def test_project_settings_get(staff_api_client, project):
    resp = staff_api_client.get(f'/api/v1/projects/{project.id}/settings')
    assert resp.status_code == 200
    assert resp.data == {
        'importPath': PATH_RE,
        'exportPath': PATH_RE,
    }


@pytest.mark.django_db
def test_project_settings_put(staff_api_client, project):
    staff_api_client.put(
        f'/api/v1/projects/{project.id}/settings',
        data={'importPath': '/new/fake/path', 'exportPath': '/new/fake/path'},
    )
    assert staff_api_client.get(f'/api/v1/projects/{project.id}/settings').data == {
        'importPath': '/new/fake/path',
        'exportPath': '/new/fake/path',
    }


@pytest.mark.django_db
def test_settings_endpoint_requires_staff(authenticated_api_client, project):
    resp = authenticated_api_client.put(
        f'/api/v1/projects/{project.id}/settings',
        data={'importPath': '/new/fake/path', 'exportPath': '/new/fake/path'},
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_experiments_list(authenticated_api_client, experiment):
    resp = authenticated_api_client.get('/api/v1/experiments')
    assert resp.status_code == 200
    assert resp.data['count'] == 1


@pytest.mark.django_db
def test_experiment_retrieve(authenticated_api_client, experiment):
    resp = authenticated_api_client.get(f'/api/v1/experiments/{experiment.id}')
    assert resp.status_code == 200
    # We want to assert that the nested project document is only the id
    assert resp.json() == {
        'id': experiment.id,
        'lock_owner': None,
        'name': experiment.name,
        'note': experiment.note,
        'project': experiment.project.id,
        'scans': [],
    }


@pytest.mark.django_db
def test_scans_list(authenticated_api_client, scan):
    resp = authenticated_api_client.get('/api/v1/scans')
    assert resp.status_code == 200
    assert resp.data['count'] == 1


@pytest.mark.django_db
def test_scan_decisions_list(authenticated_api_client, scan_decision):
    resp = authenticated_api_client.get('/api/v1/scan-decisions')
    assert resp.status_code == 200
    assert resp.data['count'] == 1


@pytest.mark.django_db
def test_frames_list(authenticated_api_client, frame):
    resp = authenticated_api_client.get('/api/v1/frames')
    assert resp.status_code == 200
    assert resp.data['count'] == 1


@pytest.mark.django_db
def test_experiment_lock_acquire_requires_auth(api_client, experiment):
    resp = api_client.post(f'/api/v1/experiments/{experiment.id}/lock')
    assert resp.status_code == 401


@pytest.mark.django_db
def test_experiment_lock_acquire(api_client, experiment, user):
    api_client.force_authenticate(user=user)
    resp = api_client.post(f'/api/v1/experiments/{experiment.id}/lock')
    assert resp.status_code == 200
    experiment.refresh_from_db()
    assert experiment.lock_owner == user


@pytest.mark.django_db
def test_experiment_lock_reacquire_ok(api_client, experiment_factory, user):
    experiment = experiment_factory(lock_owner=user)
    api_client.force_authenticate(user=user)
    resp = api_client.post(f'/api/v1/experiments/{experiment.id}/lock')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_experiment_lock_denied(authenticated_api_client, experiment_factory, user_factory):
    owner = user_factory()
    experiment = experiment_factory(lock_owner=owner)
    resp = authenticated_api_client.post(f'/api/v1/experiments/{experiment.id}/lock')
    assert resp.status_code == 409

    experiment.refresh_from_db()
    assert experiment.lock_owner == owner


@pytest.mark.django_db
def test_experiment_lock_release(api_client, experiment_factory, user):
    experiment = experiment_factory(lock_owner=user)
    api_client.force_authenticate(user=user)
    resp = api_client.delete(f'/api/v1/experiments/{experiment.id}/lock')
    assert resp.status_code == 200

    experiment.refresh_from_db()
    assert experiment.lock_owner is None


@pytest.mark.django_db
def test_experiment_lock_only_owner_can_release(
    authenticated_api_client, experiment_factory, user_factory
):
    owner = user_factory()
    experiment = experiment_factory(lock_owner=owner)
    resp = authenticated_api_client.delete(f'/api/v1/experiments/{experiment.id}/lock')
    assert resp.status_code == 409

    experiment.refresh_from_db()
    assert experiment.lock_owner.id == owner.id


@pytest.mark.django_db
def test_read_without_lock_ok(authenticated_api_client, scan_decision):
    resp = authenticated_api_client.get(f'/api/v1/scan-decisions/{scan_decision.id}')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_create_note_without_lock_fails(authenticated_api_client, scan):
    resp = authenticated_api_client.post(
        '/api/v1/scan-decisions',
        data={
            'scan': scan.id,
            'decision': 'Good',
            'note': 'hello',
        },
    )
    assert resp.status_code == 403
    assert resp.data['detail'] == 'You must lock the experiment before performing this action.'


@pytest.mark.django_db
def test_create_scan_decision_without_lock_fails(authenticated_api_client, scan):
    resp = authenticated_api_client.post(
        '/api/v1/scan-decisions',
        data={
            'scan': scan.id,
            'decision': 'Good',
        },
    )
    assert resp.status_code == 403
    assert resp.data['detail'] == 'You must lock the experiment before performing this action.'


@pytest.mark.django_db
def test_create_scan_decision_with_lock(api_client, scan, user):
    scan.experiment.lock_owner = user
    scan.experiment.save(update_fields=['lock_owner'])
    api_client.force_authenticate(user=user)

    resp = api_client.post(
        '/api/v1/scan-decisions',
        data={
            'scan': scan.id,
            'decision': 'Good',
            'note': '',
        },
    )
    assert resp.status_code == 201
    decisions = scan.decisions.all()
    assert len(decisions) == 1
    assert decisions[0].decision == 'Good'
