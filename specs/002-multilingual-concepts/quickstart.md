# Quickstart — Multilingual names and descriptions

Runnable validation scenarios that mirror the spec's acceptance criteria. Each is a few ORM lines a
test (or a developer at a shell) can run. Assumes `settings.LANGUAGES` includes at least `en` and
`de` and `LANGUAGE_CODE = "en"`.

## 1 — Preferred labels per language, identity preserved (US-1)

```python
scheme = ConceptScheme.objects.create(name="Geothermics")          # default language = app default (en)
c = Concept.objects.create(scheme=scheme, label="Heat flow")        # en preferred = the anchor
c.add_label("de", "preferred", "Wärmefluss")

assert c.preferred_label("en") == "Heat flow"
assert c.preferred_label("de") == "Wärmefluss"
assert c.slug == "heat-flow"                                        # from the default-language label

uri_before = c.uri
c.add_label("de", "preferred", "Terrestrischer Wärmefluss")         # would be a 2nd de preferred → ...
# ↑ raises ValidationError (one preferred per language)
# editing the de label instead leaves identity untouched:
assert c.uri == uri_before
```

## 2 — Alternative and hidden labels (US-2)

```python
c.add_label("en", "alternative", "terrestrial heat flow")
c.add_label("en", "alternative", "geothermal heat flow")
c.add_label("de", "alternative", "geothermischer Wärmefluss")
c.add_label("en", "hidden", "heatflow")                            # common misspelling

assert set(c.alt_labels("en")) == {"terrestrial heat flow", "geothermal heat flow"}
assert c.alt_labels("de") == ["geothermischer Wärmefluss"]
assert c.hidden_labels("en") == ["heatflow"]
assert c.uri == uri_before                                          # labels never move identity
```

## 3 — Definitions and documentary notes (US-3)

```python
c.add_note("en", "definition", "The rate of heat transfer through the Earth's surface.")
c.add_note("de", "definition", "Die Wärmestromdichte durch die Erdoberfläche.")
c.add_note("en", "scope", "Use for terrestrial contexts only.")
c.add_note("en", "example", "Continental heat flow averages ~65 mW/m².")

assert c.definition("en").startswith("The rate")
assert c.definition("de").startswith("Die")
assert c.notes("en", kind="scope") == ["Use for terrestrial contexts only."]
assert c.uri == uri_before
```

## 4 — Per-vocabulary default language (US-4)

```python
de_scheme = ConceptScheme.objects.create(name="Geothermik", default_language="de")
assert de_scheme.effective_default_language == "de"

k = Concept.objects.create(scheme=de_scheme, label="Wärmefluss")   # label is the de preferred
k.add_label("en", "preferred", "Heat flow")
assert k.slug == "warmefluss"                                      # slug anchored in de, not en
```

## 5 — Overridable slug (US-5)

```python
c2 = Concept.objects.create(scheme=scheme, label="Thermal conductivity", slug="k-value")
assert c2.slug == "k-value"                                        # explicit, not derived
c2.label = "Heat conductivity"; c2.save()
assert c2.slug == "k-value"                                        # pinned; relabel does not move it

c3 = Concept.objects.create(scheme=scheme, label="Geothermal gradient")
assert c3.slug == "geothermal-gradient"                            # auto, tracks label (as #15)
```

## 6 — Multilingual factory (US-6)

```python
c = ConceptFactory(multilingual=True)                              # trait populates en+de labels & notes
assert c.preferred_label("en") and c.preferred_label("de")
assert c.notes("en")
```

## 7 — Standards (US-7)

```python
# tests/test_standards.py walks every concrete field on all four models and asserts
# translatable verbose_name + non-empty help_text; new validation messages are lazy Promises with
# named placeholders; ConceptLabel(language, kind, text) is indexed; ConceptNote.value is a
# recorded unindexed decision.
```
