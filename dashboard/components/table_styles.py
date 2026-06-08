"""Shared DataTable style dicts."""

BROWSE_TABLE_STYLES = dict(
    style_table={"overflowX": "auto"},
    style_cell={
        "textAlign": "left",
        "padding": "8px 12px",
        "fontFamily": '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        "fontSize": "13px",
        "whiteSpace": "normal",
        "maxWidth": "350px",
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "borderBottom": "1px solid #f0f0f0",
    },
    style_header={
        "backgroundColor": "#2c3e50",
        "color": "white",
        "fontWeight": "600",
        "fontSize": "12px",
        "textTransform": "uppercase",
        "letterSpacing": "0.03em",
        "padding": "10px 12px",
        "borderBottom": "none",
    },
    style_data_conditional=[
        {"if": {"row_index": "odd"}, "backgroundColor": "#fafbfc"},
    ],
)

ENRICHED_TABLE_STYLES = dict(
    style_table={"overflowX": "auto"},
    style_cell={
        "textAlign": "left",
        "padding": "8px 12px",
        "fontFamily": '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        "fontSize": "13px",
        "whiteSpace": "normal",
        "maxWidth": "350px",
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "borderBottom": "1px solid #f0f0f0",
    },
    style_header={
        "backgroundColor": "#2c3e50",
        "color": "white",
        "fontWeight": "600",
        "fontSize": "12px",
        "textTransform": "uppercase",
        "letterSpacing": "0.03em",
        "padding": "10px 12px",
        "borderBottom": "none",
    },
    style_data_conditional=[
        {"if": {"row_index": "odd"}, "backgroundColor": "#fafbfc"},
        {"if": {"column_id": "record_linkage"}, "backgroundColor": "#f5f8fa"},
        {"if": {"column_id": "substantive_domains"}, "backgroundColor": "#f5f8fa"},
        {"if": {"column_id": "substantive_domain_count"}, "backgroundColor": "#f5f8fa"},
        {"if": {"column_id": "analytical_purpose"}, "backgroundColor": "#f5f8fa"},
    ],
)
