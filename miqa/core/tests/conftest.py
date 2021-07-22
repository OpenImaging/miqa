import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from .factories import (
    AnnotationFactory,
    ExperimentFactory,
    ImageFactory,
    NoteFactory,
    ScanFactory,
    SessionFactory,
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


register(AnnotationFactory)
register(UserFactory)
register(SiteFactory)
register(SessionFactory)
register(ExperimentFactory)
register(ScanFactory)
register(NoteFactory)
register(ImageFactory)
