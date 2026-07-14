"""Deterministic, offline Fable/GPT-5.5 comparison primitives."""

from __future__ import annotations

import pandas as pd

from analysis import llm_theme_analysis_v3 as clf


COVID_TAG = "COVID-19 & Pandemic"
EQUITY_TAG = "Demographic disparities / equity tag"
CANONICAL_TAGS = frozenset(clf.CROSS_CUTTING_TAGS)


class ComparisonError(ValueError):
    """Raised when deterministic comparison inputs are malformed or incompatible."""


def _require_frozen_tag_vocabulary() -> None:
    expected = frozenset({COVID_TAG, EQUITY_TAG})
    if CANONICAL_TAGS != expected:
        raise ComparisonError(
            "Frozen cross-cutting tag vocabulary drifted: "
            f"expected {sorted(expected)!r}, found {sorted(CANONICAL_TAGS)!r}"
        )


def split_label_set(value: object, *, field: str, allowed: frozenset[str] | None = None) -> set[str]:
    """Parse a semicolon-delimited field without changing any labels."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return set()
    text = str(value)
    if not text.strip():
        return set()
    values = [item.strip() for item in text.split(";") if item.strip()]
    labels = set(values)
    if len(labels) != len(values):
        raise ComparisonError(f"Duplicate {field} label in one record: {values!r}")
    if allowed is not None:
        unknown = labels - allowed
        if unknown:
            raise ComparisonError(f"Unknown {field} label(s): {sorted(unknown)!r}")
    return labels


def jaccard(left: set[str], right: set[str], *, field: str) -> float:
    union = left | right
    if not union:
        raise ComparisonError(f"Empty {field} label sets have no declared Jaccard convention")
    return len(left & right) / len(union)


def _require_clean_ids(frame: pd.DataFrame, source: str) -> None:
    if "Record ID" not in frame.columns:
        raise ComparisonError(f"{source} lacks Record ID")
    ids = frame["Record ID"].astype(str)
    invalid = [item for item in ids if not item or item != item.strip() or any(ord(c) <= 31 or ord(c) == 127 or c == "\u00a0" for c in item)]
    if invalid:
        raise ComparisonError(f"{source} has non-canonical Record ID(s): {invalid[:5]!r}")
    duplicated = ids[ids.duplicated()].tolist()
    if duplicated:
        raise ComparisonError(f"{source} has duplicate Record ID(s): {duplicated[:5]!r}")


def build_comparison(fable: pd.DataFrame, gpt: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build full and domain/purpose-disagreement comparison frames offline."""
    _require_frozen_tag_vocabulary()
    _require_clean_ids(fable, "Fable input")
    _require_clean_ids(gpt, "GPT input")
    required_fable = {"Project ID", "Title", "Record ID", "substantive_domains", "analytical_purpose", "cross_cutting_tags", "rationale"}
    required_gpt = {"Record ID", "gpt_status", "substantive_domains", "analytical_purpose", "cross_cutting_tags", "rationale", "validation_error"}
    if missing := required_fable - set(fable.columns):
        raise ComparisonError(f"Fable input missing columns: {sorted(missing)!r}")
    if missing := required_gpt - set(gpt.columns):
        raise ComparisonError(f"GPT input missing columns: {sorted(missing)!r}")
    merged = fable.merge(gpt, on="Record ID", suffixes=("_fable", "_gpt"), how="outer", indicator=True)
    if not (merged["_merge"] == "both").all():
        bad = merged.loc[merged["_merge"] != "both", ["Record ID", "_merge"]].to_dict("records")
        raise ComparisonError(f"Fable/GPT Record ID mismatch: {bad[:10]!r}")

    rows: list[dict[str, object]] = []
    stratum_rows: list[dict[str, object]] = []
    for _, row in merged.iterrows():
        f_domains = split_label_set(row["substantive_domains_fable"], field="Fable domain")
        g_domains = split_label_set(row["substantive_domains_gpt"], field="GPT domain")
        f_purposes = split_label_set(row["analytical_purpose_fable"], field="Fable purpose")
        g_purposes = split_label_set(row["analytical_purpose_gpt"], field="GPT purpose")
        f_tags = split_label_set(row["cross_cutting_tags_fable"], field="Fable tag", allowed=CANONICAL_TAGS)
        g_tags = split_label_set(row["cross_cutting_tags_gpt"], field="GPT tag", allowed=CANONICAL_TAGS)
        domains_exact = f_domains == g_domains
        purposes_exact = f_purposes == g_purposes
        covid_match = (COVID_TAG in f_tags) == (COVID_TAG in g_tags)
        disparities_match = (EQUITY_TAG in f_tags) == (EQUITY_TAG in g_tags)
        tag_set_match = covid_match and disparities_match
        if tag_set_match != (f_tags == g_tags):
            raise ComparisonError(f"Internal tag comparison inconsistency for {row['Record ID']!r}")
        disagree = not domains_exact or not purposes_exact
        tag_only = domains_exact and purposes_exact and not tag_set_match
        record: dict[str, object] = {
            "Record ID": row["Record ID"],
            "Project ID": row.get("Project ID_fable", ""),
            "Title": row.get("Title_fable", ""),
            "gpt_status": row["gpt_status"],
            "domains_exact_match": bool(domains_exact),
            "domains_jaccard": jaccard(f_domains, g_domains, field="domain"),
            "purposes_exact_match": bool(purposes_exact),
            "purposes_jaccard": jaccard(f_purposes, g_purposes, field="purpose"),
            "covid_tag_match": bool(covid_match),
            "disparities_tag_match": bool(disparities_match),
            "tag_set_match": bool(tag_set_match),
            # Retained for downstream compatibility; its semantics are the two-facet conjunction.
            "any_tag_set_match": bool(tag_set_match),
            "tag_only_disagreement": bool(tag_only),
            "DISAGREE": bool(disagree),
            "fable_domains": row["substantive_domains_fable"],
            "gpt_domains": row["substantive_domains_gpt"],
            "fable_purposes": row["analytical_purpose_fable"],
            "gpt_purposes": row["analytical_purpose_gpt"],
            "fable_tags": row["cross_cutting_tags_fable"],
            "gpt_tags": row["cross_cutting_tags_gpt"],
            "fable_rationale": row.get("rationale_fable", ""),
            "gpt_rationale": row.get("rationale_gpt", ""),
            "gpt_validation_error": row.get("validation_error", ""),
        }
        rows.append(record)
        if disagree:
            stratum = dict(record)
            stratum["disagreement_layer"] = (
                "both" if not domains_exact and not purposes_exact
                else "domains-only" if not domains_exact
                else "purposes-only"
            )
            stratum_rows.append(stratum)
    comparison = pd.DataFrame(rows).sort_values("Record ID").reset_index(drop=True)
    if stratum_rows:
        stratum = pd.DataFrame(stratum_rows).sort_values(["disagreement_layer", "Record ID"]).reset_index(drop=True)
    else:
        stratum = pd.DataFrame(columns=[*comparison.columns, "disagreement_layer"])
    return comparison, stratum


def disagreement_counts(comparison: pd.DataFrame, stratum: pd.DataFrame) -> dict[str, int]:
    """Return deterministic domain/purpose stratum and tag-disagreement counts."""
    if not comparison["tag_set_match"].eq(comparison["any_tag_set_match"]).all():
        raise ComparisonError("tag_set_match and any_tag_set_match are inconsistent")
    return {
        "total_disagreement": int(len(stratum)),
        "domain_only": int((stratum["disagreement_layer"] == "domains-only").sum()),
        "purpose_only": int((stratum["disagreement_layer"] == "purposes-only").sum()),
        "both": int((stratum["disagreement_layer"] == "both").sum()),
        "tag_disagreement_alongside_domain_or_purpose": int((~stratum["tag_set_match"]).sum()),
        "tag_only_outside_domain_purpose_frame": int(comparison["tag_only_disagreement"].sum()),
    }
