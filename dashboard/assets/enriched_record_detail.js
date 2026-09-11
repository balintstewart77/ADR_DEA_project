(function () {
    "use strict";

    const MODAL_SELECTOR = "#enriched-record-detail-modal";
    const CLOSE_ID = "enriched-record-detail-close";
    let invokingControl = null;
    let invokingRecordId = null;
    let modalHasOpened = false;

    function rememberInvokingControl(target) {
        const control = target && target.closest && target.closest(".enriched-detail-trigger");
        if (control) {
            invokingControl = control;
            invokingRecordId = control.dataset.recordId || null;
        }
    }

    function modalIsOpen() {
        const modal = document.querySelector(MODAL_SELECTOR);
        return Boolean(modal && window.getComputedStyle(modal).display !== "none");
    }

    function returnFocusAfterClose() {
        if (modalIsOpen()) {
            modalHasOpened = true;
            return;
        }
        if (modalHasOpened && invokingControl) {
            let control = invokingControl;
            if (!document.contains(control) && invokingRecordId) {
                control = document.querySelector(
                    `.enriched-detail-trigger[data-record-id="${CSS.escape(invokingRecordId)}"]`,
                );
            }
            invokingControl = null;
            invokingRecordId = null;
            modalHasOpened = false;
            if (control) {
                window.setTimeout(function () { control.focus(); }, 0);
            }
        }
    }

    function scheduleFocusReturn() {
        window.setTimeout(function waitForClose() {
            if (modalIsOpen()) {
                window.setTimeout(waitForClose, 100);
                return;
            }
            returnFocusAfterClose();
        }, 300);
    }

    function restoreFocusFromRecordId() {
        const recordId = invokingRecordId;
        if (!recordId) {
            return;
        }
        window.setTimeout(function () {
            const control = document.querySelector(
                `.enriched-detail-trigger[data-record-id="${CSS.escape(recordId)}"]`,
            );
            if (control) {
                control.focus();
            }
        }, 350);
    }

    document.addEventListener("click", function (event) {
        rememberInvokingControl(event.target);
        if (event.target && event.target.id === CLOSE_ID) {
            scheduleFocusReturn();
            restoreFocusFromRecordId();
        }
    }, true);
    document.addEventListener("focusin", function (event) {
        rememberInvokingControl(event.target);
    }, true);
    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape" || !modalIsOpen()) {
            return;
        }
        event.preventDefault();
        const closeControl = document.getElementById(CLOSE_ID);
        if (closeControl) {
            closeControl.click();
            scheduleFocusReturn();
            restoreFocusFromRecordId();
        }
    });

    new MutationObserver(returnFocusAfterClose).observe(document.documentElement, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["class"],
    });
}());
