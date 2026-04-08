import os
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher

import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "dashboard"))

from institution_normalisation import parse_institutions  # noqa: E402


OUTPUT_DIR = os.path.join(PROJECT_ROOT, "analysis", "outputs_v3")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "institution_review_candidates.csv")
OUTPUT_MD = os.path.join(OUTPUT_DIR, "institution_review_candidates.md")

CANDIDATE_FILES = [
    "dea_accredited_projects_20260325.csv",
    "dea_accredited_projects.csv",
]
KNOWN_VALID_INSTITUTIONS = {
    "National Centre for Social Research",
    "PwC LLP",
    "ScaleUp Institute",
}

def load_projects() -> pd.DataFrame:
    data_dir = os.path.join(PROJECT_ROOT, "data")
    for name in CANDIDATE_FILES:
        path = os.path.join(data_dir, name)
        if os.path.exists(path):
            df = pd.read_csv(path, encoding="utf-8-sig")
            df["Accreditation Date"] = pd.to_datetime(df["Accreditation Date"], errors="coerce")
            df["Year"] = df["Accreditation Date"].dt.year.fillna(0).astype(int)
            return df
    raise FileNotFoundError("No DEA projects CSV found in data/")


def find_near_duplicates(counts: pd.Series) -> dict[str, list[str]]:
    names = counts.index.tolist()
    groups: dict[str, list[str]] = defaultdict(list)
    for i, left in enumerate(names):
        left_lower = left.lower()
        left_tokens = set(left_lower.replace(",", " ").replace("-", " ").split())
        for right in names[i + 1:]:
            right_lower = right.lower()
            right_tokens = set(right_lower.replace(",", " ").replace("-", " ").split())
            ratio = SequenceMatcher(None, left_lower, right_lower).ratio()
            if ratio < 0.9:
                continue
            token_union = left_tokens | right_tokens
            overlap = (left_tokens & right_tokens)
            jaccard = (len(overlap) / len(token_union)) if token_union else 0.0
            if left_lower in right_lower or right_lower in left_lower or jaccard >= 0.6:
                groups[left].append(right)
    return groups


def reason_flags(name: str, count: int, near_duplicates: dict[str, list[str]]) -> list[str]:
    if name in KNOWN_VALID_INSTITUTIONS:
        return []

    reasons = []
    lower = name.lower()

    if count == 1:
        reasons.append("singleton")
    if name in near_duplicates or any(name in others for others in near_duplicates.values()):
        reasons.append("near-duplicate")
    if ";" in name or "/" in name:
        reasons.append("compound-label")
    if "  " in name:
        reasons.append("double-space")
    if any(fragment in lower for fragment in ["lonfon", "univeristy", "insitute", "edniburgh", "univeraity"]):
        reasons.append("possible-typo")
    if "“" in name or '"' in name:
        reasons.append("stray-quote")
    if re.search(r"[a-z][A-Z]", name):
        reasons.append("possible-glued-name")

    return sorted(set(reasons))


def build_review_table(projects: pd.DataFrame) -> pd.DataFrame:
    parsed = parse_institutions(projects)
    counts = (
        parsed.groupby("institution")["Project ID"]
        .nunique()
        .sort_values(ascending=False)
    )
    near_duplicates = find_near_duplicates(counts)

    raw_lookup = (
        projects[["Project ID", "Researchers"]]
        .drop_duplicates(subset=["Project ID"])
        .set_index("Project ID")["Researchers"]
        .to_dict()
    )

    rows = []
    for institution, count in counts.items():
        reasons = reason_flags(institution, int(count), near_duplicates)
        if not reasons:
            continue

        project_ids = (
            parsed.loc[parsed["institution"] == institution, "Project ID"]
            .drop_duplicates()
            .tolist()
        )
        examples = project_ids[:3]
        example_researchers = " || ".join(
            str(raw_lookup.get(project_id, "")).replace("\r", " ").replace("\n", " | ")
            for project_id in examples
        )
        similar = near_duplicates.get(institution, [])

        rows.append({
            "institution": institution,
            "project_count": int(count),
            "reasons": "; ".join(reasons),
            "similar_labels": " | ".join(similar[:5]),
            "example_project_ids": " | ".join(map(str, examples)),
            "example_researchers": example_researchers,
        })

    review = pd.DataFrame(rows)
    if len(review):
        review = review.sort_values(
            by=["project_count", "institution"],
            ascending=[False, True],
        ).reset_index(drop=True)
    return review


def write_outputs(review: pd.DataFrame) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    review.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    lines = [
        "# Institution Review Candidates",
        "",
        f"Rows flagged for manual review: {len(review)}",
        "",
        "Top candidates by project count:",
        "",
    ]
    preview = review.head(40)
    for _, row in preview.iterrows():
        lines.append(
            f"- {row['institution']} ({row['project_count']} projects) [{row['reasons']}]"
        )
        if row["similar_labels"]:
            lines.append(f"  similar: {row['similar_labels']}")
        if row["example_project_ids"]:
            lines.append(f"  examples: {row['example_project_ids']}")

    with open(OUTPUT_MD, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> None:
    projects = load_projects()
    review = build_review_table(projects)
    write_outputs(review)
    print(f"Wrote {len(review)} review candidates to {OUTPUT_CSV}")
    print(f"Wrote markdown summary to {OUTPUT_MD}")


if __name__ == "__main__":
    main()
