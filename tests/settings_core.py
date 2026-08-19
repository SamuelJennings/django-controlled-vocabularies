"""Minimal Django settings for the test suite — the core-only base.

This is the base ``tests/settings.py`` imports from and appends the opt-in ui front end to, not
a copy of it (013-find-a-vocabulary plan.md, Structure Decision). Its own ``ROOT_URLCONF`` points
at an empty urlconf, and it stays free of ``controlled_vocabularies.ui`` and every ui dependency —
it is what the core-only boot test (``tests/test_ui/test_boot.py``) boots against to prove the
core still starts with nothing ui installed.
"""

SECRET_KEY = "test-key-not-for-production"

ROOT_URLCONF = "tests.urls_core"

# The third wiring step a real project makes (011 decisions.md D15): django_tomselect
# builds the control's full context only when its thread-local request is set, and
# only this middleware sets it. The test project wires what a real one wires.
#
# The session, authentication and message middleware are django.contrib.admin's own
# requirements (its admin.E4xx system checks refuse to start without them), added for
# the admin suite. tests/settings_no_admin.py is the configuration that proves a
# project without the admin is unaffected.
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
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
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django_tomselect",
    "controlled_vocabularies",
    "tests.testapp",
]

# django.contrib.admin renders through the template engine and needs these three
# context processors; its own system checks enforce them. Nothing in the package
# requires a TEMPLATES entry of its own.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

STATIC_URL = "static/"

# Fixed base so URI-composition assertions are deterministic across the test suite.
CONTROLLED_VOCABULARIES_BASE_URI = "https://example.org/vocabularies"
