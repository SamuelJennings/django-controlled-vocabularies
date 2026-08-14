"""The FR-006 proof: a project that never installs ``django.contrib.admin``
(specs/012-concept-selection-in-the-admin/tasks.md T014).

Otherwise identical to ``tests/settings.py``, minus the admin app itself and
the three middleware/app entries that exist only to satisfy the admin's own
system checks (``admin.E4xx``) — session, auth and message middleware, and
their supporting installed apps. Run out of process, per ``decisions.md``
D13: a Python process' app registry is built once at startup, so proving the
admin absent needs a fresh interpreter, not an ``override_settings`` inside
the main suite.
"""

from django.core.management.utils import get_random_secret_key

# Generated per run rather than written down: this configuration is only ever
# loaded by a throwaway subprocess that renders one form, nothing it signs
# outlives that process, and a key literal in a second file is one more
# credential-shaped string for a scanner to find.
SECRET_KEY = get_random_secret_key()

ROOT_URLCONF = "tests.urls_no_admin"

# The third wiring step a real project makes (011 decisions.md D15): django_tomselect
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
