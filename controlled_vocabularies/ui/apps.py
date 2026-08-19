from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ControlledVocabulariesUIConfig(AppConfig):
    """Django AppConfig for the opt-in vocabulary-browsing front end.

    ``label`` is distinct from the core app's (``controlled_vocabularies``) — the app registry
    refuses two installed apps sharing one label, and this app is always installed alongside the
    core, never instead of it.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "controlled_vocabularies.ui"
    label = "controlled_vocabularies_ui"
    verbose_name = _("Controlled Vocabularies UI")
