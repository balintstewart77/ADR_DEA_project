from pathlib import Path
import html
from prototype_lib import ROOT, assignment_packages, default_valid_submission, load_json, package_case, write_data_quality_rules, write_dictionary, write_record_import, write_reveal_import

def main():
    write_dictionary(ROOT / "instruments" / "adjudication_stage1_candidate.csv")
    write_data_quality_rules(ROOT / "instruments" / "adjudication_data_quality_rules.csv")
    cases = load_json("cases.json")
    # One masked record per case-reviewer assignment, for an already-imported
    # dictionary. Primary and secondary packages are independently ordered.
    import_rows = write_record_import(ROOT / "instruments" / "adjudication_record_import_synthetic.csv", cases)
    # Reveal rows are imported only after Stage 1 is preserved for each record.
    write_reveal_import(ROOT / "instruments" / "adjudication_reveal_import_synthetic.csv", [(case, package) for case in cases for _, _, package in assignment_packages(case)])
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
            branch = "Differs: evidence, best supported and defensible options asked" if len(interps) > 1 else "Does not differ: no component questions"
            questions = "Asked blind for a differing component: how much information the entry gives; which option or options are best supported (ties named); and which options are defensible. Sufficient support is derived."
            if len(package["candidates"]) == 1: questions = "Single displayed set: each proposed label is checked for support and rule conflict, and an additional or alternative label may be recorded."
            modules.append(f"<details><summary>{label} — {branch}</summary><ul>{values}</ul><p>{questions}</p></details>")
        modules = "".join(modules)
        record_questions = "<p>Record-level Stage 1: summary of differences correct; explicit rule conflict, naming option, label, rule type and reason; boundary; masking. Other concern and unresolved default to No.</p>" if len(package["candidates"]) > 1 else "<p>Record-level Stage 1: summary of differences correct; boundary; masking. Other concern and unresolved default to No.</p>"
        flags = "None" if not package["qa_flags"] else ", ".join(package["qa_flags"])
        cards.append(f"<article><h2>{package['record_id']} — {package['package_id']}</h2><p>Masked synthetic package. Candidate order is seeded; no source identity, route, reveal material, or audit cue is embedded.</p><p>Input QA flags: {html.escape(flags)}. Flags are not repaired and block preservation.</p><ol>{''.join(lines)}</ol>{record_questions}{modules}</article>")
    page = "<!doctype html><meta charset=utf-8><title>Synthetic DEA Stage 1 preview</title><style>body{max-width:1000px;margin:2rem auto;font:16px system-ui}article{border:1px solid #aaa;padding:1rem;margin:1rem 0}details{margin:.5rem 0}</style><h1>Offline synthetic Stage 1 review preview</h1><p>Candidate rendering differs from REDCap and is not a security boundary. It is generated from the same synthetic package definitions, without reveal data.</p>" + "".join(cards)
    (ROOT / "preview" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "preview" / "index.html").write_text(page, encoding="utf-8")
    print(f"Generated {len(packages)} masked packages, candidate dictionary, preview, and {len(import_rows)} synthetic record-import rows.")
if __name__ == "__main__": main()
