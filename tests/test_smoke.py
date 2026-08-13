"""Package-level checks whose subject is the installed package rather than one module.

Currently the import contract for the ``django-tomselect`` runtime dependency
(T001, FR-015). Article VIII pins compatibility to names rather than to a version:
a later release of ``django-tomselect`` that renames one of these symbols fails
here, at the dependency boundary, rather than later at form render.

Article X mirrors a test module onto a source module; ``test_smoke.py`` is the
standing exception for a check that has no single source module to mirror.
"""

from django.apps import apps


class TestDjangoTomselectDependency:
    """``django-tomselect`` is declared, installed and exposes the names this
    package's views and forms build on."""

    def test_app_is_installed(self):
        assert apps.is_installed("django_tomselect")

    def test_autocomplete_model_view_is_importable(self):
        from django_tomselect.autocompletes import AutocompleteModelView

        assert AutocompleteModelView is not None

    def test_tomselect_model_choice_field_is_importable(self):
        from django_tomselect.forms import TomSelectModelChoiceField

        assert TomSelectModelChoiceField is not None

    def test_tomselect_model_multiple_choice_field_is_importable(self):
        from django_tomselect.forms import TomSelectModelMultipleChoiceField

        assert TomSelectModelMultipleChoiceField is not None
