"""The opt-in front end for browsing the vocabularies this site holds (013-find-a-vocabulary).

``controlled_vocabularies.ui`` is an installed Django app, so this module is imported during
app-registry phase 1 — before ``controlled_vocabularies.models`` is ready. It stays a docstring
and nothing else for that reason: a re-export reaching ``views.py`` would reach the models and
raise ``AppRegistryNotReady`` at ``django.setup()``, failing every install. Import from
``controlled_vocabularies.ui.views`` (or whichever module) directly.
"""
