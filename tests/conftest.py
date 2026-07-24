"""Shared pytest fixtures.

Django settings are wired via ``DJANGO_SETTINGS_MODULE`` in ``pyproject.toml``;
pytest-django handles setup/teardown from there.

The object fixtures below are thin wrappers over the model factories. A test uses
one when it needs a scheme or a concept only as a precondition. A test that asserts
on a specific derived slug or URI builds its object inline instead, since the exact
name is then the thing under test.
"""

import pytest

from tests.factories import ConceptFactory, ConceptSchemeFactory


@pytest.fixture
def scheme(db):
    """A saved :class:`ConceptScheme` with an app-wide-unique generated name."""
    return ConceptSchemeFactory()


@pytest.fixture
def concept(db):
    """A saved :class:`Concept`, with its owning scheme auto-created."""
    return ConceptFactory()
