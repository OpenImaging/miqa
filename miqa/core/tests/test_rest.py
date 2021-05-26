from miqa.core.models import experiment
import pytest


from .fuzzy import UUID_RE, ANY_RE

@pytest.mark.django_db()
def test_session_get(api_client, session_factory):

    session = session_factory()

    assert api_client.get('/api/v1/sessions').data == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [
            {
                'id':   session.id,
                'name': session.name
            }
        ]
    }
    
@pytest.mark.django_db()
def test_session_settings_get(api_client, session_factory):

    session = session_factory()

    assert api_client.get(f'/api/v1/sessions/{session.id}/settings').data == {
        'importpath': '/fake/path',
        'exportpath': '/fake/path'
    }

@pytest.mark.django_db()
def test_session_settings_put(api_client, session_factory):

    session = session_factory()

    api_client.put(f'/api/v1/sessions/{session.id}/settings', data = {
        'importpath': '/new/fake/path',
        'exportpath': '/new/fake/path'
    })

    assert api_client.get(f'/api/v1/sessions/{session.id}/settings').data == {
        'importpath': '/new/fake/path',
        'exportpath': '/new/fake/path'
    }

@pytest.mark.django_db()
def test_experiments_get(api_client, session_factory, experiment_factory):

    session = session_factory()

    experiments = []
    for _ in range(10):
        experiments.append(experiment_factory(session=session))
    
    data = api_client.get('/api/v1/experiments').data 

    print(data)
    
    assert data == {
        'count': 10,
        'next': None,
        'previous': None,
        'results': experiments
    }

    e = experiments[0]

    assert api_client.get(f'/api/v1/experiments/{e.id}').data == e

@pytest.mark.django_db()
def test_scans_get(api_client, session_factory, experiment_factory, scan_factory):

    session = session_factory()

    experiment = experiment_factory(session=session)

    scans = []
    for _ in range(10):
        scans.append(scan_factory(experiment=experiment))
    
    assert api_client.get('/api/v1/scans').data == {
        'count': 10,
        'next': None,
        'previous': None,
        'results': scans
    }

    s = scans[0]

    assert api_client.get(f'/api/v1/scans/{s.id}').data == s


# @pytest.mark.django_db()
# def test_images_get(api_client, session_factory, experiment_factory, scan_factory, image_factory):


