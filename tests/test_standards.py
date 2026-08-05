"""US-7 — Translatable, self-documenting field metadata + deliberate indexing.

FS-002 extends the vocabulary to four models (``ConceptScheme``, ``Concept``,
``ConceptLabel``, ``ConceptNote``). This suite holds every one of them to the
same standard #15 set for the first two:

- Article XII: every editable field carries a lazily-translatable ``verbose_name``
  and a non-empty, lazily-translatable ``help_text``; user-facing validation
  messages are translatable with *named* placeholders (the
  ``ValidationError(msgid, params=…)`` form — #15 ``decisions.md`` §9).
- Article XIII: indexing is deliberate. ``ConceptLabel`` is indexed on its
  ``(language, kind, text)`` lookup path and enforces one preferred label per
  language; ``ConceptNote.value`` is free prose and stays unindexed (FS-002
  ``decisions.md`` §20).

It walks ``_meta`` rather than a hand-listed field set, so a future field is
held to the same standard automatically.
"""

import pytest
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db.models import Model, UniqueConstraint
from django.utils.functional import Promise
from django.utils.text import Truncator

from controlled_vocabularies.exchange.report import (
    NormalizedEntry,
    NormalizedReason,
    SetAsideEntry,
    SetAsideReason,
)
from controlled_vocabularies.models import (
    Collection,
    CollectionMember,
    Concept,
    ConceptLabel,
    ConceptNote,
    ConceptRelation,
    ConceptScheme,
    validate_static_uri,
)

ALL_MODELS = [ConceptScheme, Concept, ConceptLabel, ConceptNote, ConceptRelation, Collection, CollectionMember]


def _editable_fields(model: type[Model]):
    """The model's own, user-editable, concrete fields (excludes the auto pk
    and reverse relations) — every one must meet the metadata standard."""
    return [
        field
        for field in model._meta.get_fields()
        if getattr(field, "concrete", False) and getattr(field, "editable", False) and not field.auto_created
    ]


# --- Article XII: every editable field carries lazy verbose_name + non-empty help_text ---


@pytest.mark.parametrize("model", ALL_MODELS)
def test_every_editable_field_has_metadata(model):
    fields = _editable_fields(model)
    assert fields, f"{model.__name__} exposes no editable fields to check"
    for field in fields:
        # help_text: present, non-empty, and a lazy translation proxy.
        assert field.help_text, f"{model.__name__}.{field.name} has no help_text"
        assert isinstance(field.help_text, Promise), (
            f"{model.__name__}.{field.name}.help_text is not lazily translatable"
        )
        # verbose_name: a lazy translation proxy (Django defaults it to a plain
        # str derived from the attribute name, which is not translatable).
        assert isinstance(field.verbose_name, Promise), (
            f"{model.__name__}.{field.name}.verbose_name is not lazily translatable"
        )


@pytest.mark.parametrize("model", ALL_MODELS)
def test_meta_verbose_names_are_lazy(model):
    assert isinstance(model._meta.verbose_name, Promise), (
        f"{model.__name__} Meta.verbose_name is not lazily translatable"
    )
    assert isinstance(model._meta.verbose_name_plural, Promise), (
        f"{model.__name__} Meta.verbose_name_plural is not lazily translatable"
    )


def test_app_config_verbose_name_is_lazy():
    from django.apps import apps

    verbose_name = apps.get_app_config("controlled_vocabularies").verbose_name
    assert isinstance(verbose_name, Promise), "AppConfig.verbose_name is not lazily translatable"


# --- Article XII: the new FS-002 validation messages are translatable, with named placeholders ---


def _inner_error(exc: ValidationError, field: str) -> ValidationError:
    """The single field-scoped ValidationError carrying the lazy message."""
    return exc.error_dict[field][0]


@pytest.mark.django_db
def test_missing_default_language_label_message_uses_named_placeholder(scheme):
    # FR-002: a concept needs a preferred label in the scheme's effective default
    # language. The refusal names that language through a *named* placeholder, so the
    # translatable msgid stays static and the language is supplied via params.
    with pytest.raises(ValidationError) as excinfo:
        Concept.objects.create(scheme=scheme, label="")
    err = _inner_error(excinfo.value, "label")
    assert isinstance(err.message, Promise), "missing-default-language-label message is not lazily translatable"
    assert "%(language)s" in str(err.message), "message lacks a named %(language)s placeholder"
    assert err.params == {"language": scheme.effective_default_language}
    # ...and it still renders with the real language substituted in.
    assert scheme.effective_default_language in excinfo.value.messages[0]


@pytest.mark.django_db
def test_duplicate_preferred_label_message_uses_named_placeholder(scheme):
    # FR-001: at most one preferred label per language. The second is refused with a
    # translatable, curator-facing message that names the language via a placeholder.
    concept = Concept.objects.create(scheme=scheme, label="Heat flow")
    concept.add_label(language="de", kind=ConceptLabel.Kind.PREFERRED, text="Wärmefluss")
    with pytest.raises(ValidationError) as excinfo:
        concept.add_label(language="de", kind=ConceptLabel.Kind.PREFERRED, text="Terrestrischer Wärmefluss")
    err = _inner_error(excinfo.value, "language")
    assert isinstance(err.message, Promise), "duplicate-preferred-label message is not lazily translatable"
    assert "%(language)s" in str(err.message), "message lacks a named %(language)s placeholder"
    assert err.params == {"language": "de"}
    assert "de" in excinfo.value.messages[0]


class TestStaticUriValidationMessages:
    """Article XII — the FS-005 ``static_uri`` metadata and validation messages.

    ``static_uri`` is added identically to ``ConceptScheme``, ``Concept``, and
    ``Collection``, all three already in ``ALL_MODELS`` above, so
    ``test_every_editable_field_has_metadata`` already holds its
    ``verbose_name`` and ``help_text`` to the standard. What that generic walk
    cannot see is whether each refusal this feature introduces is itself
    translatable and named — asserted explicitly below, one test per refusal,
    following the pattern above.
    """

    def test_static_uri_not_absolute_message_uses_named_placeholder(self):
        # FR-004/FR-010: a bare relative value is refused, naming the offending value.
        with pytest.raises(ValidationError) as excinfo:
            validate_static_uri("not-absolute")
        err = excinfo.value
        assert isinstance(err.message, Promise), "not-absolute message is not lazily translatable"
        assert "%(uri)s" in str(err.message), "message lacks a named %(uri)s placeholder"
        assert err.params == {"uri": "not-absolute"}
        assert "not-absolute" in excinfo.value.messages[0]

    def test_static_uri_unsafe_scheme_message_uses_named_placeholders(self, settings):
        # FR-004/FR-010: a scheme that can carry executable content is refused, naming
        # both the value and the offending scheme. "javascript" is outside the default
        # allowlist (T035) so it would already be refused there; the allowlist is
        # overridden to include it so this exercises the denylist's own message.
        settings.CONTROLLED_VOCABULARIES_ALLOWED_URI_SCHEMES = ["http", "https", "javascript"]
        with pytest.raises(ValidationError) as excinfo:
            validate_static_uri("javascript:alert(1)")
        err = excinfo.value
        assert isinstance(err.message, Promise), "unsafe-scheme message is not lazily translatable"
        assert "%(uri)s" in str(err.message) and "%(scheme)s" in str(err.message)
        assert err.params == {"uri": "javascript:alert(1)", "scheme": "javascript"}
        assert "javascript" in excinfo.value.messages[0]
        assert err.code == "static_uri_unsafe_scheme"

    def test_static_uri_scheme_not_allowed_message_uses_named_placeholders(self):
        # T035: a scheme outside the configured allowlist is refused, naming both the
        # value and the offending scheme.
        with pytest.raises(ValidationError) as excinfo:
            validate_static_uri("file:///etc/passwd")
        err = excinfo.value
        assert isinstance(err.message, Promise), "scheme-not-allowed message is not lazily translatable"
        assert "%(uri)s" in str(err.message) and "%(scheme)s" in str(err.message)
        assert err.params == {"uri": "file:///etc/passwd", "scheme": "file"}
        assert err.code == "static_uri_scheme_not_allowed"

    def test_static_uri_too_long_message_uses_named_placeholders(self):
        # FR-004/FR-010: an over-length identifier is refused, naming the bound and the
        # offending value's actual length. The echoed value itself is bounded to 80 chars
        # (T032) — a hostile value can be arbitrarily long, and echoing it in full would
        # make the message itself another hazard — but the true length is still reported.
        overlong = "http://example.org/" + "x" * 500
        with pytest.raises(ValidationError) as excinfo:
            validate_static_uri(overlong)
        err = excinfo.value
        assert isinstance(err.message, Promise), "too-long message is not lazily translatable"
        assert all(placeholder in str(err.message) for placeholder in ("%(max_length)s", "%(uri)s", "%(length)s"))
        assert err.params == {"max_length": 500, "uri": str(Truncator(overlong).chars(80)), "length": len(overlong)}

    def test_static_uri_unparseable_message_uses_named_placeholder(self):
        # T031: urllib.parse.urlsplit raises a bare ValueError for some malformed input
        # (e.g. a netloc invalid under NFKC normalization); caught and re-raised as a
        # translatable ValidationError naming the offending value.
        with pytest.raises(ValidationError) as excinfo:
            validate_static_uri("http://exa℀mple.com/x")
        err = excinfo.value
        assert isinstance(err.message, Promise), "unparseable message is not lazily translatable"
        assert "%(uri)s" in str(err.message), "message lacks a named %(uri)s placeholder"
        assert err.params == {"uri": "http://exa℀mple.com/x"}
        assert err.code == "static_uri_unparseable"


# --- FS-007: the two new closed-vocabulary import report reasons are translatable, named-placeholder messages ---


class TestImportLanguageMessagesUseNamedPlaceholders:
    """Article XII / SC-018 — this feature adds two entries to the importer's
    closed reason vocabularies (``report.py``): ``NormalizedReason.LANGUAGE_SUBSTITUTION``
    and the contest-loser ``SetAsideReason.VARIANT_NOT_KEPT``. Each must be
    lazily translatable and carry only named placeholders, the same standard
    the field-metadata and validation-message tests above hold every other
    curator-facing message to.
    """

    def test_language_substitution_reason_message_uses_named_placeholders(self):
        # FR-006/FR-012: a value stored under a configured language other than its
        # published tag names both the published tag and the language it was stored
        # under, via named placeholders rather than positional ones.
        assert isinstance(NormalizedReason.LANGUAGE_SUBSTITUTION.template, Promise), (
            "LANGUAGE_SUBSTITUTION template is not lazily translatable"
        )
        template = str(NormalizedReason.LANGUAGE_SUBSTITUTION.template)
        assert "%(language)s" in template and "%(kept_as)s" in template, (
            "LANGUAGE_SUBSTITUTION template lacks named %(language)s/%(kept_as)s placeholders"
        )
        entry = NormalizedEntry(
            reason=NormalizedReason.LANGUAGE_SUBSTITUTION,
            subject="https://example.org/vocab/rocks/granite",
            params={"language": "en-gb", "kept_as": "en"},
        )
        rendered = entry.render()
        assert "en-gb" in rendered
        assert "en" in rendered

    def test_variant_not_kept_reason_message_uses_named_placeholders(self):
        # FR-005/FR-012: a contest loser names the published tag it lost and the
        # configured language it lost to, via named placeholders rather than positional
        # ones.
        assert isinstance(SetAsideReason.VARIANT_NOT_KEPT.template, Promise), (
            "VARIANT_NOT_KEPT template is not lazily translatable"
        )
        template = str(SetAsideReason.VARIANT_NOT_KEPT.template)
        assert "%(language)s" in template and "%(kept_as)s" in template, (
            "VARIANT_NOT_KEPT template lacks named %(language)s/%(kept_as)s placeholders"
        )
        entry = SetAsideEntry(
            reason=SetAsideReason.VARIANT_NOT_KEPT,
            subject="https://example.org/vocab/rocks/granite",
            params={"language": "en-us", "kept_as": "en-gb"},
        )
        rendered = entry.render()
        assert "en-us" in rendered
        assert "en-gb" in rendered


# --- Article XIII: indexing is deliberate on the two new models ---


def test_concept_label_lookup_path_is_indexed():
    # FR-015: the (language, kind, text) lookup/search path is indexed.
    indexed = [tuple(index.fields) for index in ConceptLabel._meta.indexes]
    assert ("language", "kind", "text") in indexed, (
        f"ConceptLabel is missing a (language, kind, text) index; has {indexed}"
    )


def test_concept_label_has_one_preferred_per_language_constraint():
    constraint = next(
        (
            c
            for c in ConceptLabel._meta.constraints
            if isinstance(c, UniqueConstraint) and c.name == "one_preferred_label_per_language"
        ),
        None,
    )
    assert constraint is not None, "missing one_preferred_label_per_language partial unique constraint"
    assert tuple(constraint.fields) == ("concept", "language")
    assert constraint.condition is not None, "the preferred-label uniqueness must be a *partial* constraint"


def test_concept_note_value_is_unindexed():
    # decisions.md §20: value is free documentary prose with no lookup path this
    # slice, so it carries no db_index and appears in no explicit index.
    assert ConceptNote._meta.get_field("value").db_index is False, "ConceptNote.value must stay unindexed"
    for index in ConceptNote._meta.indexes:
        assert "value" not in index.fields, "ConceptNote.value must not be part of any index"


def test_concept_note_and_label_fks_are_indexed():
    # FKs are auto-indexed; assert it holds for the two new child models.
    assert ConceptLabel._meta.get_field("concept").db_index is True
    assert ConceptNote._meta.get_field("concept").db_index is True


# --- FS-003: the relation model meets the same metadata + indexing standard ---


def _authored_nonfield_error(exc: ValidationError) -> ValidationError:
    """The authored non-field ValidationError (params-bearing, else the first).

    The relation invariants raise non-field errors under ``__all__``; ``full_clean`` may
    append the DB constraint's own message alongside ours, so pick the one we authored.
    """
    errors = exc.error_dict[NON_FIELD_ERRORS]
    return next((e for e in errors if getattr(e, "params", None)), errors[0])


@pytest.mark.django_db
def test_self_relation_message_is_translatable():
    # FR-006: a self message names nothing dynamic, so it carries no placeholder — but it
    # must still be a lazily-translatable string, not a bare str.
    scheme = ConceptScheme.objects.create(name="Rock types")
    granite = Concept.objects.create(scheme=scheme, label="Granite")
    with pytest.raises(ValidationError) as excinfo:
        granite.add_broader(granite)
    err = _authored_nonfield_error(excinfo.value)
    assert isinstance(err.message, Promise), "self-relation message is not lazily translatable"


@pytest.mark.django_db
def test_cross_vocabulary_relation_message_uses_named_placeholders():
    # FR-009: the refusal names both vocabularies via *named* placeholders so the msgid stays static.
    rocks = ConceptScheme.objects.create(name="Rock types")
    minerals = ConceptScheme.objects.create(name="Minerals")
    granite = Concept.objects.create(scheme=rocks, label="Granite")
    quartz = Concept.objects.create(scheme=minerals, label="Quartz")
    with pytest.raises(ValidationError) as excinfo:
        granite.add_related(quartz)
    err = _authored_nonfield_error(excinfo.value)
    assert isinstance(err.message, Promise), "cross-vocabulary message is not lazily translatable"
    assert "%(source)s" in str(err.message) and "%(target)s" in str(err.message)
    assert set(err.params) == {"source", "target"}


@pytest.mark.django_db
def test_disjointness_message_uses_named_placeholder():
    # FR-008: the refusal names the conflicting kind via a placeholder.
    scheme = ConceptScheme.objects.create(name="Rock types")
    granite = Concept.objects.create(scheme=scheme, label="Granite")
    igneous = Concept.objects.create(scheme=scheme, label="Igneous rock")
    granite.add_broader(igneous)
    with pytest.raises(ValidationError) as excinfo:
        granite.add_related(igneous)
    err = _authored_nonfield_error(excinfo.value)
    assert isinstance(err.message, Promise), "disjointness message is not lazily translatable"
    assert "%(kind)s" in str(err.message)
    assert set(err.params) == {"kind"}


def test_concept_relation_reverse_read_path_is_indexed():
    # FR-012 / research R6: the (target, kind) reverse-read path is indexed deliberately.
    indexed = [tuple(index.fields) for index in ConceptRelation._meta.indexes]
    assert ("target", "kind") in indexed, f"ConceptRelation missing a (target, kind) index; has {indexed}"


def test_concept_relation_has_unique_and_self_constraints():
    names = {c.name for c in ConceptRelation._meta.constraints}
    assert "unique_concept_relation" in names, "missing the (source, target, kind) unique constraint (FR-007)"
    assert "concept_relation_not_self" in names, "missing the not-self check constraint (FR-006)"
    unique = next(c for c in ConceptRelation._meta.constraints if c.name == "unique_concept_relation")
    assert tuple(unique.fields) == ("source", "target", "kind")


def test_concept_relation_fks_are_indexed():
    # FKs are auto-indexed; the source-leading composite comes from the unique constraint,
    # the target-leading from the explicit index above.
    assert ConceptRelation._meta.get_field("source").db_index is True
    assert ConceptRelation._meta.get_field("target").db_index is True


# --- FS-004: the collection models meet the same metadata + indexing standard ---
# (Collection and CollectionMember are in ALL_MODELS above, so the field-metadata and
# Meta.verbose_name walks already cover them. Below: the new validation messages and the
# deliberate indexing decision.)


@pytest.mark.django_db
def test_cross_vocabulary_membership_message_uses_named_placeholders():
    # FR-005: adding a concept from another vocabulary names both vocabularies via *named*
    # placeholders so the translatable msgid stays static.
    rocks = ConceptScheme.objects.create(name="Rocks")
    minerals = ConceptScheme.objects.create(name="Minerals")
    igneous = Collection.objects.create(scheme=rocks, name="Igneous")
    mica = Concept.objects.create(scheme=minerals, label="Mica")
    with pytest.raises(ValidationError) as excinfo:
        igneous.add(mica)
    err = _authored_nonfield_error(excinfo.value)
    assert isinstance(err.message, Promise), "cross-vocabulary membership message is not lazily translatable"
    assert "%(concept_scheme)s" in str(err.message) and "%(collection_scheme)s" in str(err.message)
    assert set(err.params) == {"concept_scheme", "collection_scheme"}


@pytest.mark.django_db
def test_not_ordered_guard_message_uses_named_placeholder():
    # FR-006: ordering an unordered collection is refused with a translatable message that
    # names the collection via a placeholder.
    scheme = ConceptScheme.objects.create(name="Rocks")
    granite = Concept.objects.create(scheme=scheme, label="Granite")
    plain = Collection.objects.create(scheme=scheme, name="A set")
    plain.add(granite)
    with pytest.raises(ValidationError) as excinfo:
        plain.set_member_order([granite])
    # a non-field ValidationError raised directly (no error_dict); read messages/params off it
    assert isinstance(excinfo.value.messages[0], str)
    err = excinfo.value.error_list[0]
    assert isinstance(err.message, Promise), "not-ordered guard message is not lazily translatable"
    assert "%(name)s" in str(err.message)
    assert set(err.params) == {"name"}


def test_collection_member_has_held_once_constraint_and_order_index():
    # FR-004 / Article XIII: held-once is a DB unique constraint; the ordered read is index-backed.
    names = {c.name for c in CollectionMember._meta.constraints}
    assert "unique_collection_member" in names, "missing the (collection, concept) held-once constraint (FR-004)"
    unique = next(c for c in CollectionMember._meta.constraints if c.name == "unique_collection_member")
    assert tuple(unique.fields) == ("collection", "concept")
    indexed = [tuple(index.fields) for index in CollectionMember._meta.indexes]
    assert ("collection", "position") in indexed, (
        f"CollectionMember missing a (collection, position) index; has {indexed}"
    )


def test_collection_has_per_scheme_unique_slug_constraint():
    # FR-009: two collections in one vocabulary are distinguishable by a per-scheme-unique slug.
    constraint = next(
        (
            c
            for c in Collection._meta.constraints
            if isinstance(c, UniqueConstraint) and c.name == "unique_collection_slug_per_scheme"
        ),
        None,
    )
    assert constraint is not None, "missing unique_collection_slug_per_scheme constraint"
    assert tuple(constraint.fields) == ("scheme", "slug")


def test_collection_member_fks_are_indexed():
    # FKs are auto-indexed; the reverse read (a concept's collections) rides the concept FK index.
    assert CollectionMember._meta.get_field("collection").db_index is True
    assert CollectionMember._meta.get_field("concept").db_index is True


class TestStaticUriIndexing:
    """FS-005 — ``static_uri``'s indexing decision (data-model.md "Indexing decision").

    ``static_uri`` is indexed by its own partial unique constraint, and
    nothing else in this feature gains an index: ``local_url``, ``uri``, and
    ``has_static_uri`` are properties, not columns, composed from slug fields
    R1 already indexed and constrained.
    """

    @pytest.mark.parametrize("model", [ConceptScheme, Concept, Collection])
    def test_static_uri_is_covered_only_by_its_partial_unique_constraint(self, model):
        field = model._meta.get_field("static_uri")
        assert field.db_index is False, f"{model.__name__}.static_uri must not carry a plain db_index"
        for index in model._meta.indexes:
            assert "static_uri" not in index.fields, (
                f"{model.__name__}.static_uri must not appear in any explicit Meta.indexes entry"
            )
        constraint_name = f"{model.__name__.lower()}_static_uri_unique"
        constraint = next(
            (c for c in model._meta.constraints if isinstance(c, UniqueConstraint) and c.name == constraint_name),
            None,
        )
        assert constraint is not None, f"missing {constraint_name} partial unique constraint"
        assert tuple(constraint.fields) == ("static_uri",)
        assert constraint.condition is not None, "static_uri's uniqueness must be a *partial* constraint"

    def test_local_url_and_has_static_uri_are_properties_not_indexable_columns(self):
        # Neither local_url nor has_static_uri is a model field, so neither can carry an
        # index; they compose from slug fields already indexed/constrained by R1.
        for model in (ConceptScheme, Concept, Collection):
            field_names = {field.name for field in model._meta.get_fields()}
            assert "local_url" not in field_names, f"{model.__name__}.local_url must not be a model field"
            assert "has_static_uri" not in field_names, f"{model.__name__}.has_static_uri must not be a model field"
            assert isinstance(model.local_url, property)
            assert isinstance(model.has_static_uri, property)


class TestStaticUriFieldAttributesAgree:
    """Review round 4. ``ConceptScheme``, ``Concept``, and ``Collection`` each
    redeclared the entire ``static_uri`` field — ``max_length``, ``null``,
    ``blank``, ``verbose_name``, and ``validators`` byte-identical, only
    ``help_text`` legitimately differing per model. Nothing asserted they
    agreed, so one model's ``max_length`` (say) could drift silently and
    every one of the existing tests would still pass. This walks the three
    concrete models' own field and fails the moment one of the shared
    attributes stops matching the others.
    """

    def test_the_three_concrete_models_static_uri_fields_agree_on_every_shared_attribute(self):
        fields = {model: model._meta.get_field("static_uri") for model in (ConceptScheme, Concept, Collection)}
        max_lengths = {model.__name__: field.max_length for model, field in fields.items()}
        nulls = {model.__name__: field.null for model, field in fields.items()}
        blanks = {model.__name__: field.blank for model, field in fields.items()}
        verbose_names = {model.__name__: str(field.verbose_name) for model, field in fields.items()}

        # Validators are compared by (type, limit_value) rather than identity or raw repr:
        # Django gives every field its own MaxLengthValidator *instance* (derived from
        # max_length), so instances that are equivalent are still distinct objects with
        # distinct default reprs — comparing raw repr would report a false disagreement.
        def _validator_signature(v):
            return (type(v).__name__, getattr(v, "limit_value", None), getattr(v, "__qualname__", None))

        validator_reprs = {
            model.__name__: [_validator_signature(v) for v in field.validators] for model, field in fields.items()
        }
        assert len(set(max_lengths.values())) == 1, f"static_uri.max_length disagrees across models: {max_lengths}"
        assert len(set(nulls.values())) == 1, f"static_uri.null disagrees across models: {nulls}"
        assert len(set(blanks.values())) == 1, f"static_uri.blank disagrees across models: {blanks}"
        assert len(set(verbose_names.values())) == 1, (
            f"static_uri.verbose_name disagrees across models: {verbose_names}"
        )
        assert len({tuple(v) for v in validator_reprs.values()}) == 1, (
            f"static_uri.validators disagrees across models: {validator_reprs}"
        )
