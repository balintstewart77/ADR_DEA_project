"""Compare the before/ and after/ content baselines (assertions A1, A2, A6)."""

from __future__ import annotations

import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def load(run, name):
    with open(os.path.join(_HERE, run, name), encoding="utf-8") as fh:
        return json.load(fh)


def digest(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]


def main():
    ok = True
    before_r, after_r = load("before", "readable_check.json"), load("after", "readable_check.json")
    before_c, after_c = load("before", "complete_check.json"), load("after", "complete_check.json")
    before_m, after_m = load("before", "baseline_meta.json"), load("after", "baseline_meta.json")

    print("=== A1 (readable) ===")
    for state in sorted(before_r):
        b, a = before_r[state], after_r[state]
        for field in ("count_text", "page_size", "first_20_record_ids"):
            same = b[field] == a[field]
            ok &= same
            shown = b[field] if field != "first_20_record_ids" else f"{len(b[field])} ids, sha={digest(b[field])}"
            print(f"  {state} {field:22s} {'MATCH' if same else 'DIFFER'}  {shown}")
        bf, af = b["facet_option_labels"], a["facet_option_labels"]
        same_keys = sorted(bf) == sorted(af)
        ok &= same_keys
        print(f"  {state} facet names           {'MATCH' if same_keys else 'DIFFER'}  {len(bf)} facets")
        for facet in sorted(bf):
            same = bf[facet] == af[facet]
            ok &= same
            print(f"      {facet:22s} {'MATCH' if same else 'DIFFER'}  "
                  f"{len(bf[facet])} options, sha={digest(bf[facet])}")

    print("=== A2 (complete) ===")
    for state in sorted(before_c):
        b, a = before_c[state], after_c[state]
        same_ids = b["record_ids_in_order"] == a["record_ids_in_order"]
        same_rows = b["rows"] == a["rows"]
        ok &= same_ids and same_rows
        print(f"  {state} n_records            {b['n_records']} -> {a['n_records']}")
        print(f"  {state} ordered record ids   {'MATCH' if same_ids else 'DIFFER'}  "
              f"sha={digest(b['record_ids_in_order'])}")
        print(f"  {state} every displayed cell {'MATCH' if same_rows else 'DIFFER'}  "
              f"{len(b['rows'])} rows x {len(b['rows'][0]) - 1} columns, sha={digest(b['rows'])}")
        if not same_rows:
            for i, (br, ar) in enumerate(zip(b["rows"], a["rows"])):
                if br != ar:
                    print("      first differing row", i, br.get("id"))
                    for k in br:
                        if br[k] != ar.get(k):
                            print("        ", k, repr(br[k])[:120], "->", repr(ar.get(k))[:120])
                    break

    print("=== A6 (column set and order) ===")
    same_cols = before_m["table_columns"] == after_m["table_columns"]
    ok &= same_cols
    print(f"  columns {'MATCH' if same_cols else 'DIFFER'}  {len(before_m['table_columns'])} columns")
    for c in before_m["table_columns"]:
        print(f"      {c['id']}")

    print("=== defaults / filter states used ===")
    print("  defaults identical:", before_m["defaults"] == after_m["defaults"])
    print("  filter states identical:", before_m["filter_states"] == after_m["filter_states"])
    print("  callback invoked:", after_m["callback_qualname"])
    ok &= before_m["defaults"] == after_m["defaults"]
    ok &= before_m["filter_states"] == after_m["filter_states"]

    print()
    print("RESULT:", "ALL MATCH" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
