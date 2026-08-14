/**
 * Initialises a concept search control in an inline row added by Django's
 * "Add another" (research.md R4). Django's admin/js/inlines.js clones the
 * empty-form template row and dispatches a bubbling `formset:added` event on
 * it, but the clone's own inline `<script>` never runs — jQuery marks a
 * script inside a clone of an in-page element as already evaluated — and
 * django-tomselect does not listen for `formset:added` itself.
 *
 * This listens for that event, and for each `select[data-tomselect]` in the
 * added row recovers the configuration registered against the template row
 * (its element id carries `__prefix__`, not a row number) by substituting
 * the new row's own numeric segment back to `__prefix__`, then calls
 * `window.djangoTomSelect.initialize` — the same call django-tomselect's own
 * per-widget script makes on page load. Additive only: no django-tomselect
 * initialisation path is replaced or patched, and nothing happens on a page
 * that never fires `formset:added`.
 *
 * The substitution targets the **last** `-<digits>-` segment in the id, not
 * the first. A core-Django inline id carries exactly one, since the formset
 * prefix comes from an accessor name and must be a valid identifier — but a
 * nested inline (a third-party capability core Django does not have) produces
 * `id_orders-0-items-1-product`, where the row being added is the inner one
 * and the template registered for it is `id_orders-0-items-__prefix__-product`.
 * Taking the first segment would look up a key that was never registered and
 * leave the new row holding a bare `<select>`.
 */
(function () {
    "use strict";

    function templateRowId(rowId) {
        return rowId.replace(/-\d+-(?![\s\S]*-\d+-)/, "-__prefix__-");
    }

    /**
     * Discards the control markup the clone brought with it. The template row
     * is initialised on page load like any other, so its rendered `.ts-wrapper`
     * is part of what Django clones — and Django then rewrites `__prefix__` to
     * the new row number inside it, giving the added row a second, inert
     * control carrying duplicate element ids. It is markup only, with no
     * TomSelect instance behind it, so `initialize`'s own destroy step does not
     * reach it. Any wrapper belonging to a live instance is left alone.
     */
    function discardClonedControl(select) {
        var live = select.tomselect ? select.tomselect.wrapper : null;
        var parent = select.parentElement;
        if (!parent) {
            return;
        }
        parent.querySelectorAll(":scope > .ts-wrapper").forEach(function (wrapper) {
            if (wrapper !== live) {
                wrapper.remove();
            }
        });
    }

    function initialiseRow(row) {
        if (!(row instanceof HTMLElement) || !window.djangoTomSelect) {
            return;
        }
        row.querySelectorAll("select[data-tomselect]").forEach(function (select) {
            var config = window.djangoTomSelect.configs.get(templateRowId(select.id));
            if (!config) {
                return;
            }
            discardClonedControl(select);
            window.djangoTomSelect.initialize(select, config);
        });
    }

    document.addEventListener("formset:added", function (event) {
        initialiseRow(event.target);
    });
})();
