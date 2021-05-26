from miqa.core.models.site import Site
import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from .factories import SessionFactory, UserFactory, ExperimentFactory, ScanFactory, SiteFactory, ImageFactory, NoteFactory


@pytest.fixture
def api_client() -> APIClient:

    return APIClient()


@pytest.fixture
def authenticated_api_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


register(UserFactory)
register(SiteFactory)
register(SessionFactory)
register(ExperimentFactory)
register(ScanFactory)
register(NoteFactory)
register(ImageFactory)