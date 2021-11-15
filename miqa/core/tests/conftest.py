import os
from pathlib import Path

from guardian.shortcuts import assign_perm
import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from miqa.core.models import Project

from .factories import (
    ExperimentFactory,
    FrameFactory,
    ProjectFactory,
    ScanDecisionFactory,
    ScanFactory,
    UserFactory,
)


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture(params=[None, 'superuser'] + Project.get_read_permission_groups())
def user_api_client(request, api_client, user, project) -> APIClient:
    def _method(**kwargs):
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
