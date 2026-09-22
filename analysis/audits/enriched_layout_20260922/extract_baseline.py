"""Capture Enriched Register content baselines by invoking the production callback.

Read-only. Imports ``dashboard.app``, looks up the registered Dash callback that
produces the Enriched Register table data / count / facet options, and calls that
exact function. No filtering, sorting or pagination logic is reimplemented here.

Usage:
    python analysis/audits/enriched_layout_20260922/extract_baseline.py <out_dir>
"""

from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import dashboard.app as dashboard_app  # noqa: E402
from dashboard.data.registry import df_all  # noqa: E402
from dashboard.data.year_filter import year_slider_kwargs  # noqa: E402
from dashboard.layout.analysis.thematic import ENRICHED_TABLE_STYLES  # noqa: E402  (import check only)

_CALLBACK_OUTPUT_MARKER = "enriched-register-table.data"

# Filter states. Keys are the callback's parameter names.
_YEAR = year_slider_kwargs(df_all)
_DEFAULTS = dict(
    search=None,
    dataset_filter="ALL",
    provider_filter="ALL",
    institution_filter="ALL",
    tre_filter="ALL",
    domain_filter="ALL",
    domain_count_filter="ALL",
    purpose_filter="ALL",
    tag_filter="ALL",
    record_linkage_filter="ALL",
    collection_method_filter="ALL",
    temporal_structure_filter="ALL",
    unit_filter="ALL",
    researcher_sector_filter="ALL",
    page_size=20,
    accreditation_year_range=list(_YEAR["value"]),
    portfolio_year_range=list(_YEAR["value"]),
    sort_by=[],
    accreditation_year_min=_YEAR["min"],
    accreditation_year_max=_YEAR["max"],
)

FILTER_STATES = {
    "F0": {},
    "F1": {
        "dataset_filter": "Annual Survey of Hours and Earnings (ASHE)",
        "domain_filter": "Labour Market & Employment",
    },
}

_FACET_KEYS = [
    "dataset", "provider", "institution", "tre", "domain", "domain_count",
    "purpose", "tag", "record_linkage", "collection_method",
    "temporal_structure", "unit", "researcher_sector",
]


def _enriched_callback():
    for key, entry in dashboard_app.app.callback_map.items():
        if _CALLBACK_OUTPUT_MARKER in key:
            wrapper = entry["callback"]
            # Dash wraps the user function for HTTP dispatch; __wrapped__ is the
            # production callback body itself (update_enriched_register).
            return getattr(wrapper, "__wrapped__", wrapper), key
    raise RuntimeError("Enriched Register table callback not found in app.callback_map")


def _table_column_ids():
    """The table's column set and order, read from the built layout component."""
    def walk(node):
        if getattr(node, "id", None) == "enriched-register-table":
            return node
        for child in (getattr(node, "children", None) or []) if isinstance(
            getattr(node, "children", None), (list, tuple)
        ) else ([getattr(node, "children")] if getattr(node, "children", None) is not None else []):
            found = walk(child)
            if found is not None:
                return found
        return None

    table = walk(dashboard_app.app.layout)
    if table is None:
        raise RuntimeError("enriched-register-table not found in app.layout")
    return [{"name": c["name"], "id": c["id"]} for c in table.columns]


def run_state(callback, overrides):
    kwargs = dict(_DEFAULTS)
    kwargs.update(overrides)
    result = callback(**kwargs)
    (records, page_size, count_text, *facet_option_lists) = result
    facets = dict(zip(_FACET_KEYS, facet_option_lists))
    return records, page_size, count_text, facets


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    callback, callback_key = _enriched_callback()

    columns = _table_column_ids()
    displayed_ids = [c["id"] for c in columns]

    readable = {}
    complete = {}
    for state_name, overrides in FILTER_STATES.items():
        records, page_size, count_text, facets = run_state(callback, overrides)
        record_ids = [r["id"] for r in records]

        readable[state_name] = {
            "count_text": count_text,
            "page_size": page_size,
            "first_20_record_ids": record_ids[:20],
            "facet_option_labels": {
                name: [
                    {"label": o.get("label"), "value": o.get("value")}
                    for o in options
                ]
                for name, options in facets.items()
            },
        }
        complete[state_name] = {
            "record_ids_in_order": record_ids,
            "n_records": len(record_ids),
            "rows": [
                {"id": r["id"], **{col: r.get(col) for col in displayed_ids}}
                for r in records
            ],
        }

    meta = {
        "callback_key": callback_key,
        "callback_qualname": getattr(callback, "__qualname__", None),
        "production_functions_invoked": [
            "dashboard.app.app.callback_map[<enriched key>]['callback']"
            " -> __wrapped__ (the registered update_enriched_register callback body)",
        ],
        "defaults": {k: v for k, v in _DEFAULTS.items()},
        "filter_states": FILTER_STATES,
        "table_columns": columns,
        "enriched_table_styles_present": bool(ENRICHED_TABLE_STYLES),
    }

    for name, payload in (
        ("readable_check.json", readable),
        ("complete_check.json", complete),
        ("baseline_meta.json", meta),
    ):
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1, sort_keys=True, ensure_ascii=False)
        print("wrote", path)

    for state_name in FILTER_STATES:
        print(
            state_name,
            readable[state_name]["count_text"],
            "| complete rows:", complete[state_name]["n_records"],
        )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(_HERE, "before"))
