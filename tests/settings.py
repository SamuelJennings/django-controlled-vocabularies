"""Minimal Django settings for the test suite."""

SECRET_KEY = "test-key-not-for-production"

USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Deterministic language set for the multilingual suite: a fixed default plus two
# more so per-language behaviour (default-anchored slugs, one-preferred-per-language)
# is exercised without depending on Django's full built-in LANGUAGES list.
USE_I18N = True
LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("de", "German"),
    ("fr", "French"),
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_tomselect",
    "controlled_vocabularies",
    "tests.testapp",
]

# Fixed base so URI-composition assertions are deterministic across the test suite.
CONTROLLED_VOCABULARIES_BASE_URI = "https://example.org/vocabularies"
