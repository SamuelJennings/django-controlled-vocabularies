"""The demo's admin lets a person add a vocabulary by hand (T015, FR-014, User Story 3).

The story promises a reader can "add a vocabulary by hand to see it appear", and the README
turns that into a documented instruction: run ``createsuperuser``, sign in at ``/admin/``. The
package registers nothing with any admin site — a curator interface is a later feature — so the
demo project has to register the model itself, or the documented step leads to an admin index
holding only users and groups.

Run in a fresh subprocess for the same reason ``test_demo.py`` is: ``django.setup()`` runs once
per interpreter, and the pytest session has already booted the app registry from
``tests.settings``.

The subject is ``demo/admin.py``, which sits outside the package the mirror rule walks, so this
file is a non-mirror exception (``[tool.forge.conformance] non-mirror-paths``) alongside every
other module in this directory.
"""

import subprocess
import sys

#: The documented instruction walked end to end. Asserting the model is merely *registered*
#: would be too weak a gate: a bare registration satisfies it and still refuses the submission,
#: because ``slug`` is unique, required and derived on save, so a form carrying it demands a
#: value the model is about to compute.
ADMIN_SCRIPT = """
import os, tempfile
os.environ["DJANGO_SETTINGS_MODULE"] = "demo.settings"
os.environ["DEMO_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "db.sqlite3")
import django
django.setup()

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client
from django.test.utils import setup_test_environment
from django.urls import reverse

from controlled_vocabularies.models import ConceptScheme

setup_test_environment()
call_command("migrate", verbosity=0)

client = Client()
client.force_login(get_user_model().objects.create_superuser("demo", "demo@example.com", "pw"))

add_url = reverse("admin:controlled_vocabularies_conceptscheme_add")
assert client.get(add_url).status_code == 200, "the admin serves no form for adding a vocabulary"

client.post(add_url, {"name": "Added By Hand", "description": "Typed in.", "default_language": "", "static_uri": ""})
assert ConceptScheme.objects.filter(name="Added By Hand").exists(), "the submitted form stored nothing"

listing = client.get(reverse("controlled_vocabularies_ui:vocabulary-list")).content.decode()
assert "Added By Hand" in listing, "the hand-added vocabulary is absent from the list"

print("DEMO_ADMIN_OK")
"""


class TestDemoAdmin:
    """FR-014, User Story 3 — signing in at the demo's admin, adding a vocabulary and finding
    it on the list is the one interactive instruction the demo carries, and it works."""

    def test_a_vocabulary_added_through_the_admin_appears_on_the_list(self):
        result = subprocess.run(  # noqa: S603 — fixed interpreter, literal script, no user input
            [sys.executable, "-c", ADMIN_SCRIPT],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "DEMO_ADMIN_OK" in result.stdout
