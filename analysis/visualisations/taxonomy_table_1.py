"""Table 1: the labels of the classification taxonomy (dict-1.0-rc2). Pass-4 log P4.81; simplified under P4.82.

Reads ``taxonomy_data_dictionary.yaml``, checked against its committed version in git and against the hash of the frozen
dictionary used in validation (dict-1.0-rc2, SHA-256 7ddbf1bb…, as recorded in the Stage B run metadata). The table
lists the active labels of each layer in dictionary order, with Unclear from Register Entry last, in three columns:
Research Domains, Analytical Purposes and cross-cutting tags. Definitions and rules are not reproduced; they are in the
dictionary itself.

Writes ``analysis/tables/table_1_taxonomy.{md,csv}`` and copies them to ``DEA_paper/tables/`` (both gitignored).
Run from the repository root:  python -m analysis.visualisations.taxonomy_table_1
"""
from __future__ import annotations

import csv
import hashlib
import shutil
import subprocess
import sys
from itertools import zip_longest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_scratch_coder_pass3 as p3  # noqa: E402

DICTIONARY = "taxonomy_data_dictionary.yaml"
FROZEN_SHA256 = "7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de"
SLUG = "table_1_taxonomy"
OUT, PAPER = REPO / "analysis/tables", REPO / "DEA_paper/tables"
UNCLEAR = "Unclear from Register Entry"
LAYERS = (("Layer A -- domain", "Research Domains (one or more)"),
          ("Layer C -- purpose", "Analytical Purposes (one or two)"),
          ("Cross-cutting tag", "Cross-cutting tags (each yes or no)"))
TAG_DISPLAY = {"Demographic disparities / equity tag": "Demographic disparities / equity"}


def committed_bytes(rel: str) -> bytes:
    raw = (REPO / rel).read_bytes()
    blob = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=REPO, capture_output=True, check=True).stdout
    if raw.replace(b"\r\n", b"\n") != blob.replace(b"\r\n", b"\n"):
        raise SystemExit(f"{rel} differs from its committed version")
    return raw


def build() -> tuple[str, list[list[str]]]:
    raw = committed_bytes(DICTIONARY)
    if hashlib.sha256(raw).hexdigest() != FROZEN_SHA256:
        raise SystemExit("Dictionary is not the frozen dict-1.0-rc2 file used in validation")
    dictionary = yaml.safe_load(raw.decode("utf-8"))
    if dictionary["metadata"]["dictionary_version"] != "1.0-rc2":
        raise SystemExit("Unexpected dictionary version")
    live = [c for c in dictionary["categories"]
            if not str(c.get("status", "")).startswith("removed") and c.get("include_in_prompt") is True]
    columns = []
    for layer, _ in LAYERS:
        labels = [TAG_DISPLAY.get(c["label"], c["label"]) for c in live if c["layer"] == layer]
        labels = [lab for lab in labels if lab != UNCLEAR] + [lab for lab in labels if lab == UNCLEAR]
        columns.append(labels)
    counts = [len([lab for lab in col if lab != UNCLEAR]) for col in columns]
    if counts != [11, 7, 2] or any(UNCLEAR not in col for col in columns[:2]):
        raise SystemExit(f"Unexpected label counts {counts}")
    head = [title for _, title in LAYERS]
    body = [list(row) for row in zip_longest(*columns, fillvalue="")]
    return p3.html_table(head, body), [head] + body


def main() -> None:
    table, flat = build()
    OUT.mkdir(parents=True, exist_ok=True)
    md_path, csv_path = OUT / f"{SLUG}.md", OUT / f"{SLUG}.csv"
    md_path.write_text(table, encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerows(flat)
    banned = [f for p in (md_path, csv_path) for f in p3.banned_check_text(p.read_text(encoding="utf-8").splitlines(), p.name)]
    if banned:
        raise SystemExit(f"Table 1 wording check failed: {banned}")
    PAPER.mkdir(parents=True, exist_ok=True)
    for path in (md_path, csv_path):
        shutil.copy2(path, PAPER / path.name)
    print(f"Table 1 written to {OUT.relative_to(REPO)} and copied to {PAPER.relative_to(REPO)}; {len(flat) - 1} rows; checks passed")


if __name__ == "__main__":
    main()
