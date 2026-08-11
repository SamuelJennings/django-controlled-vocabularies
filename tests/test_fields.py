"""Tests for ``controlled_vocabularies.fields``.

Phase F (T001) covers only ``ConceptField`` construction, unbound to any consuming
model — no model declares the field yet, so every test here builds the field
directly rather than through a model instance. The bound behaviour (declaring it
on a model, saving, reading back) is US-1's (T003/T004) and is out of scope.

- ``TestConceptFieldConstruction`` — the fixed kwargs, the two construction-time
  rejections, and that building the field issues no query (FR-003's mechanism).
- ``TestConceptFieldValidate`` — the ``validate()`` override that makes the
  translated, vocabulary-naming message interpolate instead of raising
  ``KeyError`` the first time anything reads it.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import PROTECT, Q
from django.test.utils import CaptureQueriesContext
from django.utils.functional import Promise

from controlled_vocabularies.fields import ConceptField
from controlled_vocabularies.models import Concept


class TestConceptFieldConstruction:
    """FR-001, FR-002, FR-007, FR-010 — the kwargs a consumer does not supply."""

    def test_fixes_to_concept(self):
        field = ConceptField(vocabulary="rock-type")
        assert field.remote_field.model is Concept

    def test_fixes_on_delete_to_protect(self):
        field = ConceptField(vocabulary="rock-type")
        assert field.remote_field.on_delete is PROTECT

    def test_fixes_limit_choices_to_the_named_vocabulary(self):
        field = ConceptField(vocabulary="rock-type")
        assert field.get_limit_choices_to() == Q(scheme__slug="rock-type")

    @pytest.mark.django_db
    def test_construction_issues_no_queries(self):
        """FR-003's mechanism: the ``Q`` is constructed, never evaluated."""
        with CaptureQueriesContext(connection) as ctx:
            ConceptField(vocabulary="rock-type")
        assert len(ctx.captured_queries) == 0

    def test_rejects_consumer_supplied_on_delete(self):
        with pytest.raises(TypeError, match="on_delete"):
            ConceptField(vocabulary="rock-type", on_delete=PROTECT)

    def test_rejects_missing_vocabulary(self):
        with pytest.raises(TypeError, match="vocabulary"):
            ConceptField()

    def test_rejects_empty_vocabulary(self):
        with pytest.raises(TypeError, match="vocabulary"):
            ConceptField(vocabulary="")

    def test_help_text_has_a_translatable_default(self):
        field = ConceptField(vocabulary="rock-type")
        assert isinstance(field.help_text, Promise)
        assert str(field.help_text)

    def test_help_text_default_is_overridable(self):
        field = ConceptField(vocabulary="rock-type", help_text="Pick a rock type.")
        assert field.help_text == "Pick a rock type."

    def test_error_messages_invalid_carries_named_vocabulary_placeholder(self):
        field = ConceptField(vocabulary="rock-type")
        assert "%(vocabulary)s" in field.error_messages["invalid"]


class TestConceptFieldValidate:
    """The ``validate()`` override (design review finding, verified against the
    installed Django 5.2.16 source): without it, ``ForeignKey.validate()``'s
    ``ValidationError`` carries only ``model``/``pk``/``field``/``value`` in
    ``params``, and a message with ``%(vocabulary)s`` raises ``KeyError`` the
    first time anything reads ``.messages`` or ``str()`` rather than returning
    text. Asserting only that ``ValidationError`` was raised would not exercise
    that failure mode at all — these tests read ``.messages``.
    """

    @pytest.mark.django_db
    def test_invalid_value_message_names_the_vocabulary(self):
        field = ConceptField(vocabulary="rock-type")
        with pytest.raises(ValidationError) as exc_info:
            field.validate(999999, None)
        # Reading .messages is exactly the call that raises KeyError without
        # the validate() override — the field's own error_messages['invalid']
        # names the vocabulary, not Django's default "does not exist" text.
        (message,) = exc_info.value.messages
        assert "rock-type" in message

    @pytest.mark.django_db
    def test_invalid_value_str_also_interpolates(self):
        field = ConceptField(vocabulary="rock-type")
        with pytest.raises(ValidationError) as exc_info:
            field.validate(999999, None)
        assert "rock-type" in str(exc_info.value)

    @pytest.mark.django_db
    def test_invalid_code_is_preserved(self):
        field = ConceptField(vocabulary="rock-type")
        with pytest.raises(ValidationError) as exc_info:
            field.validate(999999, None)
        assert exc_info.value.code == "invalid"
