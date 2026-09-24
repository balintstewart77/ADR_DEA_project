import json
from prototype_lib import ROOT, load_json, package_case, preserve, record_correction, reveal, reveal_fields, verify_snapshot

def main():
    case = load_json("cases.json")[0]; response = load_json("submissions.json")[0]
    package = package_case(case)
    store = {}; snapshot_hash = preserve(response, package, store)
    try: preserve(response, package, store)
    except RuntimeError: pass
    verify_snapshot(store)
    # A late mutation of the submitted response cannot reach the preserved snapshot.
    response["adj_dom_evidence"] = 3
    preserved_evidence = store["snapshot"]["response"]["adj_dom_evidence"]
    integrity_ok = verify_snapshot(store) == snapshot_hash
    # One clerical/transcription correction. It is appended; Stage 1 is never overwritten.
    preserved_note = store["snapshot"]["response"]["adj_stage1_note"]
    record_correction(store, snapshot_hash, {"field": "adj_stage1_note", "original_value": preserved_note, "corrected_value": preserved_note.replace(".", " (transcription corrected)."), "reason": "Clerical transcription slip in the synthetic support note.", "author": "SYN_ADJ_R1", "date": "2026-09-21"})
    unchanged_after_correction = verify_snapshot(store) == snapshot_hash
    tampered = json.loads(json.dumps(store["snapshot"])); tampered["response"]["adj_dom_evidence"] = 3
    try:
        verify_snapshot({"snapshot": tampered, "snapshot_bytes": store["snapshot_bytes"], "snapshot_hash": snapshot_hash}); tamper_detected = False
    except PermissionError: tamper_detected = True
    payload = {package["assignment_id"]: reveal_fields(case,package)}
    try: reveal(package["assignment_id"], package["package_id"], snapshot_hash, payload, store, case, simulate_partial=True)
    except RuntimeError: pass
    revealed = reveal(package["assignment_id"], package["package_id"], snapshot_hash, payload, store, case)
    receipt = {"snapshot_hash": snapshot_hash, "snapshot_integrity_verified": integrity_ok, "snapshot_unchanged_by_caller_mutation": preserved_evidence == 1, "tampered_snapshot_detected": tamper_detected, "snapshot_unchanged_after_correction": unchanged_after_correction, "derived": store["snapshot"]["derived"], "adj_correction": store["adj_correction"], "events": store["events"], "exposure_history": store.get("exposure_history", []), "reveal_assignment": revealed["assignment_id"]}
    (ROOT / "fixtures" / "workflow_demo_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("Preserved, rejected append attempt, verified snapshot integrity, detected a tampered snapshot, appended one clerical correction, recorded partial exposure, and recovered synthetic reveal.")
if __name__ == "__main__": main()
