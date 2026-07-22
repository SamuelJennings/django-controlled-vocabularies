"""Smoke test — the app installs and its config loads.

Replaced by real coverage as the v0.1 models, fields, and RDF import/export land.
"""

from django.apps import apps


def test_app_is_installed():
    assert apps.is_installed("controlled_vocabularies")


def test_app_config():
    config = apps.get_app_config("controlled_vocabularies")
    assert config.verbose_name == "Controlled Vocabularies"
