"""Migrate cached classifications after reviewed duplicate-Project-ID rulings.

This is an offline migration: it matches old cache/output entries to the
current cleaned register by the exact classifier prompt fingerprint and never
calls an LLM API.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from analysis import llm_theme_analysis_v3 as clf
from analysis.register_cleaning import load_clean_register


FABLE_DIR = PROJECT_ROOT / "analysis" / "outputs_classified_20260702_fable5"
FABLE_CACHE = FABLE_DIR / "llm_layer_cache.json"
FABLE_META = FABLE_DIR / "run_metadata.json"
GPT_CACHE = PROJECT_ROOT / "analysis" / "outputs" / "gpt55_gpt-5.5_dict-1.0-rc2_llm_layer_cache.json"
AUDIT_PATH = PROJECT_ROOT / "analysis" / "outputs" / "reviewed_duplicate_record_id_migration_audit.csv"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _fingerprint_for_values(title: object, datasets: object) -> str:
    return clf._classification_fingerprint(
        clf._sanitise_prompt_text("" if pd.isna(title) else str(title)),
        clf._summarise_datasets("" if pd.isna(datasets) else str(datasets)),
    )


def _cleaned_register() -> pd.DataFrame:
    df, _stats, _source = load_clean_register(verbose=False)
    df["Record ID"] = df["Record ID"].astype(str)
    df["_fingerprint"] = df.apply(
        lambda row: _fingerprint_for_values(row["Title"], row.get("Datasets Used", "")),
        axis=1,
    )
    return df


def _old_release_rows(csv_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path, encoding="utf-8-sig", dtype=str).fillna("")
    frame["_fingerprint"] = frame.apply(
        lambda row: _fingerprint_for_values(row["Title"], row.get("Datasets Used", "")),
        axis=1,
    )
    return frame


def _build_record_id_mapping(cleaned: pd.DataFrame, old_rows: pd.DataFrame) -> pd.DataFrame:
    old_by_id = old_rows.set_index("Record ID", drop=False)
    used_old_ids: set[str] = set()
    mappings: list[dict[str, Any]] = []
    for _, row in cleaned.iterrows():
        new_id = str(row["Record ID"])
        fingerprint = str(row["_fingerprint"])
        project_id = str(row["Project ID"])

        old_id = ""
        action = ""
        if new_id in old_by_id.index:
            old_row = old_by_id.loc[new_id]
            if isinstance(old_row, pd.DataFrame):
                raise SystemExit(f"Old release has duplicate Record ID {new_id}")
            if str(old_row["_fingerprint"]) != fingerprint:
                raise SystemExit(
                    f"Stable Record ID {new_id} maps to different prompt content; "
                    "explicit migration decision required"
                )
            old_id = new_id
            action = "kept"
        else:
            candidates = old_rows[
                (old_rows["Project ID"].astype(str) == project_id)
                & (old_rows["_fingerprint"].astype(str) == fingerprint)
                & (~old_rows["Record ID"].astype(str).isin(used_old_ids))
            ]
            if len(candidates) != 1:
                raise SystemExit(
                    f"Expected one old row for new {new_id} using Project ID {project_id} "
                    f"and fingerprint {fingerprint}, found {len(candidates)}"
                )
            old_id = str(candidates.iloc[0]["Record ID"])
            action = "rekeyed"

        used_old_ids.add(old_id)
        mappings.append({
            "old_record_id": old_id,
            "new_record_id": new_id,
            "project_id": project_id,
            "title": row["Title"],
            "fingerprint": fingerprint,
            "action": action,
        })

    return pd.DataFrame(mappings)


def _migrate_cache(
    payload: dict[str, Any],
    mapping: pd.DataFrame,
    *,
    source_name: str,
    audit_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    old_entries = payload.get("entries") or {}
    new_entries: dict[str, dict[str, Any]] = {}
    for _, row in mapping.iterrows():
        old_record_id = str(row["old_record_id"])
        record_id = str(row["new_record_id"])
        fingerprint = str(row["fingerprint"])
        entry = old_entries.get(old_record_id)
        if not isinstance(entry, dict):
            raise SystemExit(f"{source_name}: missing old cache entry {old_record_id}")
        if str(entry.get("fingerprint") or "") != fingerprint:
            raise SystemExit(
                f"{source_name}: cache fingerprint mismatch for old {old_record_id} -> {record_id}"
            )
        migrated = dict(entry)
        migrated["fingerprint"] = fingerprint
        new_entries[record_id] = migrated
        audit_rows.append({
            "source": source_name,
            "old_record_id": old_record_id,
            "new_record_id": record_id,
            "project_id": row["project_id"],
            "title": row["title"],
            "fingerprint": fingerprint,
            "action": row["action"],
        })

    migrated_payload = dict(payload)
    migrated_payload["entries"] = new_entries
    return migrated_payload


def _classification_frame_from_cache(cleaned: pd.DataFrame, cache_payload: dict[str, Any]) -> pd.DataFrame:
    rows = cleaned.drop(columns=["_fingerprint"]).copy()
    entries = cache_payload["entries"]
    rows["substantive_domains"] = rows["Record ID"].map(
        lambda record_id: entries[str(record_id)]["substantive_domains"]
    )
    rows["analytical_purpose"] = rows["Record ID"].map(
        lambda record_id: entries[str(record_id)]["analytical_purpose"]
    )
    rows["cross_cutting_tags"] = rows["Record ID"].map(
        lambda record_id: entries[str(record_id)].get("cross_cutting_tags", [])
    )
    rows["rationale"] = rows["Record ID"].map(
        lambda record_id: entries[str(record_id)].get("rationale", "")
    )
    rows["primary_domain"] = rows["substantive_domains"].map(lambda values: values[0] if values else "")
    return rows


def _update_fable_metadata(path: Path, n_projects: int) -> None:
    meta = _read_json(path)
    meta["n_projects"] = n_projects
    meta["final_cache_entries"] = n_projects
    meta["reviewed_duplicate_record_id_migration"] = {
        "status": "applied",
        "audit_csv": str(AUDIT_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "note": "2023/211 duplicate/update collapsed; retained duplicate Project IDs rekeyed by reviewed rulings.",
    }
    _write_json(path, meta)


def main() -> None:
    cleaned = _cleaned_register()
    old_rows = _old_release_rows(FABLE_DIR / "layer_classifications.csv")
    mapping = _build_record_id_mapping(cleaned, old_rows)
    audit_rows: list[dict[str, Any]] = []

    fable_payload = _read_json(FABLE_CACHE)
    fable_payload = _migrate_cache(
        fable_payload,
        mapping,
        source_name="fable",
        audit_rows=audit_rows,
    )
    _write_json(FABLE_CACHE, fable_payload)

    clf_df = _classification_frame_from_cache(cleaned, fable_payload)
    trends = clf.analyse_layers(clf_df)
    summary_path = FABLE_DIR / "layer_summary.txt"
    narrative = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
    clf.save_outputs(clf_df, trends, narrative, str(FABLE_DIR))
    _update_fable_metadata(FABLE_META, len(cleaned))

    if GPT_CACHE.exists():
        gpt_payload = _read_json(GPT_CACHE)
        gpt_payload = _migrate_cache(
            gpt_payload,
            mapping,
            source_name="gpt55",
            audit_rows=audit_rows,
        )
        _write_json(GPT_CACHE, gpt_payload)

    pd.DataFrame(audit_rows).to_csv(AUDIT_PATH, index=False, encoding="utf-8-sig")
    print(f"[done] migrated {len(cleaned)} records")
    print(f"[done] audit: {AUDIT_PATH}")


if __name__ == "__main__":
    main()
