"""Export dataset facet audit CSV from register_reference.yaml + parsed register.

Generated snapshot for self-audit; register_reference.yaml remains authoritative.
Regenerable: python -m analysis.export_dataset_facet_audit
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.derive_register_properties import (
    build_indexes,
    load_reference,
    lookup_dataset_record,
    match_linked_products,
    parse_register_entities,
    REFERENCE_PATH,
)
from analysis.register_cleaning import DATA_DIR, load_clean_register

OUTPUT_CSV = Path(__file__).resolve().parent / "outputs" / "dataset_facet_audit_export.csv"

AGGREGATE_INDICATORS = {
    "Consumer Prices Index",
    "Producer Price Index",
    "UK Gross Value Added",
    "Capital Stock Dataset",
}


def _source_fields(record: dict) -> str:
    sources = []
    for key in ("temporal_source", "collection_method_source"):
        val = record.get(key)
        if val and str(val).strip():
            sources.append(str(val).strip())
    return " ; ".join(sources)


def main() -> None:
    reference = load_reference(REFERENCE_PATH)
    indexes = build_indexes(reference)

    df_clean, _, _ = load_clean_register(DATA_DIR, include_quarter_date=True)
    datasets_df, _ = parse_register_entities(df_clean)

    mention_counts: Counter[str] = Counter(datasets_df["dataset"].astype(str))

    all_canonical = sorted(mention_counts.keys())

    linked_product_canonicals: set[str] = set()
    for record in reference.get("linked_products", []):
        linked_product_canonicals.add(record["canonical"])

    rows = []
    for canonical in all_canonical:
        ref_record = lookup_dataset_record(canonical, indexes)
        is_linked = bool(match_linked_products(canonical, indexes))
        is_aggregate = canonical in AGGREGATE_INDICATORS

        if ref_record:
            cm = ref_record.get("collection_method", "")
            ts = ref_record.get("temporal_structure", "")
            uo = ref_record.get("unit_of_observation", "")
            notes = str(ref_record.get("notes", "")).strip()
            source = _source_fields(ref_record)

            has_source = bool(source)
            has_rationale = bool(notes) and notes not in (
                "Business survey.",
                "Business survey",
            )

            if has_source and has_rationale:
                provenance = "evidenced"
            elif has_rationale and not has_source:
                provenance = "rationale_only"
            else:
                provenance = "asserted"
        else:
            cm = ts = uo = notes = source = ""
            provenance = "unclassified"

        rows.append({
            "canonical_dataset": canonical,
            "mention_count": mention_counts[canonical],
            "collection_method": cm,
            "temporal_structure": ts,
            "unit_of_observation": uo,
            "rationale": notes,
            "source": source,
            "provenance_status": provenance,
            "is_linked_product": "yes" if is_linked else "no",
            "is_aggregate_indicator": "yes" if is_aggregate else "no",
        })

    provenance_order = {
        "unclassified": 0,
        "asserted": 1,
        "rationale_only": 2,
        "evidenced": 3,
    }
    rows.sort(
        key=lambda r: (
            provenance_order.get(r["provenance_status"], 99),
            -r["mention_count"],
            r["canonical_dataset"],
        )
    )

    df_out = pd.DataFrame(rows)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    version = reference.get("reference_version", "unknown")
    header_comment = (
        f"# Generated snapshot | source: register_reference.yaml v{version} + parsed register | "
        f"mention_count = dataset mentions (not distinct projects) | NOT a source of truth; regenerable via analysis/export_dataset_facet_audit.py\n"
    )
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        f.write(header_comment)
        df_out.to_csv(f, index=False)

    total = len(df_out)
    bucket_counts = df_out["provenance_status"].value_counts().to_dict()
    print(f"Wrote {OUTPUT_CSV.name}: {total} canonical datasets")
    for status in ("unclassified", "asserted", "rationale_only", "evidenced"):
        print(f"  {status}: {bucket_counts.get(status, 0)}")
    linked_count = int((df_out["is_linked_product"] == "yes").sum())
    agg_count = int((df_out["is_aggregate_indicator"] == "yes").sum())
    print(f"  linked_products: {linked_count}")
    print(f"  aggregate_indicators: {agg_count}")


if __name__ == "__main__":
    main()
