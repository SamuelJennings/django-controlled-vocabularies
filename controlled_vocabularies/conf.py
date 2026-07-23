"""Configuration access for controlled_vocabularies.

A single read site for the base address used to compose concept and scheme URIs
(research decision R2). Keeping the read in one place stops the composition rule
from scattering across the models.
"""

from django.conf import settings

#: Default base address when the host project does not configure one. A localhost
#: placeholder that signals "configure me for real deployments" while keeping the
#: package usable standalone. Documented in the README.
DEFAULT_BASE_URI = "http://localhost:8000/vocabularies"


def get_base_uri() -> str:
    """Return the configured base URI for vocabulary/concept URIs, without a trailing slash.

    Reads ``settings.CONTROLLED_VOCABULARIES_BASE_URI`` and falls back to
    :data:`DEFAULT_BASE_URI`. A trailing slash is stripped so callers can compose
    with ``f"{base}/{slug}"`` unconditionally.
    """
    base = getattr(settings, "CONTROLLED_VOCABULARIES_BASE_URI", DEFAULT_BASE_URI)
    return base.rstrip("/")
