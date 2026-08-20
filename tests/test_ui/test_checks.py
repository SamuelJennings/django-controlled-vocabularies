"""Tests for :mod:`controlled_vocabularies.ui.checks` (T005)."""

import sys

from django.core import checks as django_checks

from controlled_vocabularies.ui.checks import CHECK_ID, check_mvp_installed


class TestCheckMVPInstalled:
    """FR-012's neighbour: a project that forgets the ``ui`` extra learns so at
    ``manage.py check``, naming both the extra to install and the app that requires it, rather
    than from a bare ``ModuleNotFoundError: mvp`` raised from URL loading."""

    def test_reports_nothing_when_mvp_is_importable(self):
        assert check_mvp_installed(None) == []

    def test_reports_one_error_naming_the_extra_and_the_app_when_mvp_is_absent(self, monkeypatch):
        # ``mvp`` is genuinely installed in this environment (the ``ui`` extra is a dev
        # dependency of this repo's own test run) — sys.modules["mvp"] = None is the standard
        # way to make a real ``import mvp`` statement raise ImportError regardless, without
        # touching the module the rest of the suite already has loaded.
        monkeypatch.setitem(sys.modules, "mvp", None)

        errors = check_mvp_installed(None)

        assert len(errors) == 1
        error = errors[0]
        assert isinstance(error, django_checks.Error)
        assert error.id == CHECK_ID
        message = str(error.msg)
        assert "django-controlled-vocabularies[ui]" in message
        assert "controlled_vocabularies.ui" in message

    def test_reported_object_is_an_error_not_a_warning(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "mvp", None)

        errors = check_mvp_installed(None)

        assert errors
        for error in errors:
            assert isinstance(error, django_checks.Error)
