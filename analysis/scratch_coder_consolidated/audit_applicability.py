"""Fixed-evidence applicability checks for the 2026-09-14 independent audit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .preflight import Fatal, PACKAGE, ROOT

BASELINE_PATH = PACKAGE / "audit_baseline.json"


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def analytical_payload(metadata):
    """Return the fixed audit-relevant content, excluding volatile rendering facts."""
    fields = ("result_items", "cell_lineage", "source_files", "unresolved_items", "supplement", "source_run_metadata")
    try:
        payload = {"schema_version": 1, **{field: metadata[field] for field in fields}}
        # `Sources.unchanged()` appends read-after-validation facts. They are
        # useful current-generation provenance but do not change source identity.
        payload["source_files"] = {
            path: {key: record[key] for key in ("sha256", "bytes")}
            for path, record in payload["source_files"].items()
        }
        return payload
    except KeyError as exc:
        raise Fatal(f"Audit applicability content is missing required field: {exc.args[0]}") from exc


def content_sha256(metadata):
    return hashlib.sha256(_json_bytes(analytical_payload(metadata))).hexdigest()


def load_baseline(path=BASELINE_PATH):
    try:
        baseline = json.loads(Path(path).read_text())
    except FileNotFoundError as exc:
        raise Fatal("Audit applicability baseline is missing") from exc
    if baseline.get("schema_version") != 1:
        raise Fatal("Unsupported audit applicability baseline schema")
    return baseline


def validate(metadata, *, baseline_path=BASELINE_PATH, root=ROOT):
    """Fail closed if audit evidence or audited analytical content no longer matches."""
    baseline = load_baseline(baseline_path)
    evidence = baseline["audit_evidence"]
    for relative, expected in evidence["files"].items():
        path = Path(root) / evidence["directory"] / relative
        if not path.is_file() or path.is_symlink():
            raise Fatal(f"Audit applicability evidence is missing: {path}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise Fatal(f"Audit applicability evidence hash mismatch: {path}")
    observed = content_sha256(metadata)
    expected = baseline["analytical_content"]["sha256"]
    if observed != expected:
        raise Fatal("Audit applicability requires review: current analytical content differs from the fixed audited baseline")
    counts = baseline["analytical_content"]["counts"]
    for field, expected_count in counts.items():
        if len(metadata[field]) != expected_count:
            raise Fatal(f"Audit applicability content count differs for {field}")
    return {
        "audited_snapshot": baseline["audited_snapshot"],
        "analytical_content": {**baseline["analytical_content"], "current_matches_fixed_baseline": True},
        "audit_evidence": evidence,
    }
