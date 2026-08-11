"""App config for :mod:`tests.testapp` — the consuming test app (T002).

Lives under ``tests/`` rather than in ``controlled_vocabularies`` itself: a
consumer of this package's own public API (:class:`~controlled_vocabularies.fields.ConceptField`)
belongs to the test suite, not the distribution — shipping it as a package app
would make a fixture an accidental part of every install (``plan.md``,
Structure Decision).
"""

from django.apps import AppConfig


class TestappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tests.testapp"
    label = "testapp"
