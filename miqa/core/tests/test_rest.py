import pytest

from .fuzzy import PATH_RE


@pytest.mark.django_db
def test_sessions_list(authenticated_api_client, session):
    resp = authenticated_api_client.get('/api/v1/sessions')
    assert resp.status_code == 200
    assert resp.data == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [{'id': session.id, 'name': session.name, 'lock_owner': None}],
    }


@pytest.mark.django_db
def test_session_settings_get(staff_api_client, session):
    resp = staff_api_client.get(f'/api/v1/sessions/{session.id}/settings')
    assert resp.status_code == 200
    assert resp.data == {
        'importpath': PATH_RE,
        'exportpath': PATH_RE,
    }


@pytest.mark.django_db
def test_session_settings_put(staff_api_client, session):
    staff_api_client.put(
        f'/api/v1/sessions/{session.id}/settings',
        data={'importpath': '/new/fake/path', 'exportpath': '/new/fake/path'},
    )
    assert staff_api_client.get(f'/api/v1/sessions/{session.id}/settings').data == {
        'importpath': '/new/fake/path',
        'exportpath': '/new/fake/path',
    }


@pytest.mark.django_db
def test_experiments_list(authenticated_api_client, experiment):
    resp = authenticated_api_client.get('/api/v1/experiments')
    assert resp.status_code == 200
    assert resp.data['count'] == 1


@pytest.mark.django_db
def test_experiment_retrieve(authenticated_api_client, experiment):
    resp = authenticated_api_client.get(f'/api/v1/experiments/{experiment.id}')
    assert resp.status_code == 200
    # We want to assert that the nested session document isn't the giant one
    assert 'experiments' not in resp.data['session'].keys()


@pytest.mark.django_db
def test_scans_list(authenticated_api_client, scan):
    resp = authenticated_api_client.get('/api/v1/scans')
    assert resp.status_code == 200
    assert resp.data['count'] == 1


@pytest.mark.django_db
def test_scan_notes_list(authenticated_api_client, scan_note):
    resp = authenticated_api_client.get('/api/v1/scan_notes')
    assert resp.status_code == 200
    assert resp.data['count'] == 1


@pytest.mark.django_db
def test_images_list(authenticated_api_client, image):
    resp = authenticated_api_client.get('/api/v1/images')
    assert resp.status_code == 200
    assert resp.data['count'] == 1


@pytest.mark.django_db
def test_session_lock_acquire_requires_auth(api_client, session):
    resp = api_client.post(f'/api/v1/sessions/{session.id}/lock')
    assert resp.status_code == 401


@pytest.mark.django_db
def test_session_lock_acquire(authenticated_api_client, session):
    resp = authenticated_api_client.post(f'/api/v1/sessions/{session.id}/lock')
    assert resp.status_code == 204


@pytest.mark.django_db
def test_session_lock_reacquire_ok(api_client, session_factory, user):
    session = session_factory(lock_owner=user)
    api_client.force_authenticate(user=user)
    resp = api_client.post(f'/api/v1/sessions/{session.id}/lock')
    assert resp.status_code == 204


@pytest.mark.django_db
def test_session_lock_denied(authenticated_api_client, session_factory, user_factory):
    owner = user_factory()
    session = session_factory(lock_owner=owner)
    resp = authenticated_api_client.post(f'/api/v1/sessions/{session.id}/lock')
    assert resp.status_code == 409

    session.refresh_from_db()
    assert session.lock_owner == owner


@pytest.mark.django_db
def test_session_lock_release(api_client, session_factory, user):
    session = session_factory(lock_owner=user)
    api_client.force_authenticate(user=user)
    resp = api_client.delete(f'/api/v1/sessions/{session.id}/lock')
    assert resp.status_code == 204

    session.refresh_from_db()
    assert session.lock_owner is None


@pytest.mark.django_db
def test_session_lock_only_owner_can_release(
    authenticated_api_client, session_factory, user_factory
):
    owner = user_factory()
    session = session_factory(lock_owner=owner)
    resp = authenticated_api_client.delete(f'/api/v1/sessions/{session.id}/lock')
    assert resp.status_code == 409

    session.refresh_from_db()
    assert session.lock_owner.id == owner.id
