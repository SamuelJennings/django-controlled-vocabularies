"""Minimal Django settings for the test suite."""

SECRET_KEY = "test-key-not-for-production"

USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "controlled_vocabularies",
]

# Fixed base so URI-composition assertions are deterministic across the test suite.
CONTROLLED_VOCABULARIES_BASE_URI = "https://example.org/vocabularies"
