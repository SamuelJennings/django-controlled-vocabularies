"""The guard's assertion script (T017, FR-017, User Story 3 scenario 5).

Speaks real HTTP against a running demo server. It knows one address — the vocabulary list —
because that is the only page this feature ships (FR-013: no entry links anywhere else yet). It
asserts on the served response, never on the code that produced it, because the failure it
exists to catch is the one every unit test passes through: a template that renders in a test
client and not in a browser.

The assertions themselves (:func:`check_list`, :func:`check_search`) are separated from the HTTP
transport (:func:`get`) so they can be exercised against an in-process response too
(``tests/test_demo/test_smoke.py``) — "a broken assertion fails here rather than only in CI".

Not a test module: standard library only, run directly against a live server, not under pytest
(conventions; constitution Article VII).
"""

import sys
import urllib.error
import urllib.request

# The demo runs with DEBUG = True: an unbounded body on failure would put Django's technical-500
# page, including settings and the request environment, into a public CI log.
BODY_EXCERPT_LIMIT = 500

#: The demo's two seeded vocabularies and how many concepts each carries (demo/seed/*.ttl,
#: demo/management/commands/seed_demo.py) — named here once rather than re-derived, since the
#: walk's whole job is to notice when the served page stops agreeing with them.
IMPORTED_NAME = "DCMI Type Vocabulary"
IMPORTED_CONCEPT_COUNT = 5
AUTHORED_NAME = "Data Collection Methods"
AUTHORED_CONCEPT_COUNT = 4

#: A word that appears in the imported vocabulary's own name and nowhere in the authored one's
#: name or description — narrow enough that a search for it proves the search narrowed rather
#: than merely returned something.
SEARCH_TERM = "DCMI"


class SmokeCheckFailed(Exception):
    """The URL, status and a bounded body excerpt of a failed check (FR-017)."""


def fail(url, status, reason, body=""):
    raise SmokeCheckFailed(f"{url} [{status}]: {reason}\n{body[:BODY_EXCERPT_LIMIT]}")


def check_list(list_url, status, body):
    """Both seeded vocabularies are named on the list and carry their concept counts
    (FR-016, User Story 3 scenario 2)."""
    if status != 200:
        fail(list_url, status, "the vocabulary list did not serve", body)
    for name, count in ((IMPORTED_NAME, IMPORTED_CONCEPT_COUNT), (AUTHORED_NAME, AUTHORED_CONCEPT_COUNT)):
        if name not in body:
            fail(list_url, status, f"the seeded vocabulary {name!r} is not on the list — the seed did not load", body)
        if f"{count} concept" not in body:
            fail(list_url, status, f"{name!r}'s concept count ({count}) is not on the page", body)


def check_search(search_url, status, body):
    """A search narrows the list to the vocabulary it matches and excludes the other
    (User Story 3 scenario 5)."""
    if status != 200:
        fail(search_url, status, "a search did not serve", body)
    if IMPORTED_NAME not in body:
        fail(search_url, status, f"a search for {SEARCH_TERM!r} does not narrow to {IMPORTED_NAME!r}", body)
    if AUTHORED_NAME in body:
        fail(
            search_url,
            status,
            f"a search for {SEARCH_TERM!r} still shows {AUTHORED_NAME!r} — the search did not narrow",
            body,
        )


def get(url):
    """GET ``url`` and return ``(status, body)``, failing on a connection error (FR-017)."""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 — http(s) only, built from argv
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        fail(url, None, f"could not connect: {exc.reason}")
        raise  # pragma: no cover — fail() always raises; this satisfies the type checker


def walk(base_url):
    """Request the list, then a search, and check both (User Story 3 scenario 5)."""
    base_url = base_url.rstrip("/")
    list_url = f"{base_url}/browse/"
    status, body = get(list_url)
    check_list(list_url, status, body)

    search_url = f"{list_url}?q={SEARCH_TERM}"
    status, body = get(search_url)
    check_search(search_url, status, body)


def main(argv):
    base_url = argv[1] if len(argv) > 1 else "http://127.0.0.1:8000"
    try:
        walk(base_url)
    except SmokeCheckFailed as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"OK: walked the demo vocabulary list and a search, at {base_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
