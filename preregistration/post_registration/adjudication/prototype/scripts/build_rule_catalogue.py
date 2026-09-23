"""Catalogue every citable rule in the frozen taxonomy (ADJ-046).

A source-specific finding must cite a rule (§9.3). Stage 1 previously recorded
only the kind of rule, so "an exclusion rule under Descriptive Monitoring" and
one under Outcome Tracking were indistinguishable. This catalogue gives every
rule a permanent ID, so a finding cites a specific text the second reviewer can
read in the rule reference.

Generated from dict-1.0-rc2 with its SHA-256 verified. Codes are permanent:
a rule is identified by what the frozen dictionary says, not by its visible
name, so re-running keeps existing codes through a rename and appends new ones.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[5]
TAXONOMY = REPO / "taxonomy_data_dictionary.yaml"
TAXONOMY_SHA256 = "7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de"
OUT = Path(__file__).resolve().parents[1] / "instruments" / "rule_catalogue.csv"
VERSION = "rulecat-0.1"
COLUMNS = ["code", "rule_id", "scope", "category", "kind", "rule_type", "name", "excerpt", "introduced_in"]
LAYER_ORDER = ["Layer A -- domain", "Layer C -- purpose", "Cross-cutting tag"]
FIELDS = [("definition", "definition"), ("inclusion_rules", "inclusion rule"), ("exclusion_rules", "exclusion rule")]
# Assignment principles that a classification can conflict with. The retired
# Layer B rule is excluded, because its categories are not assignable.
PRINCIPLES = ["layer_cardinality", "layer_a_assignment_rule", "layer_c_assignment_rule",
              "unclear_fallback_rule", "methodology_domain_purpose_distinction"]
# The dictionary keys principles internally by layer letter.  Layer A and
# Layer C are old labels, so the reviewer reads the current names (ADJ-049).
PRINCIPLE_NAMES = {
    "layer_cardinality": "how many labels each layer takes",
    "layer_a_assignment_rule": "assigning Research Domains",
    "layer_c_assignment_rule": "assigning Analytical Purposes",
    "unclear_fallback_rule": "when Unclear from Register Entry applies",
    "methodology_domain_purpose_distinction": "Methodological research as a domain or as a purpose",
    "layer_independence": "domains, purposes and tags are assigned independently",
    "evidence_not_keyword_rule": "evidence, not a keyword",
    "register_field_evidence_rule": "which register fields count as evidence",
    "domain_purpose_separation": "domain and purpose are separate questions",
    "setting_vs_purpose_rule": "a data source or service setting is not a purpose",
    "tag_lens_rule": "a tag is a lens, not a domain or purpose",
}


def flatten(value):
    if isinstance(value, dict):
        return " ".join(f"{k}: {' '.join(str(v).split())}" for k, v in value.items())
    return " ".join(str(value).split())


def entries():
    if hashlib.sha256(TAXONOMY.read_bytes()).hexdigest() != TAXONOMY_SHA256:
        raise SystemExit("taxonomy_data_dictionary.yaml does not match the frozen dict-1.0-rc2 SHA-256")
    data = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    live = [c for c in data["categories"] if isinstance(c, dict) and not str(c.get("status", "")).startswith("removed")]
    kind_of = {"Layer A -- domain": "Research Domain", "Layer C -- purpose": "Analytical Purpose", "Cross-cutting tag": "tag"}
    # The visible name leads with the layer, matching the mechanism vocabulary
    # the reviewer already reads in Stage 2 (ADJ-049).  It also separates a
    # label such as Unclear from Register Entry, which exists in two layers.
    group_of = {"Layer A -- domain": "Domains", "Layer C -- purpose": "Purposes", "Cross-cutting tag": "Tags"}
    rows = []
    for layer in LAYER_ORDER:
        for c in sorted((x for x in live if x.get("layer") == layer), key=lambda x: x["label"]):
            label = c["label"]; kind = kind_of.get(layer, layer); shown = f"{group_of[layer]}: {label}"
            for field, rule_type in FIELDS:
                if c.get(field):
                    rows.append({"scope": "category", "category": label, "kind": kind, "rule_type": rule_type,
                                 "name": f"{shown} - {rule_type}", "excerpt": flatten(c[field])})
            for n, ce in enumerate(c.get("counterexamples") or [], 1):
                instead = ", ".join(ce.get("instead_consider") or [])
                suffix = f" (instead consider {instead})" if instead else ""
                number = f" {n}" if len(c.get("counterexamples") or []) > 1 else ""
                rows.append({"scope": "category", "category": label, "kind": kind, "rule_type": "counterexample",
                             "name": f"{shown} - counterexample{number}{suffix}", "excerpt": flatten(ce.get("text", ""))})
    meta = data["metadata"]
    for key in PRINCIPLES:
        if key in meta:
            rows.append({"scope": "principle", "category": "", "kind": "principle", "rule_type": key,
                         "name": "Principles: " + PRINCIPLE_NAMES.get(key, key.replace("_", " ")), "excerpt": flatten(meta[key])})
    for key, value in (meta.get("cross_layer_assignment_principles") or {}).items():
        rows.append({"scope": "principle", "category": "", "kind": "principle", "rule_type": key,
                     "name": "Principles: " + PRINCIPLE_NAMES.get(key, key.replace("_", " ")), "excerpt": flatten(value)})
    return rows


def main():
    rows = entries()
    identity = lambda r: (r["scope"], r["category"], r["kind"], r["rule_type"], r["excerpt"])
    existing = {}
    if OUT.exists():
        for r in csv.DictReader(OUT.open(encoding="utf-8")):
            existing[identity(r)] = r
    next_code = max((int(r["code"]) for r in existing.values()), default=0) + 1
    out = []
    for row in rows:
        if identity(row) in existing:
            out.append({**existing[identity(row)], "name": row["name"]}); continue
        out.append({"code": next_code, "rule_id": f"R{next_code:03d}", **row, "introduced_in": VERSION})
        next_code += 1
        if next_code > 998:
            raise SystemExit("rule codes exhausted")
    out.sort(key=lambda r: int(r["code"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore"); w.writeheader(); w.writerows(out)
    kinds = {}
    for r in out: kinds[r["rule_type"] if r["scope"] == "category" else "principle"] = kinds.get(r["rule_type"] if r["scope"] == "category" else "principle", 0) + 1
    print(f"{len(out)} citable rules written: {kinds}")


if __name__ == "__main__":
    main()
