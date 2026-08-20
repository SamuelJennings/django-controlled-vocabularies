"""Empty URLconf for ``tests.settings_core``.

The core-only settings module must stay free of the ui app's URLs — this is what the fresh-
subprocess core-only boot test (``tests/test_ui/test_boot.py``) resolves ``ROOT_URLCONF``
against.
"""

urlpatterns = []
