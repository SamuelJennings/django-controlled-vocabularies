from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ControlledVocabulariesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "controlled_vocabularies"
    verbose_name = _("Controlled Vocabularies")

    def ready(self):
        from django.core.checks import register

        from .checks import (
            check_concept_autocomplete_route_included,
            check_concept_field_vocabularies,
            check_django_tomselect_installed,
        )

        register(check_concept_field_vocabularies)
        register(check_concept_autocomplete_route_included)
        register(check_django_tomselect_installed)
