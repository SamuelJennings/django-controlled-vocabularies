## Research Findings: Search-as-you-type widget for django-controlled-vocabularies

### Candidates evaluated
(a) django-tomselect (b) django-autocomplete-light / DAL (c) vanilla Tom Select + custom view (d) no other credible non-jQuery Django-specific option was found — see note below

---

### Req 1 — Package carries the endpoint; consumer wires one route; widget resolves by name

**django-tomselect**: The endpoint logic lives entirely in the package as `AutocompleteModelView` (`django_tomselect/autocompletes.py`). The package does **not** ship a `urls.py` to `include()` — the consuming project writes one `path("...", MyAutocompleteView.as_view(), name="...")` per view, per the Quick Start. The widget never hardcodes a path: `TomSelectConfig(url="concept_autocomplete", ...)` is a Django URL **name**, resolved via the package's own `safe_reverse()`/`safe_url()` helpers at render time (confirmed in `autocompletes.py` and used identically in `forms.py`/widgets). Since both your FK and M2M fields target the same `Concept` model, **one view + one URL entry serves both fields** — satisfies "ONE route." (Source: `github.com/OmenApps/django-tomselect/blob/main/src/django_tomselect/autocompletes.py`, README Quick Start.)

**DAL**: Same shape — you subclass an `Autocomplete` view (`dal/views.py`), register it yourself in your `urls.py`, and the widget (`dal/widgets.py`) resolves the endpoint by URL name, not a hardcoded path. No package-provided `urls.py` to include either. (Source: `github.com/yourlabs/django-autocomplete-light/blob/master/src/dal/views.py`.)

**Verdict**: Both satisfy the *substance* of Req 1 (server owns the endpoint code, widget resolves by name, one shared Concept view covers both fields) but **neither package literally ships an includable URLconf** — that detail in your spec isn't met literally by either off-the-shelf option. Flagging this as the one place evidence didn't match the requirement's exact wording.

---

### Req 2 — Server-side restriction from the field declaration; are request params trusted? (read from source, not docs)

**django-tomselect** — read `autocompletes.py` end to end:
- `model` is a **class attribute on the view**, fixed by whichever `path()` the request hit. A request cannot change which model is queried, and cannot address another model — the URL routing pins it.
- `value_fields` (what's returned to the browser) is **hardcoded on the view class**; not influenced by any request parameter.
- `search_lookups` (what fields the typed text matches against) is **hardcoded on the view class**. The request supplies the search *string*, never a field name.
- **Nuance you should know**: `filter_by`/`exclude_by` (used for dependent/chained fields, e.g. "narrow Concepts by selected scheme") accept `dependent_field__lookup_field=value` from the URL. By default (`allowed_filter_fields = None`), the only check is that `lookup_field` **structurally exists somewhere on the model** (`_validate_filter_field` walks `model._meta.get_field`) — it does **not** by default restrict to fields the view author intended to expose as filters. Same pattern for `ordering` (`allowed_ordering_fields = None` by default → any request-supplied ordering field that exists on the model is applied, guarded only by try/except `FieldError`). Both allowlists exist (`allowed_filter_fields`, `allowed_ordering_fields`) but are **opt-in, not the default**. Practical effect: a hand-edited request can filter/order by a field on `Concept` that wasn't in your declared `search_lookups`/`value_fields` — it can't leak that field's *value* (responses are still built strictly from `value_fields`), but it can act as a boolean oracle (e.g. "does any Concept with `deprecated=True` match this text") unless you set the allowlists. **Recommendation: explicitly set `allowed_filter_fields` and `allowed_ordering_fields` on any view you write**, even though the library doesn't force you to.
- Permissions (`permission_required`, `allow_anonymous`, `skip_authorization`) are also declared server-side on the view class, checked in `dispatch()`/`has_permission()` before any queryset code runs.
(Source: read directly from `autocompletes.py`, lines covering `setup()`, `_validate_filter_field`, `apply_filters`, `order_queryset`, `has_permission`, `dispatch`.)

**DAL** — read `dal/views.py`:
- `model` and `search_fields`/`model_field_name` are class attributes on the Autocomplete subclass — same "fixed by the view class" model as tomselect.
- There is **no generic filter_by/exclude_by URL mechanism** at all. DAL's "forwarded" dependent-field data (a JSON dict from `request.GET`/`POST`) is handed to you as `self.forwarded`, and it's entirely **up to you to consume it** by overriding `get_queryset()` yourself. That means DAL has no built-in field-allowlist bug to worry about (nothing is auto-applied against arbitrary model fields) — but it also means the filtering safety is 100% on the implementer, with no framework guardrail either way.
- I found **no built-in authentication/permission gate** on the base view for GET requests in this file — `has_add_permission()` exists only for the POST "create new" path. Unlike tomselect, there's no declarative `permission_required`/`allow_anonymous` on the base class; you're expected to mix in `LoginRequiredMixin` or similar yourself if you want gating. This is a real difference: tomselect makes access control opt-out-of-default-open (`skip_authorization=False` unless you say otherwise, and anonymous is *not* allowed by default — you must set `allow_anonymous=True`), whereas DAL's example views are commonly anonymous-accessible unless you add the mixin.
(Source: `github.com/yourlabs/django-autocomplete-light/blob/master/src/dal/views.py`, full file read.)

**Verdict on Req 2**: django-tomselect has the stronger default posture (auth is closed-by-default; model/search fields are fixed) but has one soft spot (filter/order allowlists are opt-in) that you should close explicitly. DAL puts more of the trust boundary in the hands of whoever writes the Autocomplete subclass, both for permissions and filtering — riskier as a default, more flexible if you're careful.

---

### Req 3 — Bounded page, has-more flag, stable paging

**django-tomselect**: `paginate_queryset()` uses Django's `Paginator`, returns `{"results", "page", "has_more", "next_page", "total_pages"}`. Page size is clamped server-side to `MAX_PAGE_SIZE = 200` regardless of what the request asks for (`0 < requested_page_size <= MAX_PAGE_SIZE`, clamped if exceeded) — a deliberate DoS guard per the code comment. Ordering is applied before pagination (`get_queryset()` → `order_queryset()` → `paginate_queryset()`), and falls back to the model's PK if nothing else is set, so paging is stable (no repeats/skips) as long as the ordering field doesn't change between requests. **Met.**

**DAL**: `BaseQuerySetView` extends Django's `BaseListView` with `paginate_by = 10`; `has_more()` returns `page_obj.has_next()`. Standard Django `Paginator` under the hood — same stability guarantee. I did not find a page-size cap in the base view (no MAX_PAGE_SIZE equivalent) — page size looks like a fixed class attribute, not request-adjustable, so this is a non-issue by a different mechanism (no request-controlled page size at all vs. tomselect's clamp). **Met.**

---

### Req 4 — Settable as the DEFAULT widget of a custom model field via `formfield()`

Both packages ship plain Django `forms.Field`/`forms.ModelChoiceField` subclasses (`TomSelectModelChoiceField`/`TomSelectModelMultipleChoiceField` for tomselect; DAL's `dal/fields.py` + `ModelSelect2`/`ModelSelect2Multiple` widgets for DAL) that behave like any normal Django form field/widget. Either can be returned unconditionally from a custom model field's `formfield()` override — this is a completely standard Django pattern for both, not something either package does anything unusual to support or block. **Both fully met; no differentiator here.**

---

### Req 5 — Static assets ship inside the package (no npm step for consumers)

**django-tomselect**: `pyproject.toml` → `[tool.setuptools.package-data]` explicitly bundles `static/**/*.js`, `static/**/*.css`, `static/**/*.map` into the wheel. **Met, verified from the actual build config**, not marketing copy.

**DAL**: `pyproject.toml` sets `include-package-data = true`, and `src/dal_alight/static/dal_alight` and similar directories exist in the repo tree (confirmed via GitHub contents API and referenced in the ruff exclude list for generated/vendored static files). **Met**, though I did not fetch the actual compiled JS to confirm it's not a placeholder — moderate confidence rather than the direct proof I have for tomselect.

---

### Req 6 — No jQuery anywhere in the runtime dependency chain

**django-tomselect**: Built on [Tom Select](https://tom-select.js.org/), which is a vanilla-JS rewrite of Selectize with **no jQuery dependency** by design — this is Tom Select's entire reason for existing. **Met.**

**DAL**: Ships **two** widget backends: `dal_select2` (wraps select2.js, which **requires jQuery** — this is select2's own hard dependency, unrelated to DAL) and `dal_alight` ("native web component", no jQuery). To satisfy your jQuery constraint you'd have to commit to `dal_alight` specifically and avoid `dal_select2` everywhere in the app. **Conditionally met** — jQuery-free only if you consistently choose the non-default/less-historically-used backend.

**What django-select2 would have given up for the record**: it wraps select2.js directly, which has jQuery as a hard runtime dependency (confirmed by select2's own project — it's a jQuery plugin, not a standalone widget). That's the entire reason it's excluded per your constraint; there's no configuration that removes the jQuery requirement from django-select2 itself.

---

### Req 7 — Django ≥5.2 incl. 6.0, Python ≥3.11, license

| | django-tomselect | django-autocomplete-light |
|---|---|---|
| Version | **2026.6.2** (PyPI, uploaded 2026-06-13) | **5.0.0** (PyPI, uploaded 2026-06-18) |
| Django | `django>=4.2.29` dependency; classifiers list 4.2, 5.1, 5.2, 6.0 — so it **spans a wider matrix including 4.2**, and 5.2/6.0 are covered | `django>=5.2` dependency; classifiers list only 5.2, 6.0 — **narrower, but exactly matches** your ≥5.2 floor |
| Python | `>=3.11,<4.0`; classifiers 3.11–3.14 | `>=3.11`; classifiers 3.11–3.14 |
| License | MIT (confirmed via GitHub API `license.spdx_id`) | MIT (confirmed via GitHub API `license.spdx_id`) |

(Source: both packages' `pyproject.toml` read directly from `raw.githubusercontent.com`, and GitHub repo API `license` field.)

Both satisfy the requirement as stated. Tom-select's broader floor (still supporting 4.2) is irrelevant to you either way since your floor is 5.2.

---

### Req 8 — Active maintenance

| | django-tomselect (OmenApps/django-tomselect) | DAL (yourlabs/django-autocomplete-light) |
|---|---|---|
| Last release | 2026.6.2, **2026-06-13** | 5.0.0, **2026-06-18** (v5.1.0rc1 already tagged) |
| Repo created | 2023-07-02 | 2012-05-03 |
| Last push | 2026-06-13 | 2026-06-29 |
| Stars / forks | 87 / 10 | 1,870 / 462 |
| Open issues+PRs | **4** | **212** |
| Release cadence (observed) | Roughly every 1–2 weeks through May–June 2026 (2026.5.1 → 2026.5.2 → …→ 2026.6.2, six releases in six weeks) | Major-version churn: 4.0.1→4.0.3→**5.0.0**(Jun 18)→5.1.0rc1, i.e. mid-2026 is a live rewrite cycle, not a stable trickle |
| Maintainer(s) | Effectively one person (jacklinke / OmenApps org) | Larger org (yourlabs), longer history, much bigger backlog |

(Source: GitHub REST API `repos/.../releases`, `repos/.../{owner}/{repo}` for star/issue/push counts, both fetched directly on 2026-08-13.)

**Read on this**: tomselect is younger, single-maintainer, but has a tight recent cadence and a small, apparently well-triaged issue count (4 open). DAL is older and far more widely used, but 212 open issues against a repo mid-way through a **major backend rewrite** (the jQuery-dependent `dal_select2` being joined/potentially superseded by the jQuery-free `dal_alight` as of the just-shipped 5.0.0) is a signal that the non-jQuery path specifically is the newer, less field-proven part of DAL, not the long-hardened one.

---

### Candidate (c) — Vanilla Tom Select + custom Django view

Tom Select itself is jQuery-free and actively maintained as a JS library. Going this route means you write and own: the URL-conf/view (so Req 1's endpoint-ownership becomes your code, not a dependency's), the field-allowlist/permission logic for Req 2 (you'd have full control but also full responsibility — no borrowed hardening), pagination/has-more contract for Req 3, and you'd vendor Tom Select's built JS/CSS into your package's `static/` to satisfy Req 5. This is viable but is strictly more code and more attack surface to review than adopting a maintained package — django-tomselect already **is** essentially this, pre-built, with the model/permission/pagination contracts worked out and tested by someone else.

### Candidate (d) — other non-jQuery options

I did not find another credible, actively maintained, Django-specific, non-jQuery autocomplete package beyond tomselect and DAL's `dal_alight` backend. (`django-select2` and other select2-wrapping packages are jQuery-bound by construction, per Req 6's constraint.)

---

## Recommendation

**Adopt django-tomselect**, per the maintainer's steer, with one required deviation from its defaults: **explicitly set `allowed_filter_fields` and `allowed_ordering_fields`** on your `ConceptAutocompleteView` rather than relying on the library's default (schema-exists-only) validation, since default behavior lets a hand-edited request filter/order by any field on `Concept`, not just the ones you intended to expose.

**Reasoning**: it satisfies Req 2's authorization model most cleanly of the two real candidates (closed-by-default auth, declared search/value fields with no bypass), ships a genuine DoS-guarded pagination contract (Req 3's `MAX_PAGE_SIZE` clamp is a level of care I didn't find an equivalent for in DAL), bundles its static assets, and is jQuery-free with no caveat (unlike DAL, where you'd have to be disciplined about never touching `dal_select2`). Its release cadence over the last two months is tighter than DAL's, even though its community is smaller.

**Strongest argument against it**: it's maintained by essentially one person, on a repo that's three years old versus DAL's fourteen — if that maintainer stops, you have a much thinner bus factor than adopting the far more widely-used DAL. If long-term multi-maintainer risk matters more to you than the cleaner default security posture, DAL with `dal_alight` pinned as the only backend is the fallback, with the understanding that `dal_alight` is the newer, less-proven half of that project as of its 2026-06-18 major release, and that you would need to hand-roll your own auth gating.

**Requirement with thin evidence — flagging explicitly**: Req 1's literal phrasing ("the package itself carries the search endpoint in its own URL conf") isn't met by either package in the literal sense of an includable `urls.py` — both require you to write the `path()` entry yourself, even though both fully satisfy the underlying intent (server owns the endpoint code; widget resolves by name, not assumption). If that literal packaging detail matters to the spec's author, it's worth a follow-up conversation rather than treating it as satisfied by inference.
