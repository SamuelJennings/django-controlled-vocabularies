"""Tests proving the ui templates carry no vocabulary link and no untranslated reader-visible
text (T009, FR-013, decisions.md D1, and the repo's every-string-translated convention).
"""

import re
from pathlib import Path

import pytest
from django.urls import reverse

from tests.factories import ConceptSchemeFactory

TEMPLATES_ROOT = Path(__file__).resolve().parents[2] / "controlled_vocabularies" / "ui" / "templates"
ROW_TEMPLATE_PATH = TEMPLATES_ROOT / "controlled_vocabularies" / "ui" / "conceptscheme_list_item.html"

# Django syntax that is already known-safe and is stripped before the reader-visible-text scan:
# a developer comment, a blocktrans block (translated, content and all), any remaining tag
# (including a `{% trans %}` — its quoted content is translated, so removing tag and content
# together is correct), and a variable interpolation (dynamic — not a literal string this
# template owns the wording of).
_COMMENT_RE = re.compile(r"{%\s*comment\s*%}.*?{%\s*endcomment\s*%}", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_BLOCKTRANS_RE = re.compile(r"{%\s*blocktrans.*?{%\s*endblocktrans\s*%}", re.DOTALL)
_TAG_RE = re.compile(r"{%.*?%}", re.DOTALL)
_VAR_RE = re.compile(r"{{.*?}}", re.DOTALL)
_TEXT_NODE_RE = re.compile(r">([^<{]+)<")
_WORD_RE = re.compile(r"[A-Za-z]{2,}")


def bare_reader_visible_text_nodes(source: str) -> list[str]:
    """Every text-node fragment left after Django's own translation and comment syntax is
    stripped out — a non-empty result names a string the convention (every reader-visible
    string wrapped in a translation tag) failed to wrap. Scoped to text nodes (content
    between tags), not attribute values — this app's own templates put every reader-visible
    string there deliberately, for exactly this reason (T009: attribute-value scanning
    cannot tell a literal string from a structural token like a slot name or a size key
    without a real HTML/template parser, which does not earn its cost at this app's size).
    """
    stripped = _COMMENT_RE.sub("", source)
    stripped = _HTML_COMMENT_RE.sub("", stripped)
    stripped = _BLOCKTRANS_RE.sub("", stripped)
    stripped = _TAG_RE.sub("", stripped)
    stripped = _VAR_RE.sub("", stripped)
    return [node for node in _TEXT_NODE_RE.findall(stripped) if _WORD_RE.search(node)]


class TestRowPartialNeverLinksToTheVocabulary:
    """FR-013, decisions.md D1 — the row partial's own source, so a link cannot creep back in
    without the view changing at all (a second, independent proof from the rendered-page one
    below).
    """

    def test_the_row_partial_source_contains_no_url_tag(self):
        source = ROW_TEMPLATE_PATH.read_text()
        assert "{% url" not in source

    def test_the_row_partial_source_contains_no_local_url_reference(self):
        source = ROW_TEMPLATE_PATH.read_text()
        assert "local_url" not in source


class TestRenderedPageNeverLinksToAVocabulary:
    """FR-013 stated the second way: scanning the page as actually rendered."""

    @pytest.mark.django_db
    def test_no_anchor_on_the_page_points_at_a_vocabularys_own_address(self, client):
        scheme = ConceptSchemeFactory()

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"))
        content = response.content.decode()

        hrefs = re.findall(r'href="([^"]*)"', content)
        assert scheme.local_url not in hrefs


class TestEveryShippedTemplateWrapsReaderVisibleTextInATranslationTag:
    """Every reader-visible string is translatable (repo convention, checked mechanically per T009)."""

    @pytest.mark.parametrize(
        "path",
        sorted(TEMPLATES_ROOT.rglob("*.html")),
        ids=lambda p: str(p.relative_to(TEMPLATES_ROOT)),
    )
    def test_no_bare_reader_visible_text_outside_a_translation_tag(self, path):
        fragments = bare_reader_visible_text_nodes(path.read_text())
        assert fragments == []
