"""Table 1: the classification taxonomy and its core assignment rules (dict-1.0-rc2). Pass-4 log P4.81.

Sources, each checked against its committed version in git (allowing for line endings):

* ``taxonomy_data_dictionary.yaml`` — the frozen dictionary (version 1.0-rc2, SHA-256 7ddbf1bb… as recorded in the
  Stage B run metadata). It is the authority for which labels exist in each layer and for the cardinality rule.
* ``preregistration/package/05_training_and_pilot/DEA_trainer_handout_v1.docx`` — the handout delivered at the
  17 July 2026 training session. Its domain and purpose tables give the one-line, coder-facing scope of each label,
  and its ground-rules table gives the operational assignment rules. The script requires the handout's label lists to
  equal the dictionary's active labels exactly.

Tag scopes and two rules (cardinality; Outcome Tracking against Policy Evaluation) are condensed from the dictionary and
handout; each is checked against phrases in its source before the table is written.

Writes ``analysis/tables/table_1_taxonomy.{md,csv}`` and copies them to ``DEA_paper/tables/`` (both gitignored).
Run from the repository root:  python -m analysis.visualisations.taxonomy_table_1
"""
from __future__ import annotations

import csv
import hashlib
import html
import re
import shutil
import subprocess
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_scratch_coder_pass3 as p3  # noqa: E402

DICTIONARY = "taxonomy_data_dictionary.yaml"
FROZEN_SHA256 = "7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de"
HANDOUT = "preregistration/package/05_training_and_pilot/DEA_trainer_handout_v1.docx"
SLUG = "table_1_taxonomy"
OUT, PAPER = REPO / "analysis/tables", REPO / "DEA_paper/tables"
UNCLEAR = "Unclear from Register Entry"

TAGS = (  # condensed from the handout's tag section; the quoted phrases must appear there
    ("Demographic disparities / equity",
     "Yes when a comparison by an equality-relevant characteristic (for example sex, ethnicity, disability, age or migrant status) "
     "is central to the research question; not for demographic controls or socioeconomic inequality alone",
     ("equality-relevant comparison is central", "purely socioeconomic inequality")),
    ("COVID-19 & Pandemic",
     "Yes when the pandemic (infection, vaccination, lockdowns, pandemic relief schemes or its consequences) is a central condition or lens; "
     "not when it is merely the period the data cover",
     ("central condition or lens", "only the time period the data covers")),
)
EXTRA_RULES = (
    ("Number of labels",
     "One or more Research Domains and one or two Analytical Purposes per project; each tag is yes or no. "
     "Unclear from Register Entry is used only where no substantive label can be assigned in that dimension",
     ("dictionary", "Layer A -- domain: one or more", "Layer C -- purpose: one or two")),
    ("Outcome Tracking versus Policy Evaluation",
     "A naturally occurring exposure linked to a later outcome is Outcome Tracking; a deliberate, named policy, programme "
     "or intervention is Policy Evaluation / Impact Analysis",
     ("handout", "Natural exposure -> Outcome Tracking", "Named designed intervention -> Policy Evaluation")),
)


def committed_bytes(rel: str) -> bytes:
    raw = (REPO / rel).read_bytes()
    blob = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=REPO, capture_output=True, check=True).stdout
    if raw.replace(b"\r\n", b"\n") != blob.replace(b"\r\n", b"\n"):
        raise SystemExit(f"{rel} differs from its committed version")
    return raw


def docx_tables(raw: bytes) -> tuple[list[list[list[str]]], str]:
    xml = zipfile.ZipFile(BytesIO(raw)).read("word/document.xml").decode("utf-8")
    tables = []
    for tbl in re.findall(r"<w:tbl>.*?</w:tbl>", xml, flags=re.S):
        rows = [[html.unescape(re.sub(r"<[^>]+>", "", cell)).strip() for cell in re.findall(r"<w:tc>.*?</w:tc>", row, flags=re.S)]
                for row in re.findall(r"<w:tr[ >].*?</w:tr>", tbl, flags=re.S)]
        tables.append(rows)
    paragraphs = [html.unescape(re.sub(r"<[^>]+>", "", par)) for par in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)]
    return tables, re.sub(r"\s+", " ", " ".join(paragraphs))


def table_with_header(tables: list, first: str) -> list[list[str]]:
    hits = [t for t in tables if t and t[0] and t[0][0] == first]
    if len(hits) != 1:
        raise SystemExit(f"Handout: expected one table headed {first!r}, found {len(hits)}")
    return hits[0][1:]


def build() -> tuple[str, list[list[str]]]:
    raw = committed_bytes(DICTIONARY)
    if hashlib.sha256(raw).hexdigest() != FROZEN_SHA256:
        raise SystemExit("Dictionary is not the frozen dict-1.0-rc2 file used in validation")
    dictionary = yaml.safe_load(raw.decode("utf-8"))
    if dictionary["metadata"]["dictionary_version"] != "1.0-rc2":
        raise SystemExit("Unexpected dictionary version")
    live = [c for c in dictionary["categories"] if not str(c.get("status", "")).startswith("removed")]
    labels = {layer: [c["label"] for c in live if c["layer"] == layer]
              for layer in ("Layer A -- domain", "Layer C -- purpose")}
    tag_labels = [c["label"] for c in live if c["layer"] == "Cross-cutting tag"]

    tables, handout_text = docx_tables(committed_bytes(HANDOUT))
    domains = table_with_header(tables, "Domain")
    purposes = table_with_header(tables, "Purpose")
    rules = table_with_header(tables, "Rule")
    for layer, rows in (("Layer A -- domain", domains), ("Layer C -- purpose", purposes)):
        if sorted(r[0] for r in rows) != sorted(labels[layer]):
            raise SystemExit(f"Handout labels differ from the dictionary for {layer}")
    substantive = {layer: [lab for lab in labels[layer] if lab != UNCLEAR] for layer in labels}
    if len(substantive["Layer A -- domain"]) != 11 or len(substantive["Layer C -- purpose"]) != 7 or len(tag_labels) != 2:
        raise SystemExit("Unexpected number of labels")
    meta_text = yaml.safe_dump(dictionary["metadata"], allow_unicode=True)
    for name, _, phrases in TAGS:
        if not any(name.split(" ")[0] in t for t in tag_labels) or not all(p in handout_text for p in phrases):
            raise SystemExit(f"Tag scope for {name} not found in its sources")
    for name, _, (source, *phrases) in EXTRA_RULES:
        text = meta_text if source == "dictionary" else handout_text
        if not all(p in text for p in phrases):
            raise SystemExit(f"Rule {name!r} not found in the {source}")

    head = ["Label or rule", "Definition"]
    body: list[list[str]] = []
    flat: list[list[str]] = [["Section"] + head]

    def section(title: str, rows: list[tuple[str, str]]) -> None:
        body.append([title])
        for label, scope in rows:
            body.append([label, scope])
            flat.append([title, label, scope])

    section("Research Domains: what the project studies (one or more)",
            [(r[0], f"Assigned when the project is substantively about {r[1]}" if r[0] != UNCLEAR else f"Assigned when {r[1]}") for r in domains])
    section("Analytical Purposes: what the analysis does with the data (one or two)",
            [(r[0], f"Assigned when the project aims to {r[1]}" if r[0] != UNCLEAR else f"Assigned when {r[1]}") for r in purposes])
    section("Cross-cutting tags (yes or no)", [(name, scope) for name, scope, _ in TAGS])
    section("Assignment rules", [(r[0], r[1]) for r in rules] + [(name, text) for name, text, _ in EXTRA_RULES])
    return p3.html_table(head, body), flat


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
