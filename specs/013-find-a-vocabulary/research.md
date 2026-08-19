# Research — 013 Find a vocabulary

What was read, what it establishes, and what it forces the plan to do. Everything here was checked
against source on 2026-08-19, not recalled.

## R1 — The package has no HTML surface today, and this is the first one

`controlled_vocabularies/` ships `urls.py` with exactly one route (the concept search endpoint),
`views.py` with one view behind it, and **no templates at all**. There is no base template, no page
template, no template directory. Everything this feature renders is new ground, which is why the
shape of the app matters more than the page does.

## R2 — The shape is settled: an inner `ui` app, optional dependency, host mounts the routes

The maintainer set the approach when R6 was broken up: django-mvp as the shell, behind an inner
`ui/` app, the way `django-literature` does it. That package is the working reference
(`/home/sam/projects/fairdm/django-literature`), and its pattern is:

- `literature/ui/` is a full Django app — `apps.py` with a **label distinct from its name**,
  `urls.py` with `app_name` and nothing auto-mounted, `views.py`, and templates under
  `literature/ui/templates/literature/ui/`.
- `ui/__init__.py` is a docstring and nothing else. It is imported during the app registry's first
  phase, so any re-export reaching `views.py` touches models and raises `AppRegistryNotReady` at
  `django.setup()`. The package asserts this with a test that parses the file.
- The UI stack is a **packaging extra**, not a runtime dependency. Hard dependencies stay clean;
  `django-mvp` sits in an `ui` extra carrying a `python_version >= "3.12"` marker, because
  django-mvp needs 3.12 and the package keeps a 3.11 floor. The marker makes the extra
  unresolvable on 3.11 rather than an error.
- The core is proved clean three ways: a test that parses every core module and asserts it imports
  none of the UI stack, a test that boots the core in a **fresh subprocess** under core-only
  settings and runs `manage.py check`, and a test that parses `pyproject.toml` and asserts the
  dependency sits in the extra and nowhere else.
- Two settings modules in the test project: a core-only one, and the full one that star-imports it
  and appends the UI stack.
- `deptry` needs `[tool.deptry.package_module_name_map] django-mvp = "mvp"`, or it guesses
  `django_mvp` and reports the import as missing.

**The one gap in the reference, worth closing here:** a project that lists the ui app without
installing the extra gets a raw `ModuleNotFoundError: mvp` the first time the URLs are imported.
Nothing gives it a friendly failure. A system check in the ui app's `AppConfig.ready()` turns that
into a message naming the extra, at `manage.py check` time rather than on the first request.

## R3 — django-mvp supplies the whole page except the row

Read against `django-mvp` at `v0.19.1` (`/home/sam/projects/django-mvp/django-mvp`).

- `MVPListView` composes a search mixin and an ordering mixin over Django's `ListView`.
  `search_fields = ["name", "description"]` gives exactly what FR-006 asks for: it reads `?q=`,
  strips it, splits on whitespace, and applies `icontains` across the declared fields with OR
  semantics. When `search_fields` is `None` the mixin is a no-op. Nothing needs writing for search
  itself.
- `list_item_template` names the partial rendered per object. The page template
  (`list_view.html`) is django-mvp's, and it ships the count line, the grid and the pagination
  control. A consumer supplies the row.
- Empty states are **per request**: `get_empty_state_heading()` and `get_empty_state_message()` are
  methods, so the two distinct messages FR-009 and FR-011 require are an override that branches on
  whether `?q=` was given. No template work.
- **Pagination preserves the query string.** `cotton/pagination/link.html` builds its href with
  `{% querystring page=page %}`, Django's own tag, which rewrites one parameter and keeps the rest.
  `django-literature` carries a strict xfail for the opposite behaviour against an older version;
  at 0.19.1 the tag is in place, so FR-010 holds — and the acceptance scenario that searches from
  the second page is what proves it rather than assumes it.

## R4 — The search box django-mvp ships does not submit on its own

`cotton/page/list/actions/index.html` renders four actions by default — search, sort, filter,
create. This feature wants only the first.

The catch: `actions/search.html` renders an input with `form="filterForm"` and a submit button with
the same attribute, and **the element with `id="filterForm"` is defined inside `actions/filter.html`**.
Rendering the search action without the filter action produces a search box whose `form` attribute
points at nothing, so neither the input nor the button is associated with any form and the search
never submits. Grepped across the whole template tree: `filterForm` appears in the search, sort and
filter components and is created only by the third.

Three ways out, and the plan takes the third:

1. Render the filter action too — puts a filter control on a page the specification says has none.
2. Ship our own search form and skip django-mvp's component — duplicates markup we would rather
   inherit.
3. **Override the page's actions block with a `GET` form of our own wrapping django-mvp's search
   action.** The component's `form="filterForm"` becomes redundant rather than wrong once the input
   sits inside a form, and the component keeps owning the input's name, its placeholder and its
   value readback.

This is an upstream defect, not a local one — a search action that cannot submit without an
unrelated action is worth an issue on django-mvp, filed with the workaround this feature ships.

## R5 — Ordering, counting and what the data can tell us

- **Order (FR-004):** `Lower("name")` for the case-insensitive part, with `pk` last as a
  tiebreaker. Ordering without a total order lets a row appear on two pages or neither once
  pagination is involved — `django-literature` hit exactly that and now names `pk` last on every
  sortable column.
- **Count (FR-002):** `Count("concepts")` as a queryset annotation. `Concept.scheme` declares
  `related_name="concepts"`, so this is one aggregate on the list query and keeps the query count
  flat as the page grows, which is SC-005 stated as a test with `django_assert_num_queries`.
- **Origin (FR-003):** the only signal in the data is `static_uri` — present means the identifier
  was fixed by a publisher. `CONTEXT.md` defines it exactly that way, and `decisions.md` D6 records
  the limit: R4's publishing will also fix an identifier for a locally authored vocabulary, and R4
  is the feature equipped to tell the two apart.
- **No link (FR-013):** `local_url` exists on every scheme and composes an address nothing serves
  yet. The row deliberately does not use it.

## R6 — Test project changes this forces

`tests/settings.py` today installs the admin, `django_tomselect`, the package and a test app.
The UI stack adds `django_cotton`, `easy_icons`, `flex_menu`, `crispy_forms`, `crispy_tailwind`,
`mvp` and the ui app itself, plus django-mvp's context processor and the `EASY_ICONS` / `FLEX_MENUS`
settings (`django-literature`'s `tests/settings.py` is the working list to copy). `tests/urls.py`
mounts the ui routes under a prefix of the test project's choosing, so a hard-coded path in a view
would be caught.

The existing `tests/settings_no_admin.py` is the precedent for the core-only variant: a second
settings module, run out of process, because a Python process builds its app registry once at
startup and proving an app *absent* needs a fresh interpreter.

CI installs no extras today (`poetry-install-args: ''`). It must install this one, or every ui test
fails at import. The matrix runs 3.12 and 3.13 only, so the extra's `>=3.12` marker never bites
there; the package floor stays 3.11 and the extra is simply unavailable at that version.
