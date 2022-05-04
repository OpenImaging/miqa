import os
from pathlib import Path

from guardian.shortcuts import assign_perm
import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from miqa.core.models import Project
from miqa.core.tasks import import_data

from .factories import (
    ExperimentFactory,
    FrameFactory,
    ProjectFactory,
    ScanDecisionFactory,
    ScanFactory,
    UserFactory,
)
from .helpers import generate_import_csv


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture(params=[None, 'superuser'] + Project().get_read_permission_groups())
def user_api_client(request, api_client, user, project):
    def _method(**kwargs) -> APIClient:
        api_client.force_authenticate(user=user)
        if request.param:
            if request.param == 'superuser':
                user.is_superuser = True
                user.save()
            elif 'project' in kwargs:
                assign_perm(request.param, user, kwargs['project'])
            else:
                assign_perm(request.param, user, project)
        return api_client

    return _method


@pytest.fixture
def samples_dir():
    return Path(__file__).parent.parent.parent.parent / 'samples'


@pytest.fixture
def sample_scans(samples_dir):
    def generator():
        for dirpath, dirs, files in os.walk(samples_dir):
            if 'nifti_catalog.xml' in files:
                for dir in dirs:
                    scan_id, scan_type = dir.split('_')
                    yield (dirpath, scan_id, scan_type)

    return [scan for scan in generator()]


register(ScanDecisionFactory)
register(UserFactory)
register(ProjectFactory)
register(ExperimentFactory)
register(ScanFactory)
register(FrameFactory)


@pytest.fixture
def samples_project(tmp_path, sample_scans, project_factory):
    csv_file = str(tmp_path / 'import.csv')
    with open(csv_file, 'w') as fd:
        output, _writer = generate_import_csv([sample_scans[0]])
        fd.write(output.getvalue())
    project = project_factory(import_path=csv_file, name='ucsd')
    import_data(project_id=project.id)
    return project


@pytest.fixture
def log_in(webpack_server, page, page_login):
    """
    Log the given user into the page.

    This involves setting cookies as if the server has already approved the user. When navigating
    to the web app, it will see that the user has no session token and redirect to the API server,
    which thinks the user has already logged in and redirects back to the web app with a fresh
    session token.
    """

    async def _log_in(user):
        await page_login(page, user)
        await page.goto(webpack_server)
        return page

    return _log_in
