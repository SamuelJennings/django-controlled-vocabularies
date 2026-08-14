# ADR 0013 — The Django admin stays an optional dependency

**Status:** accepted

## Decision

This package does not require `django.contrib.admin`. Nothing it adds may be imported at startup in
a way that assumes the admin is installed, and no system check may report on the admin in a project
that does not have it.

The one place that needs an admin class holds a single lookup function in
`controlled_vocabularies/admin.py`, whose import of `django.contrib.admin.widgets` sits inside the
function body behind an `apps.is_installed()` test. The module itself is imported on every render,
which is fine. Nothing is registered there.

The behaviour reaches a consuming model registered on a project's own `AdminSite` exactly as it does
on the default one, and holds when the same model is registered on more than one site.

## Why

The consumption fields are for any Django project, and the admin is optional in Django's own
layering. A package that made it mandatory would break projects that never asked for the feature,
at startup rather than on a page.

The custom-site half is the same argument from the other direction. A feature wired only to
`django.contrib.admin.site` would appear to work in a test project and silently do nothing in a
project running its own site, which is common in the research-infrastructure projects this package
is built for.

Proving this needs a settings module without the admin, and a separate root URL configuration to go
with it. The test project's usual one mounts the admin unconditionally, and building the URL
resolver walks that entry and imports `django.contrib.admin` whichever route is being reversed —
which would fail the proof for a reason having nothing to do with the feature.

## Revisit if

A later feature genuinely cannot be delivered without the admin present. At that point the choice
is an optional extra a project installs deliberately, not a new hard requirement on every consumer.
