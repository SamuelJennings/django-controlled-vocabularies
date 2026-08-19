"""System check surfacing a project that installed ``controlled_vocabularies.ui`` without the
``ui`` extra (013-find-a-vocabulary, FR-012's neighbour, plan.md Key design decisions #5).

Without it the first symptom is a bare ``ModuleNotFoundError: mvp`` raised from URL loading,
which names neither the extra nor the app that needs it. Registered from
:meth:`~controlled_vocabularies.ui.apps.ControlledVocabulariesUIConfig.ready`.
"""

from django.core import checks
from django.utils.translation import gettext_lazy as _

CHECK_ID = "controlled_vocabularies.ui.E001"


def check_mvp_installed(app_configs, **kwargs):
    """Report an error when ``django-mvp`` cannot be imported.

    A real ``import mvp`` rather than an ``importlib.util.find_spec`` probe, so the check
    behaves exactly like the URL loading it replaces the failure of.
    """
    try:
        import mvp  # noqa: F401
    except ImportError:
        return [
            checks.Error(
                _(
                    "django-mvp is not installed, but controlled_vocabularies.ui requires it. "
                    "Install the 'ui' extra: pip install django-controlled-vocabularies[ui]."
                ),
                id=CHECK_ID,
            )
        ]
    return []
