"""``controlled_vocabularies.management.sources`` — classifying and, for a URL, fetching a
management-command source (T007-T009, plan.md "Source resolution", research.md R3/R4).

The ``http_stub`` and ``hanging_socket`` fixtures (``tests/conftest.py``, T006, research.md R8)
are proven here first, before :class:`SourceResolver` exists to exercise them — no real network
call is made anywhere in this file.
"""

from __future__ import annotations

import urllib.error
import urllib.request

import pytest


class TestHTTPStubFixture:
    """T006 — the stub itself, exercised directly rather than tested in isolation."""

    def test_the_stub_serves_a_configured_status_body_and_content_type(self, http_stub):
        http_stub.set_response(
            "/vocab.ttl", status=200, body=b"@prefix skos: <http://example.org/> .", content_type="text/turtle"
        )
        with urllib.request.urlopen(http_stub.url + "/vocab.ttl") as response:  # noqa: S310 -- stub is localhost-only
            assert response.status == 200
            assert response.read() == b"@prefix skos: <http://example.org/> ."
            assert response.headers.get_content_type() == "text/turtle"

    def test_the_stub_serves_a_non_2xx_status(self, http_stub):
        http_stub.set_response("/missing.ttl", status=404, body=b"not found")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(http_stub.url + "/missing.ttl")  # noqa: S310 -- stub is localhost-only
        assert exc_info.value.code == 404

    def test_an_unconfigured_path_answers_404(self, http_stub):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(http_stub.url + "/never-configured.ttl")  # noqa: S310 -- stub is localhost-only
        assert exc_info.value.code == 404

    def test_each_test_gets_a_fresh_server_on_its_own_port(self, http_stub):
        # A prior test's server is torn down (conftest's try/finally around
        # serve_forever) rather than left bound, so a second http_stub fixture
        # is free to claim a fresh ephemeral port without colliding.
        http_stub.set_response("/vocab.ttl", status=200, body=b"ok")
        with urllib.request.urlopen(http_stub.url + "/vocab.ttl") as response:  # noqa: S310 -- stub is localhost-only
            assert response.read() == b"ok"
