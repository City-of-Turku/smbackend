import pytest


@pytest.fixture(autouse=True)
def use_dummy_cache(settings):
    """Use DummyCache for all tests to prevent Redis I/O from hanging the test suite."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }
