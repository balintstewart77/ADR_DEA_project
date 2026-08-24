"""Register-sufficiency distributions, subsets, and Wilson intervals."""

from __future__ import annotations

from collections import Counter

from analysis.validation.intervals import wilson_interval

from .config import CODERS
from .panels import StageAData


SUFFICIENCY_LABELS = {1: "Sufficient", 2: "Partially sufficient", 3: "Insufficient"}
SPLIT = "No majority / split judgement"


def _record_codes(data: StageAData, population: str) -> dict[str, tuple[int, int, int]]:
    rows = data.responses[data.responses["population"] == population]
    output: dict[str, tuple[int, int, int]] = {}
    for record_id, group in rows.groupby("record_id"):
        by = {row["coder"]: row["sufficiency"] for row in group.to_dict("records")}
        if set(by) == set(CODERS) and all(by[coder] in SUFFICIENCY_LABELS for coder in CODERS):
            output[record_id] = tuple(int(by[coder]) for coder in CODERS)
    return output


def majority_category(values: tuple[int, int, int], labels: dict[int, str]) -> str:
    counts = Counter(values)
    code, count = counts.most_common(1)[0]
    return labels[code] if count >= 2 else SPLIT


def derive_sufficiency_subsets(data: StageAData) -> dict[str, frozenset[str]]:
    ratings = _record_codes(data, "baseline")
    broad = frozenset(record_id for record_id, values in ratings.items() if sum(value in (1, 2) for value in values) >= 2)
    strict = frozenset(record_id for record_id, values in ratings.items() if sum(value == 1 for value in values) >= 2)
    return {"broad": broad, "strict": strict}


def summarise_sufficiency(data: StageAData) -> dict[str, list[dict[str, object]]]:
    response_rows: list[dict[str, object]] = []
    record_rows: list[dict[str, object]] = []
    subset_rows: list[dict[str, object]] = []
    for population in ("baseline", "hard_case"):
        responses = data.responses[data.responses["population"] == population]
        for coder in ("all", *CODERS):
            selected = responses if coder == "all" else responses[responses["coder"] == coder]
            denominator = int(selected["sufficiency"].isin(SUFFICIENCY_LABELS).sum())
            for code, label in SUFFICIENCY_LABELS.items():
                count = int((selected["sufficiency"] == code).sum())
                response_rows.append({
                    "population": population, "coder": coder, "category": label,
                    "count": count, "denominator": denominator,
                    "proportion": count / denominator if denominator else None,
                })
        record_codes = _record_codes(data, population)
        majorities = Counter(majority_category(values, SUFFICIENCY_LABELS) for values in record_codes.values())
        for category in (*SUFFICIENCY_LABELS.values(), SPLIT):
            count = majorities[category]
            record_rows.append({
                "population": population, "category": category, "count": count,
                "denominator": len(record_codes), "proportion": count / len(record_codes),
            })
        for subset, predicate in (
            ("broad_register_usable", lambda values: sum(v in (1, 2) for v in values) >= 2),
            ("strict_register_sufficient", lambda values: sum(v == 1 for v in values) >= 2),
        ):
            count = sum(predicate(values) for values in record_codes.values())
            interval = wilson_interval(count, len(record_codes)) if population == "baseline" else None
            subset_rows.append({
                "population": population, "subset": subset, "count": count,
                "denominator": len(record_codes), "proportion": count / len(record_codes),
                "ci_method": "Wilson score 95%" if interval else "not applied (diagnostic sample)",
                "ci_lower": interval.lower if interval else None,
                "ci_upper": interval.upper if interval else None,
            })
    return {"responses": response_rows, "records": record_rows, "subsets": subset_rows}
