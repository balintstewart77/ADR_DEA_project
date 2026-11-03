(function () {
    "use strict";

    // AG Grid moves keyboard focus between cells, never into them. Enter or
    // Space on a focused Enriched Register cell presses the control inside it
    // ("View details", "+N more entries", "View full value" or "Read more").
    // Closing the record modal puts focus back on the cell that opened it.
    const GRID_SELECTOR = "#enriched-register-table";
    const CELL_SELECTOR = `${GRID_SELECTOR} .ag-cell`;
    const CONTROL_SELECTOR = ".enriched-detail-trigger, details.rationale-details > summary";
    const MODAL_SELECTOR = "#enriched-record-detail-modal";
    const CLOSE_ID = "enriched-record-detail-close";
    let origin = null;

    function modalIsOpen() {
        const modal = document.querySelector(MODAL_SELECTOR);
        return Boolean(modal && window.getComputedStyle(modal).display !== "none");
    }

    function rememberOrigin(target) {
        const cell = target.closest && target.closest(CELL_SELECTOR);
        const row = cell && cell.closest(".ag-row");
        if (row) {
            origin = {rowId: row.getAttribute("row-id"), colId: cell.getAttribute("col-id")};
        }
    }

    function returnFocusOnceClosed() {
        let checks = 0;
        window.setTimeout(function waitForClose() {
            if (modalIsOpen() && checks++ < 50) {
                window.setTimeout(waitForClose, 100);
                return;
            }
            const target = origin;
            origin = null;
            const cell = target && document.querySelector(
                `${GRID_SELECTOR} .ag-row[row-id="${CSS.escape(target.rowId)}"]`
                + ` .ag-cell[col-id="${CSS.escape(target.colId)}"]`,
            );
            if (cell) {
                cell.focus();
            }
        }, 100);
    }

    document.addEventListener("click", function (event) {
        if (event.target.id === CLOSE_ID) {
            returnFocusOnceClosed();
        } else {
            rememberOrigin(event.target);
        }
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && modalIsOpen()) {
            // The modal ignores Escape itself so that closing goes through Dash.
            event.preventDefault();
            const close = document.getElementById(CLOSE_ID);
            if (close) {
                close.click();
            }
            return;
        }
        if ((event.key === "Enter" || event.key === " ") && event.target.matches(CELL_SELECTOR)) {
            const control = event.target.querySelector(CONTROL_SELECTOR);
            if (control) {
                event.preventDefault();
                control.click();
            }
        }
    });
}());
