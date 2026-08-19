"""Django settings for the full test suite, with the opt-in ui front end wired in.

``tests.settings_core`` is the base — everything the core needs on its own — and this module
imports from it and appends the ui stack (013-find-a-vocabulary plan.md, Structure Decision).
"""

from tests.settings_core import *

INSTALLED_APPS = [
    *INSTALLED_APPS,
    "django_cotton",
    "easy_icons",
    "flex_menu",
    # ``mvp`` before ``crispy_tailwind``: django-mvp ships an override of
    # crispy-tailwind's help-text template, and the first app to declare a
    # template path wins (django-mvp's getting-started guide).
    "mvp",
    "crispy_forms",
    "crispy_tailwind",
    "controlled_vocabularies.ui",
]

# crispy-forms 2.7's get_template_pack() is getattr(settings, "CRISPY_TEMPLATE_PACK") with no
# default, so leaving this unset is an AttributeError on the first form render rather than a
# fallback to another pack.
CRISPY_TEMPLATE_PACK = "tailwind"

# And the allowlist has to name it too. The {% crispy %} tag validates the pack at
# TEMPLATE-COMPILE time against CRISPY_ALLOWED_TEMPLATE_PACKS, whose default is
# ("uni_form", "bootstrap3", "bootstrap4") — so every template carrying the tag fails to
# compile. django-mvp's own demo sets both settings together for the same reason.
CRISPY_ALLOWED_TEMPLATE_PACKS = ["tailwind"]

TEMPLATES[0]["OPTIONS"]["context_processors"] = [
    *TEMPLATES[0]["OPTIONS"]["context_processors"],
    "mvp.context_processors.mvp_config",
]

ROOT_URLCONF = "tests.urls"

# django-mvp resolves every icon name it renders through django-easy-icons; without a
# "default" renderer configured, any page using <c-icon> (which mvp's base template does)
# raises ImproperlyConfigured.
EASY_ICONS = {
    "default": {
        "renderer": "easy_icons.renderers.ProviderRenderer",
        "config": {"tag": "i"},
        "packs": ["mvp.utils.BS5_ICONS"],
    },
}

# django-mvp's chrome (sidebar, mobile dock) is rendered by django-flex-menus, which raises
# ValueError at render time without these renderers configured.
FLEX_MENUS = {
    "renderers": {
        "sidebar": "mvp.renderers.SidebarRenderer",
        "dock": "mvp.renderers.MobileFooterNavRenderer",
    },
}
