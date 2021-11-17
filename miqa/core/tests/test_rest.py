from guardian.shortcuts import get_perms
import pytest

from miqa.core.rest.permissions import has_read_perm, has_review_perm


@pytest.mark.django_db
def test_projects_list(user_api_client, project, user):
    resp = user_api_client().get('/api/v1/projects')
    assert resp.status_code == 200
    if not has_read_perm(get_perms(user, project)):
        assert resp.data == {
            'count': 0,
            'next': None,
            'previous': None,
            'results': [],
        }
    else:
        assert resp.data == {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{'id': project.id, 'name': project.name}],
        }


@pytest.mark.django_db
def test_project_settings_get(user_api_client, project, user):
    resp = user_api_client().get(f'/api/v1/projects/{project.id}/settings')
    if not has_read_perm(get_perms(user, project)):
        assert resp.status_code == 401
    else:
        assert resp.status_code == 200
        assert all(key in resp.data for key in ['importPath', 'exportPath', 'permissions'])


@pytest.mark.django_db
def test_project_settings_put(user_api_client, project, user):
    user_api_client = user_api_client()
    resp = user_api_client.put(
        f'/api/v1/projects/{project.id}/settings',
        data={
            'importPath': '/new/fake/path',
            'exportPath': '/new/fake/path',
            'permissions': {
                'collaborator': [],
                'tier_1_reviewer': [user.username],
                'tier_2_reviewer': [],
            },
        },
    )
    if not user.is_superuser:
        assert resp.status_code == 401
    else:
        assert resp.status_code == 200
        assert user_api_client.get(f'/api/v1/projects/{project.id}/settings').data == {
            'importPath': '/new/fake/path',
            'exportPath': '/new/fake/path',
            'permissions': {
                'collaborator': [],
                'tier_1_reviewer': [user.username],
                'tier_2_reviewer': [],
            },
        }
        assert has_read_perm(get_perms(user, project))


@pytest.mark.django_db
def test_settings_endpoint_requires_superuser(user_api_client, project, user):
    resp = user_api_client().put(
        f'/api/v1/projects/{project.id}/settings',
        data={
            'importPath': '/new/fake/path',
            'exportPath': '/new/fake/path',
            'permissions': {},
        },
    )
    if not user.is_superuser:
        assert resp.status_code == 401
    else:
        assert resp.status_code == 200


@pytest.mark.django_db
def test_experiments_list(user_api_client, experiment, user):
    resp = user_api_client(project=experiment.project).get('/api/v1/experiments')
    assert resp.status_code == 200
    if not has_read_perm(get_perms(user, experiment.project)):
        assert resp.data == {
            'count': 0,
            'next': None,
            'previous': None,
            'results': [],
        }
    else:
        expected_result = [
            {
                'id': experiment.id,
                'name': experiment.name,
                'lock_owner': None,
                'scans': [],
                'project': experiment.project.id,
                'note': experiment.note,
            }
        ]
        print(resp.data['results'])
        print()
        print(expected_result)
        assert resp.data == {
            'count': 1,
            'next': None,
            'previous': None,
            'results': expected_result,
        }


@pytest.mark.django_db
def test_experiment_retrieve(user_api_client, experiment, user):
    resp = user_api_client(project=experiment.project).get(f'/api/v1/experiments/{experiment.id}')
    if not has_read_perm(get_perms(user, experiment.project)):
        assert resp.status_code == 404
    else:
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
def test_scans_list(user_api_client, scan, user):
    resp = user_api_client(project=scan.experiment.project).get('/api/v1/scans')
    assert resp.status_code == 200
    if not has_read_perm(get_perms(user, scan.experiment.project)):
        assert resp.data == {
            'count': 0,
            'next': None,
            'previous': None,
            'results': [],
        }
    else:
        expected_result = [
            {
                'id': str(scan.id),
                'name': scan.name,
                'decisions': [],
                'frames': [],
                'scan_type': scan.scan_type,
            }
        ]
        assert resp.data == {
            'count': 1,
            'next': None,
            'previous': None,
            'results': expected_result,
        }


@pytest.mark.django_db
def test_scan_decisions_list(user_api_client, scan_decision, user):
    resp = user_api_client(project=scan_decision.scan.experiment.project).get(
        '/api/v1/scan-decisions'
    )
    assert resp.status_code == 200
    if not has_read_perm(get_perms(user, scan_decision.scan.experiment.project)):
        assert resp.data == {
            'count': 0,
            'next': None,
            'previous': None,
            'results': [],
        }
    else:
        expected_result = [
            {
                'id': str(scan_decision.id),
                'decision': scan_decision.decision,
                'creator': {
                    'id': scan_decision.creator.id,
                    'username': scan_decision.creator.username,
                    'email': scan_decision.creator.email,
                    'is_superuser': scan_decision.creator.is_superuser,
                    'first_name': scan_decision.creator.first_name,
                    'last_name': scan_decision.creator.last_name,
                },
                'created': scan_decision.created.strftime('%d-%m-%Y'),
                'note': scan_decision.note,
            }
        ]
        assert resp.data == {
            'count': 1,
            'next': None,
            'previous': None,
            'results': expected_result,
        }


@pytest.mark.django_db
def test_frames_list(user_api_client, frame, user):
    resp = user_api_client(project=frame.scan.experiment.project).get('/api/v1/frames')
    assert resp.status_code == 200
    if not has_read_perm(get_perms(user, frame.scan.experiment.project)):
        assert resp.data == {
            'count': 0,
            'next': None,
            'previous': None,
            'results': [],
        }
    else:
        assert resp.data == {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [
                {
                    'id': frame.id,
                    'frame_number': frame.frame_number,
                    'frame_evaluation': None,
                }
            ],
        }


@pytest.mark.django_db
def test_experiment_lock_acquire_requires_auth(api_client, experiment):
    resp = api_client.post(f'/api/v1/experiments/{experiment.id}/lock')
    assert resp.status_code == 401


@pytest.mark.django_db
def test_experiment_lock_acquire(user_api_client, experiment, user):
    resp = user_api_client(project=experiment.project).post(
        f'/api/v1/experiments/{experiment.id}/lock'
    )
    if not has_review_perm(get_perms(user, experiment.project)):
        assert resp.status_code == 401
    else:
        assert resp.status_code == 200

        experiment.refresh_from_db()
        assert experiment.lock_owner == user


@pytest.mark.django_db
def test_experiment_lock_reacquire_ok(user_api_client, experiment_factory, user):
    experiment = experiment_factory(lock_owner=user)
    resp = user_api_client(project=experiment.project).post(
        f'/api/v1/experiments/{experiment.id}/lock'
    )
    if not has_review_perm(get_perms(user, experiment.project)):
        assert resp.status_code == 401
    else:
        assert resp.status_code == 200


@pytest.mark.django_db
def test_experiment_lock_denied(user_api_client, experiment_factory, user_factory, user):
    owner = user_factory()
    experiment = experiment_factory(lock_owner=owner)
    resp = user_api_client(project=experiment.project).post(
        f'/api/v1/experiments/{experiment.id}/lock'
    )
    if not has_review_perm(get_perms(user, experiment.project)):
        assert resp.status_code == 401
    else:
        assert resp.status_code == 409

        experiment.refresh_from_db()
        assert experiment.lock_owner == owner


@pytest.mark.django_db
def test_experiment_lock_release(user_api_client, experiment_factory, user):
    experiment = experiment_factory(lock_owner=user)
    resp = user_api_client(project=experiment.project).delete(
        f'/api/v1/experiments/{experiment.id}/lock'
    )
    if not has_review_perm(get_perms(user, experiment.project)):
        assert resp.status_code == 401
    else:
        assert resp.status_code == 200

        experiment.refresh_from_db()
        assert experiment.lock_owner is None


@pytest.mark.django_db
def test_experiment_lock_only_owner_can_release(
    user_api_client, experiment_factory, user_factory, user
):
    owner = user_factory()
    experiment = experiment_factory(lock_owner=owner)
    resp = user_api_client(project=experiment.project).delete(
        f'/api/v1/experiments/{experiment.id}/lock'
    )
    if not has_review_perm(get_perms(user, experiment.project)):
        assert resp.status_code == 401
    else:
        assert resp.status_code == 409

        experiment.refresh_from_db()
        assert experiment.lock_owner.id == owner.id


@pytest.mark.django_db
def test_read_without_lock_ok(user_api_client, scan_decision, user):
    resp = user_api_client().get(f'/api/v1/scan-decisions/{scan_decision.id}')
    if not has_read_perm(get_perms(user, scan_decision.scan.experiment.project)):
        assert resp.status_code == 404
    else:
        assert resp.status_code == 200


@pytest.mark.django_db
def test_create_scan_decision_without_lock_fails(user_api_client, scan, user):
    resp = user_api_client().post(
        '/api/v1/scan-decisions',
        data={
            'scan': scan.id,
            'decision': 'Good',
        },
    )
    if not has_review_perm(get_perms(user, scan.experiment.project)):
        assert resp.status_code == 401
    else:
        assert resp.status_code == 403
        assert resp.data['detail'] == 'You must lock the experiment before performing this action.'


@pytest.mark.django_db
def test_create_scan_decision_with_lock(user_api_client, scan, user):
    scan.experiment.lock_owner = user
    scan.experiment.save(update_fields=['lock_owner'])

    resp = user_api_client().post(
        '/api/v1/scan-decisions',
        data={
            'scan': scan.id,
            'decision': 'Good',
            'note': '',
        },
    )
    if not has_review_perm(get_perms(user, scan.experiment.project)):
        assert resp.status_code == 401
    else:
        assert resp.status_code == 201
        decisions = scan.decisions.all()
        assert len(decisions) == 1
        assert decisions[0].decision == 'Good'
