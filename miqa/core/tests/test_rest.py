from uuid import UUID

import pytest

from .fuzzy import ANY_RE


def experiment_to_dict(session):
    def a(experiment):
        return {
            'id': experiment.id,
            'name': experiment.name,
            'note': experiment.note,
            'session': {'id': session.id, 'name': session.name},
        }

    return a


def scan_to_dict(experiment, site):
    def a(scan):
        return {
            'id': scan.id,
            'scan_id': scan.scan_id,
            'scan_type': scan.scan_type,
            'decision': scan.decision,
            'notes': [],
            'site': UUID(site.id),
            'experiment': UUID(experiment.id),
        }

    return a


def image_to_dict(scan):
    def a(image):
        return {'id': image.id, 'name': image.name, 'scan': UUID(scan.id)}

    return a


def note_to_dict(user):
    def a(note):
        return {
            'id': note.id,
            'creator': {'first_name': user.first_name, 'last_name': user.last_name},
            'note': note.note,
            'created': ANY_RE,
            'modified': ANY_RE,
        }

    return a


def compare_lst(lst1, lst2, to_dict):
    lst1 = list(map(lambda x: to_dict(x), lst1))

    diff = [i for i in lst1 + lst2 if i not in lst1 or i not in lst2]

    return len(diff)


@pytest.mark.django_db()
def test_session(api_client, session_factory):

    session = session_factory()

    assert api_client.get('/api/v1/sessions').data == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [{'id': session.id, 'name': session.name}],
    }


@pytest.mark.django_db()
def test_session_settings_get(api_client, session_factory):

    session = session_factory()

    assert api_client.get(f'/api/v1/sessions/{session.id}/settings').data == {
        'importpath': '/fake/path',
        'exportpath': '/fake/path',
    }


@pytest.mark.django_db()
def test_session_settings_put(api_client, session_factory):

    session = session_factory()

    api_client.put(
        f'/api/v1/sessions/{session.id}/settings',
        data={'importpath': '/new/fake/path', 'exportpath': '/new/fake/path'},
    )

    assert api_client.get(f'/api/v1/sessions/{session.id}/settings').data == {
        'importpath': '/new/fake/path',
        'exportpath': '/new/fake/path',
    }


@pytest.mark.django_db()
def test_experiments(api_client, session_factory, experiment_factory):

    session = session_factory()

    experiments = []
    for _ in range(10):
        experiments.append(experiment_factory(session=session))

    data = api_client.get('/api/v1/experiments').data

    assert data['count'] == 10

    # test if results contain same dicts
    assert compare_lst(experiments, data['results'], experiment_to_dict(session)) == 0

    e = experiments[0]

    assert api_client.get(f'/api/v1/experiments/{e.id}').data == experiment_to_dict(session)(e)


@pytest.mark.django_db()
def test_scans(api_client, session_factory, experiment_factory, scan_factory, site_factory):

    session = session_factory()

    site = site_factory()

    experiment = experiment_factory(session=session)

    scans = []
    for _ in range(10):
        scans.append(scan_factory(experiment=experiment, site=site))

    data = api_client.get('/api/v1/scans').data

    assert data['count'] == 10

    # test if results contain same dicts
    assert compare_lst(scans, data['results'], scan_to_dict(experiment, site)) == 0

    s = scans[0]

    assert api_client.get(f'/api/v1/scans/{s.id}').data == scan_to_dict(experiment, site)(s)


@pytest.mark.django_db()
def test_scan_notes(
    api_client,
    user_factory,
    session_factory,
    experiment_factory,
    scan_factory,
    note_factory,
    site_factory,
):

    user = user_factory()

    session = session_factory(creator=user)

    site = site_factory(creator=user)

    experiment = experiment_factory(session=session)

    scan = scan_factory(experiment=experiment, site=site)

    notes = []
    for _ in range(10):
        notes.append(note_factory(scan=scan, creator=user))

    data = api_client.get('/api/v1/scan_notes').data

    assert data['count'] == 10

    assert compare_lst(notes, data['results'], note_to_dict(user)) == 0


@pytest.mark.django_db()
def test_images(
    api_client, session_factory, experiment_factory, scan_factory, image_factory, site_factory
):

    session = session_factory()

    site = site_factory()

    experiment = experiment_factory(session=session)

    scan = scan_factory(experiment=experiment, site=site)

    images = []
    for _ in range(10):
        images.append(image_factory(scan=scan))

    data = api_client.get('/api/v1/images').data

    assert data['count'] == 10

    assert compare_lst(images, data['results'], image_to_dict(scan)) == 0
