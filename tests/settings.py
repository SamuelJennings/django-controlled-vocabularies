"""Minimal Django settings for the test suite."""

SECRET_KEY = "test-key-not-for-production"

ROOT_URLCONF = "tests.urls"

# The third wiring step a real project makes (decisions.md D15): django_tomselect
# builds the control's full context only when its thread-local request is set, and
# only this middleware sets it. The test project wires what a real one wires.
MIDDLEWARE = [
    "django_tomselect.middleware.TomSelectMiddleware",
]

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
