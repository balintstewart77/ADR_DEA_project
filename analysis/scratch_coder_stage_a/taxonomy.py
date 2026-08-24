"""Aggregate taxonomy-fit, issue, unclear, and coherence diagnostics."""

from __future__ import annotations

from collections import Counter

from .config import CODERS
from .panels import StageAData
from .sufficiency import SPLIT, majority_category


FIT_LABELS = {
    1: "Fit",
    2: "Partial Fit",
    3: "No Fit",
    4: "Cannot assess from register entry",
}
ISSUE_LABELS = {
    1: "Missing or inadequately represented category",
    2: "Ambiguous or overlapping category boundaries",
    5: "Other taxonomy problem",
}
CONFIDENCE_LABELS = {1: "High", 2: "Medium", 3: "Low"}
SUFFICIENCY_LABELS = {1: "Sufficient", 2: "Partially sufficient", 3: "Insufficient"}
UNCLEAR = "Unclear from Register Entry"


def _fit_record_codes(data: StageAData, population: str) -> dict[str, tuple[int, int, int]]:
    rows = data.responses[data.responses["population"] == population]
    output = {}
    for record_id, group in rows.groupby("record_id"):
        by = {row["coder"]: row["taxonomy_fit"] for row in group.to_dict("records")}
        if set(by) == set(CODERS) and all(by[coder] in FIT_LABELS for coder in CODERS):
            output[record_id] = tuple(int(by[coder]) for coder in CODERS)
    return output


def summarise_taxonomy_fit(data: StageAData) -> dict[str, list[dict[str, object]]]:
    responses_out: list[dict[str, object]] = []
    records_out: list[dict[str, object]] = []
    issues_out: list[dict[str, object]] = []
    unclear_out: list[dict[str, object]] = []
    coherence_out: list[dict[str, object]] = []
    for population in ("baseline", "hard_case"):
        responses = data.responses[data.responses["population"] == population]
        for coder in ("all", *CODERS):
            selected = responses if coder == "all" else responses[responses["coder"] == coder]
            denominator = int(selected["taxonomy_fit"].isin(FIT_LABELS).sum())
            for code, label in FIT_LABELS.items():
                count = int((selected["taxonomy_fit"] == code).sum())
                responses_out.append({
                    "population": population, "coder": coder, "category": label,
                    "count": count, "denominator": denominator,
                    "proportion": count / denominator if denominator else None,
                })
        record_codes = _fit_record_codes(data, population)
        majorities = Counter(majority_category(values, FIT_LABELS) for values in record_codes.values())
        for category in (*FIT_LABELS.values(), SPLIT):
            count = majorities[category]
            records_out.append({
                "population": population, "category": category, "count": count,
                "denominator": len(record_codes), "proportion": count / len(record_codes),
            })

        applicable = responses[responses["taxonomy_fit"].isin((2, 3))]
        denominator = len(applicable)
        for code, label in ISSUE_LABELS.items():
            count = sum(code in issues for issues in applicable["taxonomy_issues"])
            issues_out.append({
                "population": population, "issue": label, "count": count,
                "applicable_denominator": denominator,
                "proportion": count / denominator if denominator else None,
                "note": "Percentages may sum to more than 100%.",
            })

        for dimension, field in (("Research Domains", "domains"), ("Analytical Purposes", "purposes")):
            valid = responses[responses[field].notna()]
            uses = valid[field].map(lambda labels: UNCLEAR in labels)
            per_record = valid.assign(_unclear=uses).groupby("record_id")["_unclear"].sum()
            measures = {
                "coder_response_uses": (int(uses.sum()), len(valid)),
                "records_with_1_of_3": (int((per_record == 1).sum()), len(per_record)),
                "records_with_2_of_3": (int((per_record == 2).sum()), len(per_record)),
                "records_with_3_of_3": (int((per_record == 3).sum()), len(per_record)),
                "records_with_majority_use": (int((per_record >= 2).sum()), len(per_record)),
            }
            for measure, (count, denom) in measures.items():
                unclear_out.append({
                    "population": population, "dimension": dimension, "section": "frequency",
                    "measure": measure, "category": "Unclear", "count": count,
                    "denominator": denom, "proportion": count / denom if denom else None,
                })
            working = valid.assign(_unclear=uses)
            for construct, source, labels in (
                ("sufficiency", "sufficiency", SUFFICIENCY_LABELS),
                ("confidence", "confidence", CONFIDENCE_LABELS),
            ):
                for code, label in labels.items():
                    category_rows = working[working[source] == code]
                    denom = len(category_rows)
                    count = int(category_rows["_unclear"].sum())
                    unclear_out.append({
                        "population": population, "dimension": dimension,
                        "section": f"response_crosstab_{construct}", "measure": "unclear_use",
                        "category": label, "count": count, "denominator": denom,
                        "proportion": count / denom if denom else None,
                    })

        cannot = responses[responses["taxonomy_fit"] == 4]
        for construct, source, labels in (
            ("sufficiency", "sufficiency", SUFFICIENCY_LABELS),
            ("confidence", "confidence", CONFIDENCE_LABELS),
        ):
            for code, label in labels.items():
                count = int((cannot[source] == code).sum())
                coherence_out.append({
                    "population": population, "analysis": f"cannot_assess_by_{construct}",
                    "category": label, "count": count, "denominator": len(cannot),
                    "proportion": count / len(cannot) if len(cannot) else None,
                })
        coherent = int((cannot["sufficiency"] != 1).sum())
        incoherent = int((cannot["sufficiency"] == 1).sum())
        for category, count in (("validator_coherent", coherent), ("validator_incoherent", incoherent)):
            coherence_out.append({
                "population": population, "analysis": "candidate_0.7_cannot_assess_coherence",
                "category": category, "count": count, "denominator": len(cannot),
                "proportion": count / len(cannot) if len(cannot) else None,
            })
    return {
        "responses": responses_out,
        "records": records_out,
        "issues": issues_out,
        "unclear": unclear_out,
        "coherence": coherence_out,
    }
