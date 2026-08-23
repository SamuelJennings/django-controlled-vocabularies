# Research — 014-look-inside-a-vocabulary

What was read before the plan was written, and what each reading settled. Everything here is a
finding about code that exists, not a proposal.

---

## R1 — django-mvp offers a detail view, and it is deliberately empty

`MVPDetailView` exists (`mvp/views/detail.py:204`) and is `BaseTemplateNameMixin` +
`PageObjectMixin` + Django's `DetailView`. Its template, `detail_view.html`, is twenty-five lines
whose `{% block page.content %}` is literally empty, with a comment saying the body belongs to the
project.

That is a recorded decision upstream, not an unfinished page —
`docs/adr/0001-detail-views-do-not-take-a-field-list.md`: *"The packaged detail page is deliberately
empty below the heading. That is the finished behaviour, not a placeholder awaiting a renderer."*
The rationale given is that a list page is one uniform row repeated while a detail page is layout,
and layout is where an application's design lives.

**Settles:** building this page on `MVPDetailView` buys the heading and nothing else, and costs
search, pagination, both empty states and the paging controls. The page is a list view over
concepts instead (plan Key design decision 1).

## R2 — Nothing in django-mvp supports a detail page with an embedded list

No combined class, no mixin, no template block, no documented pattern. `MultipleObjectMixin` does
not appear anywhere in the package. The closest things are the inline formset views, which are an
editing surface rather than a read list.

The mixins can be composed by hand — `SearchMixin`, `OrderMixin` and `SearchOrderMixin` only touch
`get_queryset()` and `get_context_data()`, and django-mvp's own documentation says they work on any
plain `ListView`. That route was weighed and rejected on Article II grounds; the reasoning is in the
plan, not here.

## R3 — The search control is wired to a form that a page without a filter never renders

`mvp/templates/cotton/page/list/actions/search.html` renders its input and its submit button
carrying `form="filterForm"`, and the only template that ever declares `id="filterForm"` is
`cotton/page/list/actions/filter.html`, which renders only when a django-filter `FilterSet` is in
context. On a plain list view with `search_fields` and no filter, the box renders and submitting it
does nothing.

Reported upstream as **django-mvp/django-mvp#282**, confirmed still open on 2026-08-20. The
unreleased source checkout carries a fix; the installed release 0.19.1 does not.

**Settles:** the search works through the address and not through the box, on this page exactly as
on the list of vocabularies #140 shipped. ADR 0015 governs, the affected tests are skipped citing
#282, and nothing is built around it.

## R4 — The list component cannot be pointed at a second row template

`cotton/page/list/index.html` declares a `card` variable and never reads it; the loop renders
whatever `list_item_template` is in the surrounding context. `list_view.html`'s `:card=` attribute
is decorative.

Two further properties of the same path: `render_list_item` (`mvp/templatetags/mvp.py:255`) renders
each row in an isolated context holding only `object`, `model` and the model name — no `request`, no
`user`, no `csrf_token` — and `?q=`, `?o=` and `?page=` are fixed names with no per-instance prefix.

**Settles:** the concept list uses the component; the collections are rendered with an ordinary
template loop (plan Key design decision 5). A row partial may use `{% url %}` but must not expect
the request.

## R5 — The pagination component preserves the query string

`cotton/pagination/link.html:16` builds each link with Django's `{% querystring page=page %}`, so an
active `?q=` survives paging without anything being done about it.

**Settles:** FR-016's "with any search in force preserved" needs no work beyond using the shipped
component.

## R6 — Prebuilt CSS carries the whole daisyUI component set, and only some plain utilities

django-mvp's stylesheet is generated from three sources: its own templates, the complete daisyUI
component set (deliberately, so a consumer is not limited to the subset upstream happens to use),
and an explicit safelist of plain Tailwind utilities. So daisyUI classes are safe to use, and the
earlier rule of thumb — that any class django-mvp does not itself use is absent — is too strong.

What genuinely is absent: `line-clamp-*`, every `shadow-*` utility, physical-axis spacing such as
`pl-4` and `text-left`, and arbitrary colour opacities beyond the two upstream writes.

**Settles:** the page stays on `c-*` components, daisyUI classes and the safelist. #140's use of the
`truncatewords` filter rather than a CSS clamp remains correct and is reused for a long description.

## R7 — The importer already reads collections, ordered collections, and alternative and hidden labels

`CollectionImporter.import_collections` handles both `skos:Collection` and `skos:OrderedCollection`
(`exchange/skos.py:1588`), and the concept label path covers `skos:prefLabel`, `skos:altLabel` and
`skos:hiddenLabel` (`exchange/skos.py:923`).

**Settles:** the demonstration gains its collections and its alternative and hidden labels by
editing the two seed Turtle files. No Python is written for seed data, and the demonstration keeps
exercising the package's real import path rather than a fixture loaded behind it.

## R8 — A vocabulary's address and the browsing app's mount have never been made to agree

`ConceptScheme.local_url` is `conf.get_base_uri()` + `/` + the slug, and `get_base_uri()` reads
`settings.CONTROLLED_VOCABULARIES_BASE_URI`, defaulting to `http://localhost:8000/vocabularies`. The
`ui` app is mounted by the project at a prefix of its choosing; the demonstration mounts it at
`/browse/`.

Nothing has ever compared the two, and until this feature nothing served a page at that address, so
the disagreement had no symptom.

**Settles:** the plan's second key design decision — the route, a system check that reports the
disagreement, and a demonstration configured so its identifiers actually resolve.

## R9 — Concepts carry no notation, and the search cannot match one

No field on `Concept` holds a notation, no `ConceptNote` kind covers one, and no import path
populates one, though `CONTEXT.md` defines the term.

**Settles:** `decisions.md` D1, and the gap raised at and approved through the specification gate.
