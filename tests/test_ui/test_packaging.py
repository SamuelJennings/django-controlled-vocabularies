"""Tests proving django-mvp only ever arrives through the opt-in ``ui`` extra (T004).

There is no ``controlled_vocabularies/ui/packaging.py`` to mirror against — the subject is
``pyproject.toml`` itself — so this file is one of the standing non-mirror exceptions
(``[tool.forge.conformance] non-mirror-paths``, T001).
"""

import tomllib
from pathlib import Path

PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"


def load_pyproject():
    return tomllib.loads(PYPROJECT_PATH.read_text())


class TestDjangoMVPIsOptOnly:
    """FR-012 — installing the core alone resolves no ui dependency."""

    def test_django_mvp_is_optional(self):
        pyproject = load_pyproject()
        dependency = pyproject["tool"]["poetry"]["dependencies"]["django-mvp"]
        assert dependency["optional"] is True

    def test_django_mvp_is_declared_in_the_ui_extra(self):
        pyproject = load_pyproject()
        extras = pyproject["tool"]["poetry"]["extras"]
        assert extras["ui"] == ["django-mvp"]

    def test_django_mvp_is_absent_from_every_other_extra(self):
        pyproject = load_pyproject()
        extras = pyproject["tool"]["poetry"]["extras"]
        for extra_name, packages in extras.items():
            if extra_name == "ui":
                continue
            assert "django-mvp" not in packages

    def test_django_mvp_is_absent_from_every_poetry_dependency_group(self):
        pyproject = load_pyproject()
        groups = pyproject["tool"]["poetry"].get("group", {})
        for group_name, group in groups.items():
            dependencies = group.get("dependencies", {})
            assert "django-mvp" not in dependencies, f"django-mvp found in poetry group '{group_name}'"
