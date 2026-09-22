"""Draft the starter mechanism vocabulary (ADJ-044) from the frozen taxonomy and protocol.

A mechanism is the specific, repeatable reason a disagreement arose.  The
release triggers count a mechanism across distinct records, so it is picked
from a controlled list rather than typed.  This draft draws only on the frozen
taxonomy dict-1.0-rc2 and on the protocol's own family definitions, so it is
built before any formal case is seen.

Codes are permanent.  Re-running keeps every existing code for an unchanged
name and appends new entries with new codes; a code is never renumbered or
reused, because findings already coded against it would change meaning.
"""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[5]
TAXONOMY = REPO / "taxonomy_data_dictionary.yaml"
TAXONOMY_SHA256 = "7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de"
OUT = Path(__file__).resolve().parents[1] / "instruments" / "mechanism_vocabulary.csv"
VERSION = "mechvocab-0.1"
COLUMNS = ["code", "group", "name", "description", "components", "source", "introduced_in"]
# Group "rule": families 1, 2, 4 and 6.  Group "data": family 7.
GENERAL = [
    ("rule", "General: label assigned from an incidental mention or background data",
     "A label is assigned because the entry mentions a topic, or uses data only as background, controls or context, which the exclusion rules repeatedly forbid.",
     "dom;purp", "dict-1.0-rc2 exclusion rules (repeated 'do not assign solely/merely because' wording)"),
    ("rule", "General: label central to the entry omitted",
     "A label whose inclusion rule is met, because its subject is central to the project, is left out.",
     "dom;purp", "dict-1.0-rc2 inclusion rules ('assign when ... central')"),
    ("rule", "General: Unclear from Register Entry used though the entry resolves the label",
     "Unclear is assigned although the title or datasets reveal a clear domain or purpose.",
     "dom;purp", "dict-1.0-rc2 Unclear from Register Entry exclusion rules, Layers A and C"),
    ("rule", "General: substantive label assigned where only Unclear is supported",
     "A substantive label is assigned although the title is opaque and the datasets do not resolve the domain or purpose.",
     "dom;purp", "dict-1.0-rc2 Unclear from Register Entry inclusion rules, Layers A and C"),
    ("rule", "Tags: equity tag applied for controls, covariates or routine stratifiers",
     "The equity tag is assigned although demographic variables are only controls, covariates, sample descriptors or routine stratifiers.",
     "equity", "dict-1.0-rc2 equity tag exclusion rule"),
    ("rule", "Tags: equity tag omitted where a demographic comparison is central",
     "The equity tag is left out although comparison across demographic or equality-relevant groups is central to the research question.",
     "equity", "dict-1.0-rc2 equity tag inclusion rule"),
    ("rule", "Tags: COVID-19 tag applied because the study period overlaps the pandemic",
     "The COVID-19 tag is assigned although COVID-19 is only a date range, background period or incidental context.",
     "covid", "dict-1.0-rc2 COVID-19 tag exclusion rule and counterexample"),
    ("rule", "Tags: COVID-19 tag applied to health or infectious-disease research without explicit pandemic framing",
     "The COVID-19 tag is assigned to infectious disease, health or mortality research where COVID-19 or pandemic framing is not explicit.",
     "covid", "dict-1.0-rc2 COVID-19 tag exclusion rule"),
    ("rule", "Tags: COVID-19 tag omitted where pandemic conditions are central",
     "The COVID-19 tag is left out although COVID-19 or pandemic conditions are central to the research question.",
     "covid", "dict-1.0-rc2 COVID-19 tag inclusion rule"),
    ("rule", "Tags: tag used as a substitute for a substantive domain or purpose",
     "A tag stands in for the domain or purpose it should accompany.",
     "covid;equity", "dict-1.0-rc2 exclusion rules of both tags"),
    ("rule", "Taxonomy: no category adequately represents the research focus",
     "The project's substantive focus has no adequate category, so sources choose different near fits.",
     "dom;purp", "Protocol §9.3(4): missing or inadequately represented category"),
    ("rule", "Taxonomy: category definitions overlap where the rules give no resolution",
     "Two categories both fit and no exclusion rule or counterexample says which applies.",
     "dom;purp", "Protocol §9.3(4): ambiguous or overlapping category boundaries"),
    ("data", "Data: datasets-used or title field truncated, garbled or mis-parsed",
     "The public entry shown differs from the source because a field was parsed incorrectly.",
     "dom;purp;covid;equity", "Protocol §9.3(7): a parsed field"),
    ("data", "Data: cleaning decision changed the visible entry",
     "A cleaning or deduplication decision altered what the entry showed.",
     "dom;purp;covid;equity", "Protocol §9.3(7): a cleaning decision"),
    ("data", "Data: Record ID or duplicate-entry problem",
     "The entry is linked to the wrong record, duplicated or merged.",
     "dom;purp;covid;equity", "Protocol §9.3(7): a Record-ID issue"),
    ("data", "Data: form design or wording shaped the recorded classification",
     "An instrument's layout, wording or choices led a source to a classification it would not otherwise give.",
     "dom;purp;covid;equity", "Protocol §9.3(7): form design"),
    ("data", "Data: branching or validation rule shaped the recorded classification",
     "A branching rule, requiredness or validation limit constrained the recorded answer.",
     "dom;purp;covid;equity", "Protocol §9.3(7): a branching rule"),
    ("data", "Data: other procedure affected the classification",
     "A procedural step not listed above affected the classification.",
     "dom;purp;covid;equity", "Protocol §9.3(7): related procedure"),
]


def boundary_pairs():
    if hashlib.sha256(TAXONOMY.read_bytes()).hexdigest() != TAXONOMY_SHA256:
        raise SystemExit("taxonomy_data_dictionary.yaml does not match the frozen dict-1.0-rc2 SHA-256")
    # Every category not marked removed is live: "active", "new v3.4" and
    # "relabelled v3.4" all appear in the frozen dictionary.
    cats = [c for c in yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))["categories"]
            if isinstance(c, dict) and not str(c.get("status", "")).startswith("removed")]
    kind_of = lambda layer: "Tags" if "tag" in layer.lower() else "Purposes" if "purpose" in layer.lower() else "Domains"
    layers_of = {}
    for c in cats:
        layers_of.setdefault(c["label"], set()).add(kind_of(c.get("layer", "")))
    pairs = {}
    for c in cats:
        src = c["label"]; src_kind = kind_of(c.get("layer", ""))
        targets = re.findall(r"\*\*(.+?)\*\*", c.get("exclusion_rules") or "")
        for ce in c.get("counterexamples") or []:
            targets += ce.get("instead_consider") or []
        for tgt in targets:
            if tgt not in layers_of or tgt == src: continue
            # A label such as Unclear from Register Entry exists in more than
            # one layer; the rule's own layer decides which is meant.
            tgt_kind = src_kind if src_kind in layers_of[tgt] else sorted(layers_of[tgt])[0]
            key = tuple(sorted(((src, src_kind), (tgt, tgt_kind))))
            pairs.setdefault(key, set()).add(src)
    rows = []
    for ((a, ka), (b, kb)), sources in pairs.items():
        kinds = {ka, kb}
        kind = "Tags" if "Tags" in kinds else ka
        comp = {"Domains": "dom", "Purposes": "purp"}
        if kind == "Tags":
            tag = a if ka == "Tags" else b
            other = kb if ka == "Tags" else ka
            components = ("covid" if "COVID" in tag else "equity") + ";" + comp.get(other, "")
        else:
            components = comp[kind]
        rows.append(("rule", f"{kind}: {a} vs {b}",
                     "One is assigned where the frozen rules point to the other, or the pair is confused.",
                     components.strip(";"), "dict-1.0-rc2 exclusion rule or counterexample under " + " and ".join(sorted(sources))))
    order = {"Domains": 0, "Purposes": 1, "Tags": 2}
    return sorted(rows, key=lambda r: (order[r[1].split(":")[0]], r[1]))


def main():
    entries = boundary_pairs() + GENERAL
    existing = {}
    if OUT.exists():
        for r in csv.DictReader(OUT.open(encoding="utf-8")):
            existing[r["name"]] = r
    next_code = {"rule": 1, "data": 101}
    for r in existing.values():
        g = r["group"]; next_code[g] = max(next_code[g], int(r["code"]) + 1)
    rows = []
    for group, name, description, components, source in entries:
        if name in existing:
            rows.append(existing[name]); continue
        rows.append({"code": next_code[group], "group": group, "name": name, "description": description,
                     "components": components, "source": source, "introduced_in": VERSION})
        next_code[group] += 1
        if next_code["rule"] > 998 or next_code["data"] > 998:
            raise SystemExit("vocabulary codes exhausted")
    rows.sort(key=lambda r: int(r["code"]))
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS); w.writeheader(); w.writerows(rows)
    groups = {}
    for r in rows: groups[r["group"]] = groups.get(r["group"], 0) + 1
    print(f"{len(rows)} mechanisms written ({groups}); boundary pairs from the frozen rules: {len(boundary_pairs())}")


if __name__ == "__main__":
    main()
