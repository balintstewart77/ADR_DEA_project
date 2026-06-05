"""Dashboard-side reader for the taxonomy data dictionary.

The classifier (``analysis/llm_theme_analysis_v3.py``) and the dashboard must
present the same label set. Both derive it from ``taxonomy_data_dictionary.yaml``
so the two cannot drift apart on the next ontology change. This module is kept
dependency-light (no anthropic) so it can be imported by the dashboard runtime.
"""

from __future__ import annotations

from pathlib import Path

import yaml

TAXONOMY_FILENAME = "taxonomy_data_dictionary.yaml"

LAYER_A_DOMAIN = "Layer A -- domain"
LAYER_C_PURPOSE = "Layer C -- purpose"
LAYER_CROSS_CUTTING_TAG = "Cross-cutting tag"


def _find_taxonomy_path() -> Path:
    here = Path(__file__).resolve()
    for directory in here.parents:
        candidate = directory / TAXONOMY_FILENAME
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"{TAXONOMY_FILENAME} not found in any parent of {here}")


def _flatten(value: object) -> str:
    """Collapse YAML-folded whitespace without changing wording."""
    return " ".join(str(value or "").split()).strip()


def _load() -> dict:
    with _find_taxonomy_path().open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or not isinstance(data.get("categories"), list):
        raise RuntimeError(f"{TAXONOMY_FILENAME} is malformed (missing categories list)")
    return data


_DATA = _load()
_META = _DATA.get("metadata") if isinstance(_DATA.get("metadata"), dict) else {}

DICTIONARY_VERSION = _flatten(_META.get("dictionary_version")) or "unknown"
ONTOLOGY_VERSION = _flatten(_META.get("documents_ontology_version"))


def _is_active(category: dict, layer: str) -> bool:
    """Match the classifier's in-prompt filter so labels stay in lockstep."""
    status = _flatten(category.get("status")).lower()
    return (
        category.get("layer") == layer
        and category.get("include_in_prompt") is True
        and not status.startswith("removed")
    )


def _categories(layer: str) -> list[dict]:
    return [c for c in _DATA["categories"] if isinstance(c, dict) and _is_active(c, layer)]


def labels_for(layer: str) -> list[str]:
    return [label for c in _categories(layer) if (label := _flatten(c.get("label")))]


def category_rows(layer: str) -> list[tuple[str, str]]:
    """Return ``(label, one-line definition)`` pairs for methodology tables."""
    rows = []
    for c in _categories(layer):
        label = _flatten(c.get("label"))
        if label:
            rows.append((label, _flatten(c.get("definition"))))
    return rows


DOMAIN_LABELS = labels_for(LAYER_A_DOMAIN)
PURPOSE_LABELS = labels_for(LAYER_C_PURPOSE)
TAG_LABELS = labels_for(LAYER_CROSS_CUTTING_TAG)
