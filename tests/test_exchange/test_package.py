"""T002 — the ``controlled_vocabularies.exchange`` package exists and is importable.

The package is the new module tree the import feature lands in (plan.md
Project Structure); this only asserts the scaffold itself is in place. Each
later task (T003 the report, T004 the safety scan) extends what
``exchange/__init__.py`` re-exports and gets its own test for that surface.
"""

import controlled_vocabularies.exchange as exchange


def test_package_is_importable():
    assert exchange is not None


def test_package_has_a_module_docstring():
    # A public package gets documented (Article VI); this catches an
    # accidentally-empty __init__.py before anything is re-exported from it.
    assert exchange.__doc__, "controlled_vocabularies.exchange has no module docstring"
