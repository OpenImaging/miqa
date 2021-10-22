import os
from pathlib import Path

import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from .factories import (
    ExperimentFactory,
    ImageFactory,
    NoteFactory,
    ProjectFactory,
    ScanDecisionFactory,
    ScanFactory,
    SiteFactory,
    UserFactory,
)


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def authenticated_api_client(api_client, user) -> APIClient:
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def staff_api_client(api_client, user_factory) -> APIClient:
    user = user_factory(is_staff=True)
    api_client.force_authenticate(user=user)
    return api_client


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
register(SiteFactory)
register(ProjectFactory)
register(ExperimentFactory)
register(ScanFactory)
register(NoteFactory)
register(ImageFactory)
