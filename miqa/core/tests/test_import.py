import pytest


@pytest.mark.django_db
def test_migrate():
    # TODO this test can be deleted once we have real database tests.
    # For now it's a placeholder to force the migrations to run in CI
    assert True
