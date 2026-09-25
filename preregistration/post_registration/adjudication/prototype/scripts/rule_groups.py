"""Group Stage 1 rule citations into problem groups for analysis (ADJ-079).

A label's definition, inclusion rule, exclusion rule and counterexample
describe one boundary from different sides, and an adjudicator can reasonably
cite any of them for the same problem.  Counting by rule ID would split one
problem by citation habit, so the analysis counts by label group instead:

* level 1, as recorded: the rule ID, reported descriptively only;
* level 2, label group: the four category rules of a label, one group per
  label and layer (22).  A principle, or Other, names no label, so it is
  grouped by the labels ticked for its conflict; principle 92, on when
  Unclear from Register Entry applies, joins the Unclear group of the layer
  its conflict is scoped to.  A principle with no label in scope forms its
  own group;
* level 3: the Domains and Purposes Unclear groups, also reported together.

The direction of a breach is derived from whether the conflicting option
contains the label, never from the rule type cited.  The mapping is generated
from the frozen rule catalogue alone and uses no adjudication data.

Run to write instruments/rule_groups.csv.
"""
from __future__ import annotations

import csv

from prototype_lib import ROOT, RULE_OTHER, rule_catalogue, rule_choices


def principle_names():
    """Principle names as the dropdown shows them, e.g. 'how many labels each layer takes'."""
    names = {}
    for choice in rule_choices().split(" | "):
        code, _, label = choice.partition(", ")
        if label.startswith("Principles: "):
            names[int(code)] = label[len("Principles: "):]
    return names

LAYER = {"Research Domain": "Domains", "Analytical Purpose": "Purposes", "tag": "Tags"}
COMPONENT_LAYER = {"dom": "Domains", "purp": "Purposes"}
UNCLEAR = "Unclear from Register Entry"
UNCLEAR_PRINCIPLE = 92
OUT = ROOT / "instruments" / "rule_groups.csv"
COLUMNS = ("code", "rule_id", "scope", "layer", "category", "rule_type", "label_group", "grouping", "unclear_problem")


def catalogue_rows():
    """One row per citable code: the 99 frozen rules, then Other."""
    rows = []
    names = principle_names()
    for r in rule_catalogue():
        code = r["code"]
        if r["scope"] == "category":
            layer = LAYER[r["kind"]]
            rows.append({"code": code, "rule_id": r["rule_id"], "scope": "category", "layer": layer,
                         "category": r["category"], "rule_type": r["rule_type"],
                         "label_group": f"{layer}: {r['category']}", "grouping": "fixed: the rule's own label",
                         "unclear_problem": int(r["category"] == UNCLEAR)})
        else:
            unclear = code == UNCLEAR_PRINCIPLE
            rows.append({"code": code, "rule_id": r["rule_id"], "scope": "principle", "layer": "Principles",
                         "category": names[code], "rule_type": r["rule_type"], "label_group": "",
                         "grouping": ("scoped layer's Unclear from Register Entry group" if unclear
                                      else "the labels ticked for the conflict"),
                         "unclear_problem": int(unclear)})
    rows.append({"code": RULE_OTHER, "rule_id": "", "scope": "other", "layer": "Other", "category": "",
                 "rule_type": "other", "label_group": "", "grouping": "the labels ticked for the conflict",
                 "unclear_problem": 0})
    return rows


def groups_for(code, scope, labels):
    """Level-2 groups for one recorded conflict.

    code: the cited rule code.  scope: the components the conflict is scoped
    to ("dom", "purp", "covid", "equity").  labels: {"dom": [...], "purp": [...]}
    label names ticked for the conflict, empty where the form did not ask.
    """
    row = next((r for r in catalogue_rows() if r["code"] == code), None)
    if row is None:
        raise ValueError(f"rule code {code!r} is not in the frozen catalogue")
    if row["scope"] == "category":
        return [row["label_group"]]
    if code == UNCLEAR_PRINCIPLE:
        groups = [f"{COMPONENT_LAYER[c]}: {UNCLEAR}" for c in ("dom", "purp") if c in scope]
    else:
        groups = [f"{COMPONENT_LAYER[c]}: {label}" for c in ("dom", "purp") if c in scope for label in labels.get(c, [])]
    return sorted(set(groups)) or [f"{row['layer']}: {row['category'] or row['rule_type']}"]


def record_groups(conflicts):
    """Distinct level-2 groups for one record's conflicts.

    conflicts: (code, scope, labels) for each conflict recorded.  One problem
    cited through two rules on the same record, such as a label's exclusion
    rule and the Unclear principle, counts once: the unit is the record and
    group, never the citation.
    """
    return sorted({g for code, scope, labels in conflicts for g in groups_for(code, scope, labels)})


def is_unclear_problem(group):
    """Level 3: the Domains and Purposes Unclear groups, reported together."""
    return group.endswith(f": {UNCLEAR}") and group.split(":")[0] in ("Domains", "Purposes")


def write(path=OUT):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(catalogue_rows())


if __name__ == "__main__":
    write()
    rows = catalogue_rows()
    groups = {r["label_group"] for r in rows if r["label_group"]}
    print(f"{len(rows)} codes; {len(groups)} fixed label groups; "
          f"{sum(r['scope'] != 'category' for r in rows)} grouped by labels ticked or scope")
