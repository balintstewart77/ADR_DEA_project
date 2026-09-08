"""Read and apply the authorised baseline Wilson interval supplement."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from .preflight import Fatal, ROOT, sha

SELECTED_RANGES = ((53, 61), (75, 77), (90, 101), (118, 122), (135, 138), (146, 149))
SELECTED_IDS = tuple(f"WSA{i:04d}" for start, end in SELECTED_RANGES for i in range(start, end + 1))


class WilsonSupplement:
    """A validated supplement whose rows can be joined once to report items."""

    def __init__(self, directory: Path, sources):
        self.s = sources
        self.directory = directory.resolve()
        if not self.directory.is_relative_to(ROOT) or "preregistration_restricted" in self.directory.parts:
            raise Fatal("Wilson supplement must be an unrestricted repository directory")
        if not self.directory.name.startswith("outputs_validation_wilson_baseline_"):
            raise Fatal("Wilson supplement directory does not use the expected dated naming convention")
        expected = {"wilson_intervals.csv", "reused_intervals.json", "methods_wilson_baseline.md", "run_metadata.json"}
        actual = {path.name for path in self.directory.iterdir() if path.is_file()}
        if actual != expected:
            raise Fatal(f"Wilson supplement file set mismatch: expected={sorted(expected)} actual={sorted(actual)}")
        self.relative_directory = self.directory.relative_to(ROOT).as_posix()
        self.metadata = self._json("run_metadata.json")
        self.reused = self._json("reused_intervals.json")
        self.rows = list(csv.DictReader(io.StringIO(self._read("wilson_intervals.csv").decode("utf-8-sig"))))
        self._validate_artifact()

    def _read(self, name: str) -> bytes:
        path = self.directory / name
        if path.is_symlink():
            raise Fatal(f"Supplement files may not be symlinks: {path}")
        return path.read_bytes()

    def _json(self, name: str):
        return json.loads(self._read(name))

    def _validate_artifact(self):
        if self.metadata.get("status") != "complete" or self.metadata.get("selection_count") != 37:
            raise Fatal("Supplement metadata is not a complete 37-row run")
        for name in ("wilson_intervals.csv", "reused_intervals.json", "methods_wilson_baseline.md"):
            recorded = self.metadata.get("files", {}).get(name, {})
            content = self._read(name)
            if recorded.get("sha256") != sha(content) or recorded.get("bytes") != len(content):
                raise Fatal(f"Supplement file hash/size mismatch: {name}")
        identifiers = [row["candidate_id"] for row in self.rows]
        if len(identifiers) != 37 or set(identifiers) != set(SELECTED_IDS) or len(identifiers) != len(set(identifiers)):
            raise Fatal("Supplement interval identifiers do not equal the authorised 37-row selection")
        targets = set()
        for row in self.rows:
            try:
                key = json.loads(row["source_key_json"])
            except json.JSONDecodeError as exc:
                raise Fatal(f"Invalid supplement source key: {row['candidate_id']}") from exc
            identity = (row["source_path"], json.dumps(key, sort_keys=True), row["metric"])
            if identity in targets:
                raise Fatal(f"Duplicate supplement target: {identity}")
            targets.add(identity)
            if row["population"] != "baseline" or row["observational_unit"] not in ("record_binary", "individual_coder_binary"):
                raise Fatal(f"Unapproved supplement population/unit: {row['candidate_id']}")
            if row["original_denominator"] != "150" or row["metric"] != "proportion":
                raise Fatal(f"Unapproved supplement denominator/metric: {row['candidate_id']}")
            source_record = self.s.files.get(row["source_path"])
            if source_record is None or source_record["sha256"] != row["source_sha256"]:
                raise Fatal(f"Supplement/source hash mismatch: {row['candidate_id']}")
            name = Path(row["source_path"]).stem
            source_row = self.s.lookup(name, **key)
            if (source_row["count"], source_row["denominator"], source_row["proportion"]) != (
                    row["original_numerator"], row["original_denominator"], row["original_proportion"]):
                raise Fatal(f"Supplement/source analytical cell mismatch: {row['candidate_id']}")
            if row["method"] != "Wilson score" or row["confidence_level"] != "0.95" or row["continuity_correction"] != "False":
                raise Fatal(f"Unsupported supplement method annotation: {row['candidate_id']}")
            lower, upper, point = float(row["ci_lower"]), float(row["ci_upper"]), float(row["original_proportion"])
            if not 0.0 <= lower <= point <= upper <= 1.0:
                raise Fatal(f"Invalid supplement interval ordering: {row['candidate_id']}")
        source_records = self.metadata.get("source_files", {})
        for path, record in source_records.items():
            current = self.s.files.get(path)
            if current is None or current["sha256"] != record.get("sha256_before") or record.get("unchanged") is not True:
                raise Fatal(f"Supplement input identity is not verified against consolidation sources: {path}")
        if self.reused.get("originating_interval_count") != 2 or self.reused.get("report_entry_count") != 3:
            raise Fatal("Reused-interval inventory must contain two origins and three report entries")

    def _match(self, report, source_path: str, key: dict, metric: str):
        matches = [item for item in report.items if item["source_path"] == source_path and
                   item["source_key"] == key and item["metric"] == metric]
        if len(matches) != 1:
            raise Fatal(f"Supplement target must match exactly one report item: {source_path}/{key}/{metric}; found {len(matches)}")
        return matches[0]

    def _lineage(self, report, item, *, role: str, value: str, candidate_id: str, column: str,
                 source_path: str, source_key: dict, lineage_type: str, origin: str):
        report.lineage.append({
            "lineage_type": lineage_type,
            "table_id": item["table_id"],
            "result_id": item["result_id"],
            "metric": item["metric"],
            "document_cell_role": role,
            "source_path": source_path,
            "row_selection_key": source_key,
            "column": column,
            "raw_value": value,
            "displayed_value": value,
            "displayed_status": "reported",
            "retained_raw_status": item["source_status"],
            "candidate_id": candidate_id,
            "interval_origin": origin,
        })

    def apply(self, report):
        if len(report.s.unresolved) != 69 or len({item["id"] for item in report.s.unresolved}) != 69:
            raise Fatal("Generated original-source unresolved inventory is not the expected 69 unique entries")
        original_unresolved = json.loads(json.dumps(report.s.unresolved))
        applied = []
        for row in self.rows:
            key = json.loads(row["source_key_json"])
            item = self._match(report, row["source_path"], key, row["metric"])
            if item["interval_status"] != "unavailable_in_source" or item["displayed_lower"] or item["displayed_upper"]:
                raise Fatal(f"Supplement attempted to overwrite an existing reported interval: {row['candidate_id']}")
            item["original_interval_status"] = item["interval_status"]
            item["original_interval_method"] = item["interval_method"]
            item["interval_status"] = "reported"
            item["interval_method"] = "wilson_score"
            item["confidence_level"] = "95%"
            item["displayed_lower"] = row["ci_lower"]
            item["displayed_upper"] = row["ci_upper"]
            item["status_reason"].append("Original source exported no interval columns; displayed bounds come from the dated Wilson supplement")
            item["policy_source"].append(self.relative_directory + "/methods_wilson_baseline.md")
            item["supplement_interval"] = {
                "candidate_id": row["candidate_id"], "origin": "newly_calculated_supplementary_wilson",
                "source_path": self.relative_directory + "/wilson_intervals.csv",
                "calculation_timestamp_utc": row["calculation_timestamp_utc"],
                "original_interval_status": "unavailable_in_source",
            }
            for role, column in (("interval_lower", "ci_lower"), ("interval_upper", "ci_upper")):
                self._lineage(report, item, role=role, value=row[column], candidate_id=row["candidate_id"], column=column,
                              source_path=self.relative_directory + "/wilson_intervals.csv", source_key={"candidate_id": row["candidate_id"]},
                              lineage_type="supplement_interval_cell", origin="newly_calculated_supplementary_wilson")
            applied.append(row["candidate_id"])

        entries = {entry["candidate_id"]: entry for entry in self.reused["report_entries"]}
        if set(entries) != {"WSA0074", "WSA0082", "WSA0083"}:
            raise Fatal("Unexpected reused-interval report-entry identifiers")
        reuse = entries["WSA0074"]
        target = reuse["target"]
        item = self._match(report, target["source_path"], target["source_key"], target["metric"])
        if item["interval_status"] != "unavailable_in_source" or item["displayed_lower"] or item["displayed_upper"]:
            raise Fatal("WSA0074 reuse attempted to overwrite a reported interval")
        origin = self.reused["originating_intervals"][reuse["origin"]]
        origin_item = self._match(report, origin["source_path"], origin["source_key"], origin["metric"])
        if (origin_item["displayed_estimate"], origin_item["displayed_lower"], origin_item["displayed_upper"]) != (
                target["proportion"], reuse["lower"], reuse["upper"]):
            raise Fatal("WSA0074/WSA0083 report equivalence or originating interval mismatch")
        item["original_interval_status"] = item["interval_status"]
        item["original_interval_method"] = item["interval_method"]
        item["interval_status"] = "reported"
        item["interval_method"] = "wilson_score"
        item["confidence_level"] = "95%"
        item["displayed_lower"], item["displayed_upper"] = reuse["lower"], reuse["upper"]
        item["status_reason"].append("Original distribution row exported no interval; bounds are reused from the verified equivalent strict-sufficiency result")
        item["policy_source"].append(self.relative_directory + "/reused_intervals.json")
        item["supplement_interval"] = {
            "candidate_id": "WSA0074", "origin": "reused_verified_equivalent_result",
            "source_path": origin["source_path"], "origin_candidate_id": reuse["origin"],
            "original_interval_status": "unavailable_in_source",
        }
        for role, column, value in (("interval_lower", "ci_lower", reuse["lower"]), ("interval_upper", "ci_upper", reuse["upper"])):
            self._lineage(report, item, role=role, value=value, candidate_id="WSA0074", column=column,
                          source_path=origin["source_path"], source_key=origin["source_key"],
                          lineage_type="reused_interval_cell", origin="reused_verified_equivalent_result")

        for identifier in ("WSA0082", "WSA0083"):
            entry = entries[identifier]
            target = entry["target"]
            retained = self._match(report, target["source_path"], target["source_key"], target["metric"])
            if (retained["displayed_lower"], retained["displayed_upper"], retained["interval_status"]) != (
                    target["lower"], target["upper"], "reported"):
                raise Fatal(f"Existing interval was not retained exactly: {identifier}")

        if len(applied) != 37 or report.s.unresolved != original_unresolved:
            raise Fatal("Supplement coverage or original unresolved-entry preservation failed")
        report.meta["supplement"] = {
            "directory": self.relative_directory,
            "calculation_timestamp_utc": self.metadata["calculation_timestamp_utc"],
            "new_interval_rows": 37,
            "new_interval_candidate_ids": applied,
            "originating_existing_intervals_retained": ["WSA0082", "WSA0083"],
            "equivalent_result_reuse": "WSA0074 from WSA0083",
            "original_unresolved_entries_retained": 69,
            "source_hashes_verified": True,
            "join_cardinality": "one_to_one",
            "files": {name: {"sha256": sha(self._read(name)), "bytes": len(self._read(name))} for name in
                      ("wilson_intervals.csv", "reused_intervals.json", "methods_wilson_baseline.md", "run_metadata.json")},
        }
