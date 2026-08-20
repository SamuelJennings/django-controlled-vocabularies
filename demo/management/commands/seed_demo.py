"""``python manage.py seed_demo`` (T016, FR-016, User Story 3 scenarios 2 and 3).

Destructive and idempotent: every vocabulary is deleted before the two seed files load, so
re-running always returns the demo to the same state whatever was added or removed since —
including anything entered through the admin. Both files load through the package's own import
path (``controlled_vocabularies.exchange.import_skos``), never a Django fixture loaded behind
it, so the demo exercises exactly what a real project does.
"""

from pathlib import Path

from django.core.management.base import BaseCommand

from controlled_vocabularies.exchange import import_skos
from controlled_vocabularies.models import ConceptScheme

SEED_DIR = Path(__file__).resolve().parent.parent.parent / "seed"

#: Declares its own skos:ConceptScheme with a real, externally published URI, so the vocabulary
#: it becomes reads as "Imported" on the list (FR-003).
IMPORTED_FILE = SEED_DIR / "dcmi_types.ttl"

#: Declares no vocabulary of its own — loaded against AUTHORED_NAME below, created directly
#: here rather than by import, so that vocabulary reads as "Held here" on the list (FR-003).
AUTHORED_FILE = SEED_DIR / "research_methods.ttl"

AUTHORED_NAME = "Data Collection Methods"
AUTHORED_DESCRIPTION = (
    "Categories of method by which a research dataset was produced — authored for this "
    "demo rather than imported from a publisher."
)


class Command(BaseCommand):
    help = (
        "Delete every vocabulary, then reload the demo's two seed vocabularies: one imported "
        "from a publisher, one authored here. Destructive: anything entered through the admin "
        "is lost."
    )

    def handle(self, *args, **options):
        ConceptScheme.objects.all().delete()

        import_skos(IMPORTED_FILE)

        authored_scheme = ConceptScheme.objects.create(
            name=AUTHORED_NAME,
            description=AUTHORED_DESCRIPTION,
        )
        import_skos(AUTHORED_FILE, scheme=authored_scheme)

        self.stdout.write(self.style.SUCCESS("seed_demo loaded 2 vocabularies"))
