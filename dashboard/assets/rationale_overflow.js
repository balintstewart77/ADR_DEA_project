(function () {
    "use strict";

    const TABLE_SELECTOR = "#enriched-register-table";
    const PREVIEW_SELECTOR = ".rationale-cell > .rationale-preview";
    const DETAILS_SELECTOR = ".rationale-cell > details.rationale-details";

    function RationaleOverflowManager(root) {
        this.root = root;
        this.previews = new Set();
        this.frame = null;
        this.handleToggle = this.handleToggle.bind(this);
        this.schedule = this.schedule.bind(this);

        this.resizeObserver = new ResizeObserver(this.schedule);
        this.mutationObserver = new MutationObserver(() => {
            this.sync();
            this.schedule();
        });
        this.resizeObserver.observe(root);
        this.mutationObserver.observe(root, {childList: true, subtree: true});
        root.addEventListener("toggle", this.handleToggle, true);
        this.sync();
        this.schedule();
    }

    RationaleOverflowManager.prototype.sync = function () {
        const current = new Set(this.root.querySelectorAll(PREVIEW_SELECTOR));
        this.previews.forEach((preview) => {
            if (!current.has(preview)) {
                this.resizeObserver.unobserve(preview);
            }
        });
        current.forEach((preview) => {
            if (!this.previews.has(preview)) {
                this.resizeObserver.observe(preview);
            }
        });
        this.previews = current;
    };

    RationaleOverflowManager.prototype.schedule = function () {
        if (this.frame !== null) {
            return;
        }
        this.frame = window.requestAnimationFrame(() => {
            this.frame = null;
            this.measure();
        });
    };

    RationaleOverflowManager.prototype.measure = function () {
        this.sync();
        this.previews.forEach((preview) => {
            const cell = preview.closest(".rationale-cell");
            const details = cell && cell.querySelector(DETAILS_SELECTOR);
            if (!details) {
                return;
            }
            if (details.open) {
                details.dataset.overflow = "true";
                return;
            }
            if (preview.clientWidth <= 0 || preview.getClientRects().length === 0) {
                // A hidden accordion or tab cannot be measured. Keep disclosure usable.
                details.dataset.overflow = "unknown";
                return;
            }
            details.dataset.overflow = (
                preview.scrollHeight > preview.clientHeight + 1
            ) ? "true" : "false";
        });
    };

    RationaleOverflowManager.prototype.handleToggle = function (event) {
        const details = event.target;
        if (!(details instanceof HTMLDetailsElement) || !details.matches(DETAILS_SELECTOR)) {
            return;
        }
        const cell = details.closest(".rationale-cell");
        if (cell) {
            cell.classList.toggle("rationale-expanded", details.open);
        }
        this.mirrorToggle(details);
        if (details.open) {
            // Never remove the control while the row is expanded.
            details.dataset.overflow = "true";
        } else {
            this.schedule();
        }
    };

    // fixed_columns renders the body twice (pinned and scrolling copies) and each
    // copy sizes its rows independently. A disclosure opened in the visible copy
    // must open in the hidden one too, or every row below it goes out of line.
    // The counterpart's own toggle event lands here again and stops at the
    // equality check.
    RationaleOverflowManager.prototype.mirrorToggle = function (details) {
        const td = details.closest("td");
        const tr = td && td.parentElement;
        const table = tr && tr.closest("table");
        const container = table && table.closest(".dt-table-container__row");
        if (!container) {
            return;
        }
        container.querySelectorAll("table").forEach((other) => {
            if (other === table) {
                return;
            }
            const otherRow = other.rows[tr.rowIndex];
            const otherCell = otherRow && otherRow.cells[td.cellIndex];
            const counterpart = otherCell && otherCell.querySelector(DETAILS_SELECTOR);
            if (counterpart && counterpart.open !== details.open) {
                counterpart.open = details.open;
            }
        });
    };

    RationaleOverflowManager.prototype.closeExpanded = function () {
        this.root.querySelectorAll(`${DETAILS_SELECTOR}[open]`).forEach((details) => {
            details.open = false;
            const cell = details.closest(".rationale-cell");
            if (cell) {
                cell.classList.remove("rationale-expanded");
            }
        });
    };

    RationaleOverflowManager.prototype.destroy = function () {
        if (this.frame !== null) {
            window.cancelAnimationFrame(this.frame);
        }
        this.resizeObserver.disconnect();
        this.mutationObserver.disconnect();
        this.root.removeEventListener("toggle", this.handleToggle, true);
        this.previews.clear();
    };

    function ensureManager() {
        const root = document.querySelector(TABLE_SELECTOR);
        let manager = window.__enrichedRationaleOverflowManager;
        if (manager && manager.root !== root) {
            manager.destroy();
            manager = null;
            window.__enrichedRationaleOverflowManager = null;
        }
        if (root && !manager) {
            manager = new RationaleOverflowManager(root);
            window.__enrichedRationaleOverflowManager = manager;
        }
        return manager;
    }

    window.dash_clientside = Object.assign({}, window.dash_clientside, {
        enrichedRationale: {
            update: function (viewportRows, pageCurrent, sortBy) {
                window.requestAnimationFrame(() => {
                    window.requestAnimationFrame(() => {
                        const manager = ensureManager();
                        if (manager) {
                            manager.closeExpanded();
                            manager.sync();
                            manager.schedule();
                        }
                    });
                });
                return {
                    page: pageCurrent,
                    sort: sortBy || [],
                    recordIds: (viewportRows || []).map((row) => row.id)
                };
            }
        }
    });
}());
