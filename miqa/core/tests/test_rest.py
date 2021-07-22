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
        'results': [{'id': session.id, 'name': session.name}],
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
