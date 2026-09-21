from pathlib import Path
import html
from prototype_lib import ROOT, default_valid_submission, load_json, package_case, write_dictionary, write_record_import

def main():
    write_dictionary(ROOT / "instruments" / "adjudication_stage1_candidate.csv")
    cases = load_json("cases.json")
    # One masked record per case-reviewer assignment, for an already-imported
    # dictionary. Primary and secondary packages are independently ordered.
    import_rows = write_record_import(ROOT / "instruments" / "adjudication_record_import_synthetic.csv", cases)
    packages = [package_case(case) for case in cases]
    (ROOT / "fixtures" / "generated_masked_packages.json").write_text(__import__("json").dumps(packages, indent=2), encoding="utf-8")
    (ROOT / "fixtures" / "submissions.json").write_text(__import__("json").dumps([default_valid_submission(package) for package in packages], indent=2), encoding="utf-8")
    cards = []
    for package in packages:
        lines = []
        for c in package["candidates"]:
            lines.append(f"<li><strong>{html.escape(c['candidate_id'])}</strong>: Domains {html.escape(', '.join(c['domains']))}; Purposes {html.escape(', '.join(c['purposes']))}; COVID {html.escape(c['covid'])}; equity {html.escape(c['equity'])}</li>")
        modules = []
        for code, label in (("dom", "Domains"), ("purp", "Purposes"), ("covid", "COVID-19/pandemic"), ("equity", "Equity")):
            interps = package["interpretations"][code]
            values = "".join(f"<li>{html.escape(x['interpretation_id'])}: {html.escape(', '.join(x['value']) if isinstance(x['value'], list) else x['value'])}; complete candidates {html.escape(', '.join(x['candidate_ids']))}</li>" for x in interps)
            branch = "Comparative fields required" if len(interps) > 1 else "Single-interpretation path: comparative fields not applicable"
            questions = "Relative support; best interpretation slots; absolute adequacy; defensible interpretations (None / identified / cannot judge); materially weaker support; boundary state/citation/explanation."
            if code in {"dom", "purp"}: questions += " Differing-label rows require support, rule conflict/citation, and supported-omission assessment; shared-label and additional-label routes have explicit None states."
            else: questions += " Tag-status support, rule conflict/citation, and opposite-status support are separate."
            modules.append(f"<details><summary>{label} — {branch}</summary><ul>{values}</ul><p>{questions}</p></details>")
        modules = "".join(modules)
        flags = "None" if not package["qa_flags"] else ", ".join(package["qa_flags"])
        cards.append(f"<article><h2>{package['record_id']} — {package['package_id']}</h2><p>Masked synthetic package. Candidate order is seeded; no source identity, route, reveal material, or audit cue is embedded.</p><p>Input QA flags: {html.escape(flags)}. Flags are not repaired and block preservation.</p><ol>{''.join(lines)}</ol>{modules}</article>")
    page = "<!doctype html><meta charset=utf-8><title>Synthetic DEA Stage 1 preview</title><style>body{max-width:1000px;margin:2rem auto;font:16px system-ui}article{border:1px solid #aaa;padding:1rem;margin:1rem 0}details{margin:.5rem 0}</style><h1>Offline synthetic Stage 1 review preview</h1><p>Candidate rendering differs from REDCap and is not a security boundary. It is generated from the same synthetic package definitions, without reveal data.</p>" + "".join(cards)
    (ROOT / "preview" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "preview" / "index.html").write_text(page, encoding="utf-8")
    print(f"Generated {len(packages)} masked packages, candidate dictionary, preview, and {len(import_rows)} synthetic record-import rows.")
if __name__ == "__main__": main()
