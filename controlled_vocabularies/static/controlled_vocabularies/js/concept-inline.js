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
 */
(function () {
    "use strict";

    function templateRowId(rowId) {
        return rowId.replace(/-\d+-/, "-__prefix__-");
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
            window.djangoTomSelect.initialize(select, config);
        });
    }

    document.addEventListener("formset:added", function (event) {
        initialiseRow(event.target);
    });
})();
