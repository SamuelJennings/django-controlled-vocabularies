# django-controlled-vocabularies

[![Tests](https://github.com/SamuelJennings/django-controlled-vocabularies/actions/workflows/tests.yml/badge.svg)](https://github.com/SamuelJennings/django-controlled-vocabularies/actions/workflows/tests.yml)
[![Build](https://github.com/SamuelJennings/django-controlled-vocabularies/actions/workflows/build.yml/badge.svg)](https://github.com/SamuelJennings/django-controlled-vocabularies/actions/workflows/build.yml)
[![Publish](https://github.com/SamuelJennings/django-controlled-vocabularies/actions/workflows/publish.yml/badge.svg)](https://github.com/SamuelJennings/django-controlled-vocabularies/actions/workflows/publish.yml)
[![PyPI](https://img.shields.io/pypi/v/django-controlled-vocabularies.svg)](https://pypi.org/project/django-controlled-vocabularies/)
[![codecov](https://codecov.io/gh/SamuelJennings/django-controlled-vocabularies/branch/main/graph/badge.svg)](https://codecov.io/gh/SamuelJennings/django-controlled-vocabularies)
[![Python Versions](https://img.shields.io/pypi/pyversions/django-controlled-vocabularies.svg)](https://pypi.org/project/django-controlled-vocabularies/)
[![Django Versions](https://img.shields.io/pypi/djversions/django-controlled-vocabularies.svg)](https://pypi.org/project/django-controlled-vocabularies/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Django app for **managing, publishing, and consuming SKOS controlled vocabularies** — built for
research organisations. Curators create and edit vocabularies through a web interface; developers
attach concepts to their own models and serve standards-compliant RDF at stable URIs. No hand-edited
RDF, no code releases to add a term, no triplestore to operate.

> **Status:** early development (pre-`0.1`). The data model and design are sketched out (see
> [`docs/brainstorm.md`](docs/brainstorm.md)); the first release targets **consumption** (import,
> models, a concept relationship field, and RDF export) ahead of the editing interface. See
> [`GOALS.md`](GOALS.md).

## Scope & philosophy

Research data infrastructure runs on controlled vocabularies, but Django has no native way to manage
or consume them, and the existing editors are foreign stacks, unmaintained, or deployment-heavy.
This app closes that gap by treating a vocabulary as **relational data, not a document**: concepts
are Django models, the database is the source of truth, and RDF is a projection produced only at the
import/export boundary. That turns everything Django already does well (forms, permissions, indexed
search, referential integrity) onto vocabulary management, and lets vocabularies scale to tens of
thousands of concepts and evolve as data rather than code.

**It deliberately is:**

- SKOS-focused.
- A Django app — installable into any Django project (notably FairDM) and runnable standalone.
- Both a **manager** (author, edit, version, publish) and a **consumer** (attach concepts to your
  models via a field; serve RDF at stable URIs).
- Multilingual — a concept holds labels and definitions in any number of languages, with one
  preferred label per language. Each vocabulary picks the language that anchors its concept URIs,
  and a curator can override any concept's slug.
- A graph, not a flat list — concepts link to one another through a broader/narrower hierarchy
  (navigable both ways, and a concept may sit under several broader concepts) and a symmetric
  related association, all within one vocabulary.
- Organisable into collections — a curator can gather a vocabulary's concepts into named
  collections, optionally in a deliberate order, separate from the hierarchy and from any other
  collection a concept belongs to.

**It deliberately is not:**

- A general RDF/OWL toolkit — the SKOS-only scope is intentional.
- A triplestore or SPARQL endpoint — the relational database is the store.
- A replacement for rdflib — rdflib is used only to parse and serialize at the boundary.
- A reasoner — no OWL inference.
- An editor for external vocabularies — imported external vocabularies are read-only references.
- A way to extend a published vocabulary with your own terms — that is out of scope.
- A faithful mirror of imported external vocabularies — imports are normalised to what the app
  supports (e.g. its configured languages); unsupported languages and constructs are not stored.

**Tie-breaks, when principles collide:** the database is the source of truth over RDF fidelity in
memory · lossless round-tripping over schema neatness · stable concept URIs over convenient
identifiers · vocabulary-as-data over vocabulary-as-code · SKOS fidelity over generality.

## Configuration

Every vocabulary, concept, and collection has a URI — its identity, always present. It is static,
held exactly as given and never recomputed by the app, once it is fixed: a record imported from an
external vocabulary keeps the identifier its publisher assigned it. A record authored here instead
has a dynamic URI, composed from a base address, until it is published, at which point that becomes
static too. Set the base address in your Django settings:

```python
CONTROLLED_VOCABULARIES_BASE_URI = "https://vocab.example.org/vocabularies"
```

If you leave it unset, the app falls back to `http://localhost:8000/vocabularies` so it still
runs out of the box — set a real address before you rely on it anywhere it is seen. This site's own
address for viewing a record is always composed from this base and the record's slugs — a concept's
is `{base}/{scheme-slug}/{concept-slug}` — even when that record's static URI points elsewhere, and
the slugs follow the labels while a vocabulary is unpublished.

A record's place in its vocabulary is what keeps its URI distinct, and the database enforces that:
a vocabulary's slug is unique across the site, and a concept's or collection's slug is unique
within its vocabulary. A composed URI therefore cannot collide, because the parts it is built from
cannot. A stored `static_uri` carries its own unique index per model on top of that.

Nothing stops you changing a `static_uri` once it is set. That is deliberate. A published
identifier is not supposed to move, but keeping it still is a matter of not editing it, rather than
of the model refusing every write path. Make the field non-editable wherever you expose it once a
record is published, and treat a value that differs between two imports of the same vocabulary as a
problem with the source file.

An externally assigned static URI must use one of a small set of accepted schemes — `http`,
`https`, `urn`, `doi`, `info`, `ark`, `tag`, `hdl`, and `oai` by default, since those are what real
SKOS vocabularies actually use. If your vocabularies carry identifiers in another scheme, add it
explicitly:

```python
CONTROLLED_VOCABULARIES_ALLOWED_URI_SCHEMES = [
    "http", "https", "urn", "doi", "info", "ark", "tag", "hdl", "oai", "my-custom-scheme",
]
```

A stored identifier is later rendered as a link, so schemes that can carry executable content
(`javascript`, `data`, `vbscript`) are refused even if you add them to this setting.

## Attaching a concept to your model

`ConceptField` is a `ForeignKey` to `Concept`, optionally restricted to the vocabularies you name.
`vocabulary` takes three shapes:

```python
from django.db import models

from controlled_vocabularies.fields import ConceptField


class Specimen(models.Model):
    name = models.CharField(max_length=200)
    rock_type = ConceptField(vocabulary="rock-type")                     # one vocabulary
    dominant_material = ConceptField(vocabulary=["igneous", "mineral"])  # several
    keyword = ConceptField(null=True, blank=True)                        # no vocabulary named
```

`vocabulary` names the owning `ConceptScheme` by its slug rather than by a database relation. A
field declaration is read when Python imports the module, and a vocabulary is rows in a table that
may not exist yet, so the slug is all the field can carry.

`vocabulary="rock-type"` restricts to one vocabulary. A list restricts to the union of the named
vocabularies, and the refusal names every vocabulary the field accepts. Leaving `vocabulary` out
entirely restricts nothing: any concept in the database is a valid choice. That last shape is for a
field drawing on whatever a project has imported rather than one fixed list.

When the field names at least one vocabulary, only a concept whose `scheme.slug` matches is offered
as a form choice or accepted by `full_clean()`. A concept from any other vocabulary is refused.
Deleting a concept a record still references is refused whichever shape you declare
(`on_delete=PROTECT`), whether the delete reaches it directly or cascades down from its scheme.

Reading a concept back:

```python
specimen.rock_type              # the attached Concept, or None
specimen.get_rock_type_label()  # its preferred label in the active language, falling
                                # back to the vocabulary's default language
specimen.get_rock_type_uri()    # its URI
```

If `"rock-type"` has not been imported yet, which is the state of a fresh install before the
vocabulary's own import step has run, nothing about the field declaration fails. `manage.py check`
reports a warning (`controlled_vocabularies.W001`) naming the model, the field, and the missing
slug. If the vocabulary genuinely arrives in a later deployment step, silence the warning with
`SILENCED_SYSTEM_CHECKS`.

Reading `get_<field>_label()` on every row of a list costs a query for the concept and one for its
scheme, plus one for its labels when the active language is not the vocabulary's default, per row.
`select_related("rock_type__scheme")` and `prefetch_related("rock_type__labels")` collapse that
back to a fixed number of queries for the whole list.

## Attaching several concepts to your model

`ConceptsField` is the many-to-many counterpart: several concepts on one record instead of one.
`vocabulary` takes the same three shapes it takes on `ConceptField`, and means the same thing by
each:

```python
from django.db import models

from controlled_vocabularies.fields import ConceptsField


class Sample(models.Model):
    name = models.CharField(max_length=200)
    rock_types = ConceptsField(vocabulary=["igneous", "sedimentary"])  # several vocabularies
    keywords = ConceptsField(blank=True)  # no vocabulary named
```

One slug restricts to that vocabulary, a list restricts to the union of the named vocabularies, and
leaving `vocabulary` out — as `keywords` does above — restricts nothing. A concept outside the
named vocabularies is refused, and the refusal names every vocabulary the field accepts.

Reading concepts back:

```python
sample.rock_types                    # the many-to-many manager
sample.get_rock_types_labels()       # a list of preferred labels, active language with fallback
sample.get_rock_types_uris()         # a list of URIs, same order
```

Both accessors return an empty list for a record holding nothing, including one that has not been
saved yet, rather than raising.

**Required and optional.** `blank=True`, as on `keywords` above, makes the field optional: a record
can hold zero concepts. Without it, as on `rock_types`, the field is required, and required means at
least one concept attached. Django gives a many-to-many field no hook into ordinary field
validation, so this is enforced when `full_clean()` runs rather than by the database — a
`ModelForm` or an explicit `full_clean()` call catches an empty required field, a plain `.save()`
does not. A record cannot hold any concepts before it has a primary key, so the check is skipped on
an unsaved instance. If your own model overrides `full_clean()` after declaring the field, your
override shadows this check, and you'll need to call it yourself or reproduce it.

**Query cost.** `get_<field>_labels()` and `get_<field>_uris()` issue a query for the field's
concepts, and a further query per concept for its scheme and its labels — the same per-concept cost
`ConceptField`'s singular accessors carry, multiplied by however many concepts a record holds. Over
a list of records that's at least one query per record. `prefetch_related("rock_types__scheme",
"rock_types__labels")` collapses that back to a fixed number of queries for the whole list.

**What every shape guarantees, and what the unrestricted one gives up.** Naming one vocabulary,
several, or none all give a record the same three things: a concept it already holds cannot be
deleted out from under it, its attached concepts read back by label and by URI, and required still
means at least one. Naming one or several vocabularies adds a fourth guarantee on top — a concept
outside those vocabularies is refused, both by a form built from the model and by the relation
itself, in either direction, at the moment the membership is written.

A field naming no vocabulary gives up only that fourth guarantee, and nothing else. Said plainly, so
it needn't be inferred:

- It places **no restriction** on which concepts a record can hold — any concept in the database is
  accepted.
- A form built from the model offers **every concept in the database** as a choice, not a filtered
  subset. On an installation with several vocabularies imported, that can be a genuinely long list
  of choices in an ordinary select widget — sooner than a restricted field would ever reach.
- `manage.py check` has no named vocabulary that could be missing, so it reports **nothing** for
  this field.

It still deletes-protects, reads back, and enforces "required" exactly as a restricted field does.

**The delete guarantee's real boundary.** "Cannot be deleted out from under it" holds for anything
that goes through the Django ORM — a single instance, and a bulk queryset `.delete()` alike, since
Django applies `on_delete=PROTECT` to both the same way. It does not hold for a `DELETE` issued
directly against the database outside Django — raw SQL, a database console, a migration that drops
rows without going through the ORM — because Django never writes an `ON DELETE` clause into the
schema for any relation. The protection lives in application code, not in a database constraint.

## Choosing a concept by typing

`ConceptField` and `ConceptsField` render as a search-as-you-type control by default. A project
declaring either gets it without naming a widget, writing an endpoint, or configuring anything
per field — an ordinary `ModelForm` built from the model already renders it.

Getting it working outside the admin takes three steps, done once per project rather than once
per field. In the order a developer does them:

1. **Include the route.** The package carries its own search endpoint in
   `controlled_vocabularies.urls`; include it once, at an address of your choosing:

   ```python
   from django.urls import include, path

   urlpatterns = [
       ...
       path("vocab/", include("controlled_vocabularies.urls")),
   ]
   ```

2. **Add `"django_tomselect"` to `INSTALLED_APPS`.** The control's templates and static assets
   live inside that package, and Django only finds another package's templates and static files
   through an installed app — no amount of work in this package moves that.

3. **Add `"django_tomselect.middleware.TomSelectMiddleware"` to `MIDDLEWARE`.** Without it, the
   control still renders, but as a plain `<select>` carrying no search box and no JavaScript at
   all — nothing errors, nothing warns at render time, and the control simply doesn't work.

Skip any of the three and `manage.py check` reports it: a missing route
(`controlled_vocabularies.W002`), a missing `INSTALLED_APPS` entry (`controlled_vocabularies.W003`),
or a missing middleware entry (`controlled_vocabularies.W004`), each naming exactly what to add.
A render that reaches the missing-route case despite the warning raises `ImproperlyConfigured`
naming both the route and the `INSTALLED_APPS` entry, rather than the underlying library's own
`NoReverseMatch` against a URL pattern you never wrote.

A search returns, per concept, its identifier, its preferred label in the active language, and the
name of the vocabulary it belongs to — nothing else, no editorial notes or alternative labels. The
results are restricted to whatever vocabularies the field declares, the same restriction that
already governs which concepts a form accepts; a field naming no vocabulary searches every concept
in the database. The endpoint carries **no permission rule by default** — it serves the same
concept data the rest of this package publishes at stable URIs. A project holding vocabularies it
does not want searched restricts the include instead, at whatever access level fits.

The control needs a browser running JavaScript. Without it, both fields still work as an ordinary
required-relation form field; only the search-as-you-type behaviour is unavailable.

## Choosing a concept in the admin

A model that declares `ConceptField` or `ConceptsField` gets the same search-as-you-type control on
its Django admin pages once it's registered — nothing further to configure. `ModelAdmin` builds the
field the same way it builds any other, and the wiring is the three steps above: the route,
`django_tomselect` in `INSTALLED_APPS`, and its middleware. The admin adds nothing to that list.

A concept is chosen on these pages, never created or edited there. Django ordinarily puts an
add, change, delete or view link beside a related field so a person filling in a form can manage
the related record without leaving it. None of the four appears beside a concept field, whether or
not this package's own models are registered in the admin, and whatever permissions the signed-in
person holds. Authoring stays wherever concepts themselves are curated — a controlled vocabulary
stops being controlled the moment a data-entry form can invent or edit one.

Where the admin presents the field read-only — listed in `readonly_fields`, or because the
signed-in person may view the page but not change it — the concept is shown by its preferred label
and no control renders. This is Django's own read-only presentation, not this package's: with
`Concept` registered, a single concept links to its own change page. Several concepts, on a
`ConceptsField`, always render as plain text. The package neither adds to this nor suppresses it.

A project can still ask for a different control the way it would for any other related field:

- `autocomplete_fields` renders Django's own autocomplete widget instead — Django requires the
  related model to be registered and searchable, as it does for any field named this way.
- `raw_id_fields` renders Django's plain identifier input, with the magnifying-glass lookup link
  Django gives every field named this way. That link opens a list to pick from — it selects a
  concept, it does not create one.
- A `ModelForm` declaring its own widget for the field via `Meta.widgets`, passed to
  `ModelAdmin.form`, renders that widget.
- `readonly_fields` renders the read-only presentation described above.

The first three still refuse the add, change, delete and view affordances, the same as the default
control, and saving and validation carry on unchanged: a concept outside the field's named
vocabularies is refused, and a legitimate one still saves.

One piece of text on these pages is Django's rather than this package's. Under a multi-value field
the admin adds *Hold down "Control", or "Command" on a Mac, to select more than one.* It is the
same sentence the admin puts under any multiple-select field, and it does not describe this
control: concepts are added by typing and picking, and removed one at a time.

## Finding a vocabulary

The `ui` extra adds one reader-facing page: every vocabulary the site holds, in alphabetical
order, each entry showing its description, how many concepts it holds, and whether it was
authored here or imported from a publisher — with the publisher's own identifier shown for an
imported one. A site holding no vocabularies says so rather than showing an empty list.

A search box narrows that list by a vocabulary's name and description — not by the concepts it
holds; finding a concept without already knowing which vocabulary holds it is not something this
page does. The term travels in the page's address (`?q=`), so a narrowed list can be linked to or
bookmarked and returned to. A second word **widens** the results rather than narrowing them:
matching is OR across every word and both fields, not AND, which is the opposite of what a search
box usually implies. There is no other way to filter or sort the list. A search matching nothing
says so, repeats what was searched for, and offers a link back to the unsearched list.

Case is ignored, with one limit that belongs to the database rather than to this package. SQLite
folds case for ASCII letters only, so a vocabulary named *Ökologie* is found by *ÖKOLOGIE* and not
by *ökologie*. PostgreSQL folds the whole of Unicode and matches either way. Django
[documents this](https://docs.djangoproject.com/en/stable/ref/databases/#substring-matching-and-case-sensitivity)
and does not work around it, and neither does this package, because nothing above the database can.
It matters for any site whose vocabularies are named in German, French, Greek or Russian.

The page carries **no permission rule of its own**. Every vocabulary in the database is listed to
anyone who reaches the URL, exactly as the concept search endpoint above serves anyone who reaches
it, and for the same reason: a package cannot guess a project's access policy. A vocabulary has no
draft state, so one still being authored is listed from the moment it exists. A site that needs the
page restricted wraps the include where it mounts these routes.

```bash
pip install django-controlled-vocabularies[ui]
```

This section adds to the package's base configuration rather than replacing it: `django_tomselect`
and its middleware are still required, as ["Choosing a concept by typing"](#choosing-a-concept-by-typing)
describes, and `manage.py check` says so on startup if they are missing.

Add the ui app and django-mvp's own stack to `INSTALLED_APPS` — quoted from this package's own
test project, so the list below is one that demonstrably works:

```python
INSTALLED_APPS = [
    ...
    "controlled_vocabularies",
    "django_cotton",
    "easy_icons",
    "flex_menu",
    # "mvp" before "crispy_tailwind": django-mvp ships an override of crispy-tailwind's
    # help-text template, and the first app to declare a template path wins.
    "mvp",
    "crispy_forms",
    "crispy_tailwind",
    "controlled_vocabularies.ui",
]

# crispy-forms 2.7's get_template_pack() has no default, and the {% crispy %} tag validates
# the pack against CRISPY_ALLOWED_TEMPLATE_PACKS at template-compile time — django-mvp's own
# templates carry the tag, so both settings are required even though this page renders no
# form of its own.
CRISPY_TEMPLATE_PACK = "tailwind"
CRISPY_ALLOWED_TEMPLATE_PACKS = ["tailwind"]

TEMPLATES[0]["OPTIONS"]["context_processors"] += ["mvp.context_processors.mvp_config"]

# django-mvp's base template renders icons through django-easy-icons and its own sidebar and
# mobile-dock chrome through django-flex-menus; both raise at render time without these.
EASY_ICONS = {
    "default": {
        "renderer": "easy_icons.renderers.ProviderRenderer",
        "config": {"tag": "i"},
        "packs": ["mvp.utils.BS5_ICONS"],
    },
}
FLEX_MENUS = {
    "renderers": {
        "sidebar": "mvp.renderers.SidebarRenderer",
        "dock": "mvp.renderers.MobileFooterNavRenderer",
    },
}
```

Mount the routes at an address of your choosing:

```python
from django.urls import include, path

urlpatterns = [
    ...
    path("browse/", include("controlled_vocabularies.ui.urls")),
]
```

Reverse the page by name, under its own namespace — `controlled_vocabularies_ui`, distinct from
the core package's own `controlled_vocabularies` namespace, so both can be mounted in one
project without either shadowing the other's reverses:

```python
reverse("controlled_vocabularies_ui:vocabulary-list")
```

`manage.py check` reports `controlled_vocabularies.ui.E001`, naming the extra to install, if
`django-mvp` is not importable.

**An entry names a vocabulary — it does not yet link to it.** Every vocabulary already has an
address on this site (`ConceptScheme.local_url`), but nothing serves that address yet. Shipping
a list whose every entry led to a missing page would ship a broken front door rather than a
working one; a later feature turns the name into a link in the same change that gives it
somewhere to lead.

**One thing does not work yet.** The search box on the page cannot be submitted: the control comes
from django-mvp, and in the released version its input is tied to a form that only its filter
control creates ([django-mvp#282](https://github.com/django-mvp/django-mvp/issues/282)). Searching
by address works exactly as documented — `?q=soil` narrows the list, and the narrowed address can be
shared and bookmarked — but typing in the box and pressing the button does nothing until that fix
ships. The same fault is why a page whose search matched nothing names the term but offers no link
back to the full list.

We are waiting on the fix rather than shipping a copy of django-mvp's page with the gap patched: an
override in a package like this one outlives the release that makes it unnecessary, and nothing ever
reports that it has (`docs/adr/0015-upstream-defects-are-waited-on-not-worked-around.md`).

The page is served by `VocabularyListView`, in `controlled_vocabularies.ui.views`. A project that
wants a different presentation subclasses it and routes its own path at the same view — the
queryset, its ordering and its concept count come with the class, so an override that only changes
`list_item_template` keeps every guarantee above:

```python
from controlled_vocabularies.ui.views import VocabularyListView


class BrandedVocabularyListView(VocabularyListView):
    list_item_template = "myproject/vocabulary_card.html"
```

### Try it: the demo project

The repository carries a runnable demo of the page above, wired the same way this section
documents. From a fresh clone, with dependencies installed:

```bash
poetry install --extras ui

poetry run python manage.py migrate
poetry run python manage.py seed_demo
poetry run python manage.py runserver
```

The three commands run through `poetry run` so they use the environment the install just built,
whatever `python` on the shell's path happens to be — on many systems there is no `python` there
at all.

`migrate` builds the database, `seed_demo` loads two small vocabularies into it, and `runserver`
serves the site at `http://127.0.0.1:8000/`, which redirects straight to the populated,
searchable vocabulary list at `http://127.0.0.1:8000/browse/`. The seeded content shows both
kinds of entry the list distinguishes: the DCMI Type Vocabulary, a real vocabulary published by
the Dublin Core Metadata Initiative, imported from a SKOS file; and Data Collection Methods, a
short vocabulary authored here, with no publisher of its own.

`seed_demo` is destructive and idempotent: it clears every vocabulary before loading, so running
it again returns the demo to the same seeded state whatever was added or removed before —
including anything entered through the admin.

To add a vocabulary by hand and watch it appear on the list, give yourself an account first and
sign in at `http://127.0.0.1:8000/admin/`:

```bash
poetry run python manage.py createsuperuser
```

The admin form there belongs to the demo project, not to the package: `demo/admin.py` registers
the vocabulary model with its own admin site. The package registers nothing, so installing it
adds no admin of its own — a project decides for itself which of its models it curates that way.

The demo is not a production configuration: `DEBUG` is on, the database is a local SQLite file,
and the secret key is a throwaway value committed in `demo/settings.py`. Do not deploy it as-is.

## Importing a published vocabulary

`import_skos()` reads a SKOS file — Turtle, RDF/XML, or JSON-LD — and creates or updates the
vocabulary it declares, along with every concept it contains: identity, labels, documentary notes,
broader/narrower and related relationships, and collection membership. Every record is matched by
its static URI, never by name, so importing the same file twice updates the same rows rather than
duplicating them.

```python
from controlled_vocabularies.exchange import import_skos

report = import_skos("rocks.ttl")
```

The caller may name a target `ConceptScheme` for a file that declares no vocabulary of its own, or
have it checked against one the file does declare:

```python
report = import_skos("rocks.ttl", scheme=my_scheme)
```

Re-running an import upserts rather than deleting and recreating. For a record the file still
contains, the file is authoritative for that record's own content — labels, notes, relationships,
and collection membership end up matching the file exactly, including the removal of a value the
file no longer carries. A record the file does not mention at all is left completely untouched and
named in the report instead, never deleted.

Labels and notes are matched by language, not only by predicate. A file's `en` value fills a site
configured for `en-gb`, and a file's `en-gb` value fills a site configured for `en`. Matching runs
on the base language, the first subtag of the tag, case-insensitively and in both directions, and
an exact tag match always wins over a variant.

Where a file offers several variants of one configured language, what happens next depends on how
many values that kind of label or note can hold:

- A preferred label holds one per language, so the variant the vocabulary predominantly publishes
  in is the one kept, with ties broken by language code. Each variant that lost is named in the
  report under its own published language.
- Alternative labels, hidden labels, and notes have no such limit, so every variant the file offers
  is stored.

A value stored under a variant match is named in the report as a substitution rather than applied
silently. That matters most where two variants differ by script. A site configured for `zh-Hans`
importing a vocabulary published only as `zh-Hant` receives that content, in a script its readers
may not be able to read. The report is what makes that visible, so a curator can decide what to do
about it.

The package stores content for every language code in `settings.LANGUAGES`. A project that declares
none inherits Django's own default list of 99 languages, so a vocabulary published in sixty
languages imports into all sixty. Narrowing `LANGUAGES` is how a site limits what an import stores.

A vocabulary's slug and a concept's slug are both derived from their own published identifier —
its fragment where it has one, otherwise the last segment of its path — assigned once, on first
import, and never recomputed by a later one. Renaming a record, or a vocabulary's name arriving in
a different language on a later import, never moves that record's local address; only the
publisher reassigning the identifier itself does. A record authored on this site rather than
imported has no published identifier to derive from, and keeps deriving its slug from its label,
as it always has.

That permanence has a cost worth naming: a vocabulary published under opaque codes gets an opaque
local address — `/v-113/00123` rather than `/soil-types/clay`. It is accepted because the address
is correct and stays correct, which is what every consumer of a URL needs from it, and because a
readable address that can move under data already pointing at it is worse than a stable one that
cannot.

The call returns an `ImportReport`, a plain dataclass rather than rendered text, so a caller can
inspect what happened without parsing anything:

- `created` / `updated` — the URIs of every vocabulary, concept, and collection the run wrote.
- `set_aside` — a `SetAsideEntry` per value the run could not store, each carrying a closed,
  translatable reason (an unconfigured language, a notation, a mapping to another vocabulary, a
  predicate the models have no place for, a missing relationship or collection member, and so on)
  and the data needed to render a message about it. Nothing a file contains is ever dropped in
  silence — a value the app cannot store is always named here.

  Published files are often not well-behaved, and the reasons cover that too. Where a pair of
  concepts is stated as both broader and related, the hierarchical statement wins, because SKOS
  declares the two disjoint, and the related one is set aside. A second preferred label in one
  language is set aside rather than refused at the database. An identifier whose own segment
  yields no usable slug is set aside naming the slug as the problem, not the identifier. None of
  these stops the rest of the vocabulary from importing.
- `absent_from_source` — the URIs of records that exist here but that the file no longer mentions.
- `normalized` — a `NormalizedEntry` per value the run stored, but under a different predicate than
  the one the file asserted (a foreign `dcterms:description` read as a concept's definition, for
  example).
- `fatal` — populated only on a failed run: a `FatalFinding` per reason the whole import was
  refused (a missing or blank-node identity, or a vocabulary that could not be resolved). A failed
  run raises `SkosImportFailed`, carrying this same report, and leaves the database exactly as it
  was before the run started.

A run either succeeds in full or changes nothing: every problem in a file is collected before any
of it is written, and a fatal one rolls the whole run back. The `import_skos` management command
wraps this for use from a terminal (see below). There is no web-facing entry point yet.

Reading a file never reassigns identity. A concept or collection whose URI is already held by a
different vocabulary stays where it is. So does one whose URI is held by a record of another kind,
such as a collection in one file and a concept in another. Both are set aside and reported. Moving
a record between vocabularies is a curatorial decision, not a side effect of reading a file.

An imported file is treated as untrusted input. RDF/XML is scanned for entity expansion and
external references before a parser sees it. A JSON-LD document is refused rather than fetched if
its `@context` names a remote location, whether that is a plain string reference or an `@import`
reference tucked inside an inline object context. `import_skos()` itself never makes a network
request when reading a file — the command's own URL fetch (see below) happens first, and only the
fetched or local bytes ever reach this scan. An ordinary inline JSON-LD context, carrying no such
reference, imports normally.

`import_skos()` raises one of two exceptions, both `ValidationError` subclasses carrying a
translatable message. `SkosImportError` covers every reason a file cannot be turned into usable SKOS
at all: not found, not in a supported serialization, unparseable, or refused by the safety scan
above. `SkosImportFailed` covers the case where the file parses but the run collects one or more
fatal problems (a missing or blank-node identity, or a vocabulary that cannot be resolved), and
carries the same `ImportReport` its `fatal` bucket names them in. `UnsafeRdfXmlError` and
`UnsafeJsonLdError`, the two exceptions the safety scan itself raises, are exported
`SkosImportError` subclasses, so code that only catches `(SkosImportError, SkosImportFailed)`
already catches a file the safety scan refuses too.

## Importing from the command line

The `import_skos` management command wraps `import_skos()` for use from a terminal or a
deployment script:

```bash
python manage.py import_skos rocks.ttl
```

The source can be a local filesystem path or an `http://`/`https://` URL, told apart by the value
itself rather than by a flag. A URL is fetched under a fixed 30-second read timeout, a fixed 50 MiB
response ceiling and a fixed ten-minute deadline for the whole transfer, over a connection that
only ever speaks http and https. The fetched document's identifiers resolve against the address it
was served from, following any redirect — so a vocabulary published behind a PURL or a `/latest`
alias is stored under the URIs its publisher assigned, and a re-import updates the same concepts
the first import created rather than making a second copy.

- `--format` names the source's serialization (`turtle`, `xml`, or `json-ld`), for a source whose
  extension or `Content-Type` does not.
- `--dry-run` performs the entire import and reports the outcome exactly as a live run would,
  then leaves the database exactly as it was beforehand — useful for seeing what a file would set
  aside before deciding whether to configure a language for it.
- `--verbosity`, Django's own option, prints bucket counts by default — how many records were
  created, updated, set aside, normalized, or absent from the source, plus the set-aside account
  grouped by reason and by language. At `2` or above, every individual set-aside entry prints too.
  At `0` nothing prints at all, as with any Django command.

A refusal exits non-zero and prints every reason the run was refused. A run that sets values aside
still exits zero: importing a vocabulary published in more languages than a site is configured for
always sets some aside, so that outcome is treated as normal rather than as a failure a deployment
script should stop on.

## Relationship to other packages

Supersedes and retires `skos-builder` and `django-research-vocabs`, consolidating vocabulary
authoring, management, and Django consumption into one app.

## License

MIT — see [LICENSE](LICENSE).
