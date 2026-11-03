(function () {
    "use strict";

    function isMissing(value) {
        return value === null || value === undefined || Number.isNaN(value);
    }

    const functions = (window.dashAgGridFunctions = window.dashAgGridFunctions || {});

    // Missing values last in both directions, as Dash DataTable sorted them.
    // Blank strings are values. Other values compare as AG Grid's default does.
    functions.nullsLast = function (a, b, nodeA, nodeB, isDescending) {
        const aMissing = isMissing(a);
        const bMissing = isMissing(b);
        if (aMissing || bMissing) {
            if (aMissing && bMissing) {
                return 0;
            }
            // The grid reverses the result for a descending sort.
            return (aMissing ? 1 : -1) * (isDescending ? -1 : 1);
        }
        return a > b ? 1 : (a < b ? -1 : 0);
    };

    const components = (window.dashAgGridComponentFunctions = window.dashAgGridComponentFunctions || {});

    // A cell that shows HTML the server built and escaped, stored in the row
    // under the column's id. The column's field holds the value it sorts by.
    components.ServerHtml = function (props) {
        const html = props.data ? props.data[props.column.getColId()] : "";
        return React.createElement("div", {dangerouslySetInnerHTML: {__html: html || ""}});
    };
}());
