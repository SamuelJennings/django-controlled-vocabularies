"""``ConceptField`` — attach a concept from a named vocabulary to a model.

A ``ForeignKey`` subclass a consuming project declares on its own model, naming
one vocabulary by its slug. It fixes three things the consumer does not supply
— ``to="controlled_vocabularies.Concept"``, ``on_delete=PROTECT``, and
``limit_choices_to`` restricted to that vocabulary — so almost everything
FR-002/FR-005/FR-006/FR-007 ask for falls out of ``limit_choices_to``: it is
what ``ForeignKey.validate()`` applies, and it is a ``Q``, so it is lazy and
never queries the database while the declaration is only being read (FR-003).
"""

from django.core.exceptions import ValidationError
from django.db.models import PROTECT, ForeignKey, ManyToManyField, Q
from django.utils.translation import gettext_lazy as _


class ConceptField(ForeignKey):
    """A ``ForeignKey`` to ``controlled_vocabularies.Concept``, constrained to
    one named vocabulary.

    ``vocabulary`` is the owning :class:`~controlled_vocabularies.models.ConceptScheme`'s
    slug — required and non-empty, since an unconstrained field would be a plain
    ``ForeignKey`` and offer none of this field's guarantees (FR-002). ``to``,
    ``on_delete`` and ``limit_choices_to`` are not the consumer's to supply:
    ``on_delete`` is refused outright (FR-007's guarantee is not theirs to
    weaken), while ``to`` and ``limit_choices_to`` are simply overwritten.

    ``to`` is always the *string* ``"controlled_vocabularies.Concept"``, never
    the imported class — deliberately, not a detail. Migration state rejects a
    resolved model class in a field's ``to``: ``ModelState`` has to be
    rebuildable without every referenced model already loaded, and raises
    ``ValueError`` the moment one holds a live class rather than a string. An
    ordinary ``ForeignKey`` never hits this, because its own ``deconstruct()``
    stringifies a live-class ``to`` before anything rebuilds from it — but
    this field's :meth:`deconstruct` strips ``to`` from the emitted kwargs
    entirely (T003), so ``__init__`` is the only place the string can come
    from. The consequence is real: with a string ``to``,
    ``remote_field.model`` only resolves once the field is attached to a
    model class (``RelatedField.contribute_to_class()`` defers to
    ``lazy_related_operation``), so an *unbound* field cannot run
    ``validate()`` — that assertion belongs to a task with a real consuming
    model (T005), not this one. The string form also means this module never
    imports :class:`~controlled_vocabularies.models.Concept`, which removes a
    circular-import risk.
    """

    default_error_messages = {
        "invalid": _("%(value)s is not a valid concept in the '%(vocabulary)s' vocabulary."),
    }

    def __init__(self, vocabulary=None, **kwargs):
        if not vocabulary:
            raise TypeError(
                "ConceptField() requires a non-empty 'vocabulary' naming the "
                "ConceptScheme slug to constrain choices to."
            )
        if "on_delete" in kwargs:
            raise TypeError("ConceptField() sets on_delete=PROTECT itself; a consumer may not override it.")
        if "limit_choices_to" in kwargs:
            raise TypeError(
                "ConceptField() sets limit_choices_to itself to constrain choices to "
                "'vocabulary'; a consumer may not override it."
            )
        self.vocabulary = vocabulary
        kwargs["to"] = "controlled_vocabularies.Concept"
        kwargs["on_delete"] = PROTECT
        kwargs["limit_choices_to"] = Q(scheme__slug=vocabulary)
        # A static message, not one interpolating `vocabulary`: `%` on a
        # gettext_lazy() proxy evaluates it immediately, which would defeat
        # the laziness this default exists to keep (translation happens at
        # access time, per request).
        kwargs.setdefault("help_text", _("A concept from this field's configured vocabulary."))
        super().__init__(**kwargs)

    def validate(self, value, model_instance):
        """Refuse a concept outside the named vocabulary, with a message that
        actually reads.

        ``ForeignKey.validate()`` builds its ``ValidationError``'s ``params``
        itself — ``model``, ``pk``, ``field``, ``value``, and nothing else
        (Django 5.2.16, ``django/db/models/fields/related.py``).
        ``ValidationError`` defers ``%``-substitution to iteration time
        (``message %= error.params`` in ``core/exceptions.py.__iter__``, which
        backs both ``.messages`` and ``str()``), so
        ``error_messages["invalid"]`` carrying ``%(vocabulary)s`` constructs
        fine and raises ``KeyError: 'vocabulary'`` the first time anything
        reads it. Catching the ``code="invalid"`` error here and re-raising
        with ``vocabulary`` in ``params`` is what gives the placeholder
        something to interpolate. This is a message concern only — the
        refusal itself is still ``limit_choices_to``. Only reachable on a
        field bound to a model (``remote_field.model`` must be resolved);
        proved end-to-end by T005 against a real test-app model.
        """
        try:
            super().validate(value, model_instance)
        except ValidationError as exc:
            if exc.code != "invalid":
                raise
            raise ValidationError(
                self.error_messages["invalid"],
                code="invalid",
                # Carry the ForeignKey's own params through. A consumer's
                # error_messages["invalid"] is free to use `model`, `pk` or
                # `field`, and dropping them would reproduce the same
                # KeyError-on-read this override exists to prevent.
                params={**(exc.params or {}), "value": value, "vocabulary": self.vocabulary},
            ) from exc

    def contribute_to_class(self, cls, name, private_only=False, **kwargs):
        """Add ``get_<name>_label()`` and ``get_<name>_uri()`` to the
        consuming model (FR-008, FR-009), named the way Django's own
        ``get_FOO_display()`` is (``Field.contribute_to_class``'s own
        precedent for a derived read named after a field).

        ``get_<name>_label()`` delegates to
        :meth:`~controlled_vocabularies.models.Concept.display_label`;
        ``get_<name>_uri()`` returns the attached concept's ``uri``
        unchanged. Both return ``None``, never raise, when nothing is
        attached. The ``setattr`` is guarded: a model that already defines
        either name keeps its own definition rather than having it
        silently overwritten.
        """
        super().contribute_to_class(cls, name, private_only=private_only, **kwargs)

        # Three-arg getattr, not two: on a required field with nothing attached
        # Django's forward descriptor raises RelatedObjectDoesNotExist rather
        # than returning None. It subclasses AttributeError, so a default turns
        # that back into the None both accessors promise.
        def get_label(instance):
            concept = getattr(instance, name, None)
            return concept.display_label() if concept is not None else None

        def get_uri(instance):
            concept = getattr(instance, name, None)
            return concept.uri if concept is not None else None

        label_attr_name = f"get_{name}_label"
        uri_attr_name = f"get_{name}_uri"
        if not hasattr(cls, label_attr_name):
            setattr(cls, label_attr_name, get_label)
        if not hasattr(cls, uri_attr_name):
            setattr(cls, uri_attr_name, get_uri)

    def deconstruct(self):
        """Strip the three kwargs this field fixes and record ``vocabulary`` instead.

        ``ForeignKey.deconstruct()`` emits ``to`` and ``on_delete``;
        ``RelatedField.deconstruct()`` emits ``limit_choices_to`` whenever it is
        truthy — which it always is here. Left alone, every generated migration
        would carry a redundant ``to``, a redundant ``on_delete``, and a ``Q``
        literal that duplicates ``vocabulary`` and drifts from it the moment
        either changes. Without this override, ``Field.clone()`` — called by
        ``ModelState.from_model()`` on every ``makemigrations``,
        ``makemigrations --check``, ``migrate`` and pytest-django's own
        test-database build — cannot rebuild the field at all: ``__init__``
        would receive ``on_delete`` (rejected) and no ``vocabulary`` (required).
        """
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop("to", None)
        kwargs.pop("on_delete", None)
        kwargs.pop("limit_choices_to", None)
        kwargs["vocabulary"] = self.vocabulary
        return name, path, args, kwargs


def _normalise_vocabulary(vocabulary):
    """Normalise ``ConceptsField``'s ``vocabulary`` argument to a tuple of slugs.

    One code path for all three shapes (FR-002, ``decisions.md`` D9): a single
    slug becomes a one-element tuple so ``__in`` serves both the one- and
    several-vocabulary cases, a list collapses duplicates with order left
    insignificant, and an omitted (``None``) vocabulary normalises to the
    empty tuple — the field's only real branch, and everywhere it appears the
    answer is to do nothing rather than something weaker.
    """
    if vocabulary is None:
        slugs = ()
    elif isinstance(vocabulary, str):
        slugs = (vocabulary,)
    else:
        slugs = tuple(vocabulary)
    for slug in slugs:
        if not isinstance(slug, str):
            raise TypeError(f"ConceptsField() vocabulary elements must be strings; got {slug!r}.")
    return tuple(dict.fromkeys(slugs))


class ConceptsField(ManyToManyField):
    """A ``ManyToManyField`` to ``controlled_vocabularies.Concept``, optionally
    constrained to one or more named vocabularies.

    ``vocabulary`` is optional (FR-002, ``decisions.md`` D9) and takes three
    shapes, normalised once by :func:`_normalise_vocabulary`: a single slug, a
    list of slugs, or omitted entirely. A declaration naming no vocabulary is
    a supported shape rather than an error — it keeps the delete protection
    T003 builds, the label/URI readback, and the required-set rule, and gives
    up only the restriction.

    ``to`` and ``limit_choices_to`` are not the consumer's to supply: ``to``
    is fixed and ``limit_choices_to`` is derived from ``vocabulary``, set only
    when the declaration named at least one (an empty restriction is not set
    at all, rather than a restriction that matches everything by accident).
    ``through`` is refused outright, for the same reason ``ConceptField``
    refuses ``on_delete`` — a consumer-supplied membership model would
    silently drop the delete guarantee T003 provides.

    ``to`` stays the *string* ``"controlled_vocabularies.Concept"``, never the
    imported class — see :class:`ConceptField`'s docstring for why.
    """

    def __init__(self, vocabulary=None, **kwargs):
        if "limit_choices_to" in kwargs:
            raise TypeError(
                "ConceptsField() sets limit_choices_to itself to constrain choices to "
                "'vocabulary'; a consumer may not override it."
            )
        if "through" in kwargs:
            raise TypeError(
                "ConceptsField() generates its own through model with PROTECT on the "
                "foreign key to Concept; a consumer may not override it."
            )
        self.vocabulary = _normalise_vocabulary(vocabulary)
        kwargs["to"] = "controlled_vocabularies.Concept"
        if self.vocabulary:
            kwargs["limit_choices_to"] = Q(scheme__slug__in=self.vocabulary)
        # A static message, not one interpolating `vocabulary`: `%` on a
        # gettext_lazy() proxy evaluates it immediately, which would defeat
        # the laziness this default exists to keep (translation happens at
        # access time, per request).
        kwargs.setdefault("help_text", _("Concepts from this field's configured vocabulary or vocabularies."))
        super().__init__(**kwargs)

    def deconstruct(self):
        """Strip ``to`` and ``limit_choices_to`` and record ``vocabulary`` instead.

        ``through`` is never emitted here to begin with: T003 marks the
        generated membership model ``auto_created``, and
        ``ManyToManyField.deconstruct()`` only emits ``through`` when it is
        not. Left alone otherwise, ``Field.clone()`` — called on every
        ``makemigrations``, ``makemigrations --check``, ``migrate`` and
        pytest-django test-database build — would receive a ``to`` and
        ``limit_choices_to`` that reconstruct a plain relation, with no
        ``vocabulary`` to rebuild this field's own restriction from.
        """
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop("to", None)
        kwargs.pop("limit_choices_to", None)
        kwargs["vocabulary"] = self.vocabulary
        return name, path, args, kwargs
