"""``ConceptField`` — attach a concept from a named vocabulary to a model.

A ``ForeignKey`` subclass a consuming project declares on its own model, naming
one vocabulary by its slug. It fixes three things the consumer does not supply
— ``to=Concept``, ``on_delete=PROTECT``, and ``limit_choices_to`` restricted to
that vocabulary — so almost everything FR-002/FR-005/FR-006/FR-007 ask for
falls out of ``limit_choices_to``: it is what ``ForeignKey.validate()`` applies,
and it is a ``Q``, so it is lazy and never queries the database while the
declaration is only being read (FR-003).
"""

from django.core.exceptions import ValidationError
from django.db.models import PROTECT, ForeignKey, Q
from django.utils.translation import gettext_lazy as _

from controlled_vocabularies.models import Concept


class ConceptField(ForeignKey):
    """A ``ForeignKey`` to :class:`~controlled_vocabularies.models.Concept`,
    constrained to one named vocabulary.

    ``vocabulary`` is the owning :class:`~controlled_vocabularies.models.ConceptScheme`'s
    slug — required and non-empty, since an unconstrained field would be a plain
    ``ForeignKey`` and offer none of this field's guarantees (FR-002). ``to``,
    ``on_delete`` and ``limit_choices_to`` are not the consumer's to supply:
    ``on_delete`` is refused outright (FR-007's guarantee is not theirs to
    weaken), while ``to`` and ``limit_choices_to`` are simply overwritten.
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
        self.vocabulary = vocabulary
        kwargs["to"] = Concept
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
        refusal itself is still ``limit_choices_to``.
        """
        try:
            super().validate(value, model_instance)
        except ValidationError as exc:
            if exc.code != "invalid":
                raise
            raise ValidationError(
                self.error_messages["invalid"],
                code="invalid",
                params={"value": value, "vocabulary": self.vocabulary},
            ) from exc
