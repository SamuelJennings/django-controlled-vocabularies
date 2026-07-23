from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ControlledVocabulariesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "controlled_vocabularies"
    verbose_name = _("Controlled Vocabularies")
