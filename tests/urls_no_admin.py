"""Root URL configuration for ``tests/settings_no_admin.py`` (012 T014).

``tests/urls.py`` mounts ``admin.site.urls`` unconditionally, and resolving
*any* route through it walks every pattern in the urlconf — including that
one — which imports ``django.contrib.admin`` the moment ``AdminSite`` builds
its own default site, regardless of what the resolved route actually is.
That would make the FR-006 proof fail for a reason unrelated to the feature.
This urlconf carries only the package's own route, mirroring what a project
without the admin actually mounts.
"""

from django.urls import include, path

urlpatterns = [
    path("vocabularies/", include("controlled_vocabularies.urls")),
]
