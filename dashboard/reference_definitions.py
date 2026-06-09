"""Dashboard-side reader for deterministic facet definitions.

The reference YAML is the source of truth for deterministic facet rules. Keeping
the dashboard wired to this file avoids drift when the controlled vocabulary is
updated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REFERENCE_FILENAME = "register_reference.yaml"


FACET_CONFIG = (
    {
        "name": "Record linkage",
        "values": (
            "No record linkage",
            "Within-domain record linkage",
            "Cross-domain record linkage",
        ),
        "source_key": "linked_products_rule",
        "detail_keys": (
            ("lens_vs_object_rule", "Lens vs object rule"),
            ("worked_edge_cases", "Worked edge cases"),
        ),
    },
    {
        "name": "Collection method",
        "values": ("Survey", "Administrative"),
        "source_key": "dataset_collection_method_rule",
        "detail_keys": (
            ("edge_case_rule", "Edge-case rule"),
            ("worked_edge_cases", "Worked edge cases"),
        ),
    },
    {
        "name": "Temporal structure",
        "values": ("Cross-sectional", "Longitudinal"),
        "source_key": "dataset_temporal_structure_rule",
        "detail_keys": (
            ("construction_rule", "Construction rule"),
            ("aggregate_indicator_limitation", "Aggregate-indicator limitation"),
            ("retired_category_note", "Retired category note"),
            ("worked_edge_cases", "Worked edge cases"),
        ),
    },
    {
        "name": "Unit of observation",
        "values": ("Individual", "Household", "Business", "Area"),
        "source_key": "dataset_unit_rule",
        "detail_keys": (
            ("worked_edge_cases", "Worked edge cases"),
            ("aggregate_indicator_limitation", "Aggregate-indicator limitation"),
            ("cross_facet_consistency_note", "Cross-facet consistency note"),
        ),
    },
    {
        "name": "Researcher sector",
        "values": ("Academic", "Government", "Third-sector", "Commercial"),
        "source_key": "researcher_sector_rule",
        "detail_keys": (
            ("priority_procedure", "Classification guidance"),
            ("worked_edge_cases", "Worked edge cases"),
        ),
    },
)


def _find_reference_path() -> Path:
    here = Path(__file__).resolve()
    for directory in here.parents:
        candidate = directory / "analysis" / REFERENCE_FILENAME
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"{REFERENCE_FILENAME} not found in any parent of {here}")


def _flatten(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _load_reference() -> dict[str, Any]:
    with _find_reference_path().open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise RuntimeError(f"{REFERENCE_FILENAME} is malformed")
    return data


def _detail_item(block: dict[str, Any], key: str, title: str) -> dict[str, Any] | None:
    value = block.get(key)
    if value is None:
        return None
    if isinstance(value, list):
        content: str | list[str] = [_flatten(item) for item in value if _flatten(item)]
    else:
        content = _flatten(value)
    if not content:
        return None
    return {"title": title, "content": content}


def deterministic_facets() -> list[dict[str, Any]]:
    reference = _load_reference()
    facets: list[dict[str, Any]] = []
    for config in FACET_CONFIG:
        block = reference.get(config["source_key"])
        if not isinstance(block, dict):
            raise RuntimeError(f"{REFERENCE_FILENAME} is missing {config['source_key']}")
        rule = _flatten(block.get("rule"))
        if not rule:
            raise RuntimeError(f"{REFERENCE_FILENAME} {config['source_key']} is missing rule")
        details = [
            detail
            for key, title in config["detail_keys"]
            if (detail := _detail_item(block, key, title)) is not None
        ]
        facets.append({
            "name": config["name"],
            "values": list(config["values"]),
            "rule": rule,
            "details": details,
        })
    return facets


def meta_principle() -> str:
    return _flatten(_load_reference().get("meta_principle"))
