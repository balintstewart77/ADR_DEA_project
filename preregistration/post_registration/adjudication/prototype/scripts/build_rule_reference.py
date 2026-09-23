"""Generate the adjudicator rule reference from the frozen taxonomy (ADJ-045).

Protocol §9.2 makes the frozen taxonomy and coding rules an input to Stage 1,
so both the primary adjudicator and the second reviewer read this document.
It is generated from dict-1.0-rc2 with its SHA-256 verified, so it cannot
drift from the rules the production model and the coders worked to.

It carries rules, not answers: definitions, inclusion and exclusion rules,
counterexamples and the assignment principles. The coders' keyed worked
examples are deliberately excluded, because they were selected from records
where the two models agreed (protocol §6.1).
"""
from __future__ import annotations

import csv
import hashlib
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[5]
TAXONOMY = REPO / "taxonomy_data_dictionary.yaml"
TAXONOMY_SHA256 = "7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de"
OUT = Path(__file__).resolve().parents[2] / "reference" / "taxonomy_rule_reference.md"
CATALOGUE = Path(__file__).resolve().parents[1] / "instruments" / "rule_catalogue.csv"
PRINCIPLES = [
    ("Layer cardinality", "layer_cardinality"),
    ("Assigning a Research Domain", "layer_a_assignment_rule"),
    ("Assigning an Analytical Purpose", "layer_c_assignment_rule"),
    ("Unclear from Register Entry", "unclear_fallback_rule"),
    ("Across layers", "cross_layer_assignment_principles"),
    ("Domain or purpose for methodology", "methodology_domain_purpose_distinction"),
    ("How the dictionary uses examples", "example_policy"),
]
KIND_OF = {"Layer A -- domain": "Research Domain", "Layer C -- purpose": "Analytical Purpose", "Cross-cutting tag": "tag"}
ORDER = [("Layer A -- domain", "Research Domains"), ("Layer C -- purpose", "Analytical Purposes"), ("Cross-cutting tag", "Cross-cutting tags")]


def text(value, indent=""):
    if isinstance(value, dict):
        return "\n".join(f"{indent}- **{k}:** {' '.join(str(v).split())}" for k, v in value.items())
    return indent + " ".join(str(value).split())


def rule_ids():
    """Map a catalogue entry's name to its permanent ID, so the reference and the
    form cite the same rule (ADJ-046)."""
    if not CATALOGUE.exists(): raise SystemExit("rule_catalogue.csv missing; run build_rule_catalogue.py first")
    ids = {}
    for row in csv.DictReader(CATALOGUE.open(encoding="utf-8")):
        key = (row["category"], row["kind"], row["rule_type"]) if row["scope"] == "category" else ("", "principle", row["rule_type"])
        ids[key] = row["rule_id"]
    return ids


def main():
    actual = hashlib.sha256(TAXONOMY.read_bytes()).hexdigest()
    if actual != TAXONOMY_SHA256:
        raise SystemExit(f"taxonomy SHA-256 {actual} does not match the frozen dict-1.0-rc2")
    data = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    meta = data["metadata"]
    live = [c for c in data["categories"] if isinstance(c, dict) and not str(c.get("status", "")).startswith("removed")]
    retired = [c for c in data["categories"] if isinstance(c, dict) and str(c.get("status", "")).startswith("removed")]

    ids = rule_ids()
    out = [f"# Adjudication rule reference: {meta.get('title', '')}".rstrip(),
           "",
           f"Generated {date.today().isoformat()} from `taxonomy_data_dictionary.yaml`, dictionary "
           f"version {meta.get('dictionary_version')}, ontology {meta.get('documents_ontology_version')}.",
           f"Source SHA-256 `{TAXONOMY_SHA256}`.",
           "",
           "This is the rule text the production model and the scratch coders worked to, and",
           "protocol §9.2 makes it an input to Stage 1. The primary adjudicator and the second",
           "reviewer use this same version. Do not edit it, and do not substitute a later",
           "dictionary. Each rule carries the ID the adjudication form uses, such as R003,",
           "so a finding cites a rule both reviewers can read here.",
           "",
           "It contains rules, not worked answers. The coders' keyed training examples are",
           "excluded, because they were selected from records where the two models agreed.",
           "",
           "**Older names in the quoted rules.** The frozen dictionary names its layers",
           "internally, and the rule text below is reproduced exactly, so those names",
           "remain. Read Layer A as Research Domains, Layer C as Analytical Purposes, and",
           "Layer B as the retired linkage categories, which are no longer assignable.",
           "Headings in this document use the current names.",
           "",
           "## Assignment principles", ""]
    principles = list(PRINCIPLES)
    # Each cross-layer principle is catalogued separately, so each gets its own
    # subsection and ID rather than being flattened into one block.
    principles = [p for p in principles if p[1] != "cross_layer_assignment_principles"]
    for key in (meta.get("cross_layer_assignment_principles") or {}):
        principles.append((key.replace("_", " ").capitalize(), key))
    meta = {**meta, **(meta.get("cross_layer_assignment_principles") or {})}
    for heading, key in principles:
        if key in meta:
            rid = ids.get(("", "principle", key))
            out += [f"### {heading}" + (f" ({rid})" if rid else ""), "", text(meta[key]), ""]
    for layer, heading in ORDER:
        cats = [c for c in live if c.get("layer") == layer]
        if not cats:
            continue
        out += [f"## {heading}", ""]
        for c in cats:
            out += [f"### {c['label']}", ""]
            if c.get("status") not in (None, "active"):
                out += [f"*Status: {c['status']}.*", ""]
            for field, title, kind in (("definition", "Definition", "definition"), ("inclusion_rules", "Assign when", "inclusion rule"), ("exclusion_rules", "Do not assign when", "exclusion rule")):
                if c.get(field):
                    rid = ids.get((c["label"], KIND_OF.get(c.get("layer"), ""), kind))
                    out += [f"**{title}{f' ({rid})' if rid else ''}.** {text(c[field])}", ""]
            for ce in c.get("counterexamples") or []:
                instead = ", ".join(ce.get("instead_consider") or [])
                rid = ids.get((c["label"], KIND_OF.get(c.get("layer"), ""), "counterexample"))
                out += [f"**Counterexample{f' ({rid})' if rid else ''}.** " + text(ce.get("text", "")), ""]
                if ce.get("rationale"):
                    out += ["*Why:* " + text(ce["rationale"]), ""]
                if ce.get("instead_consider"):
                    out += ["*Instead consider:* " + ", ".join(ce["instead_consider"]), ""]
            for ex in c.get("examples") or []:
                out += ["**Example.** " + text(ex if isinstance(ex, str) else ex.get("text", "")), ""]
    if retired:
        out += ["## Retired categories, not assignable", "",
                "These appear in the dictionary's history and must not be assigned:", ""]
        out += [f"- {c['label']} ({c.get('layer')}, {c.get('status')})" for c in retired] + [""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"{OUT.name}: {len(live)} live categories, {len(retired)} retired, "
          f"{sum(len(c.get('counterexamples') or []) for c in live)} counterexamples")


if __name__ == "__main__":
    main()
