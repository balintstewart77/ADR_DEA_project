import csv
import hashlib
import re
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET


CALIBRATION = Path(
    "preregistration/package/05_training_and_pilot/"
    "DEA_post_pilot_shared_calibration_note.docx"
)
AUDIT = Path(
    "preregistration/package/05_training_and_pilot/"
    "post_pilot_calibration_model_direction_audit.csv"
)
FABLE = Path("analysis/outputs_classified_20260702_fable5/layer_classifications.csv")
GPT = Path("preregistration_restricted/classifications_1309_precollapse_PROVISIONAL.csv")
PROTOCOL = Path(
    "preregistration/package/00_protocol/Validation_Protocol_PreReg_v0.12.docx"
)
MANIFEST = Path("preregistration/preregistration_artifact_manifest.csv")
EXCLUSIONS = Path(
    "preregistration/package/04_exclusions_and_sampling/"
    "training_pilot_exclusion_list_v8.csv"
)
EXPECTED_IDS = {"2019/015", "2021/038", "2021/056", "2024/248"}
CALIBRATION_SHA256 = "ae2bae5169260f4e7e3bf10af5e158068d91be6e0a4860fc36b6612538d3c946"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _docx_paragraphs(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    return [
        "".join(node.text or "" for node in paragraph.iter(W + "t"))
        for paragraph in root.iter(W + "p")
    ]


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _sets(value: str, delimiter: str) -> frozenset[str]:
    return frozenset(part.strip() for part in value.split(delimiter) if part.strip())


def _calibration_sets() -> dict[tuple[str, str], frozenset[str]]:
    paragraphs = _docx_paragraphs(CALIBRATION)
    output: dict[tuple[str, str], frozenset[str]] = {}
    current_id = ""
    current_dimension = ""
    for text in paragraphs:
        match = re.fullmatch(r"Example \d+: (\d{4}/\d{3})", text)
        if match:
            current_id = match.group(1)
        elif text == "Research Domain(s)":
            current_dimension = "Research Domains"
        elif text == "Analytical Purpose(s)":
            current_dimension = "Analytical Purposes"
        elif text.startswith("Best-supported classification: "):
            value = text.removeprefix("Best-supported classification: ")
            value = value.split("; (Defensible:", 1)[0].strip()
            output[(current_id, current_dimension)] = _sets(value, ";")
    return output


def test_calibration_docx_is_unchanged_and_contains_only_the_four_cases():
    assert CALIBRATION.stat().st_size == 198448
    assert hashlib.sha256(CALIBRATION.read_bytes()).hexdigest() == CALIBRATION_SHA256
    paragraphs = _docx_paragraphs(CALIBRATION)
    text = "\n".join(paragraphs)
    ids = re.findall(r"\b\d{4}/\d{3}\b", text)
    assert Counter(ids) == Counter({record_id: 1 for record_id in EXPECTED_IDS})
    assert sum(value.startswith("Project title: ") for value in paragraphs) == 4
    assert sum(value.startswith("Datasets used: ") for value in paragraphs) == 4
    assert paragraphs.count("Research Domain(s)") == 4
    assert paragraphs.count("Analytical Purpose(s)") == 4
    for prohibited in ("C01", "C02", "C03", "Fable", "GPT-5.5"):
        assert prohibited not in text
    with zipfile.ZipFile(CALIBRATION) as archive:
        names = archive.namelist()
        xml = "\n".join(
            archive.read(name).decode("utf-8", "replace")
            for name in names if name.endswith(".xml")
        )
    assert not any("comment" in name.lower() for name in names)
    assert "<w:ins" not in xml
    assert "<w:del" not in xml
    assert "<w:vanish" not in xml


def test_model_direction_audit_recomputes_from_complete_sets():
    calibration = _calibration_sets()
    fable_rows = {row["Record ID"]: row for row in _csv_rows(FABLE)}
    gpt_all = _csv_rows(GPT)
    gpt_rows = {row["Record ID"]: row for row in gpt_all}
    assert len(gpt_all) == 1309
    assert len(gpt_rows) == 1309
    assert {variant: sum(row["Record ID"] == variant for row in gpt_all) for variant in (
        "2023/211/a", "2023/211/b"
    )} == {"2023/211/a": 1, "2023/211/b": 1}
    assert all(record_id not in {"2023/211/a", "2023/211/b"} for record_id in EXPECTED_IDS)
    audit_rows = _csv_rows(AUDIT)
    assert len(audit_rows) == 5
    for row in audit_rows:
        record_id = row["record_id"]
        dimension = row["dimension"]
        model_field = (
            "substantive_domains" if dimension == "Research Domains"
            else "analytical_purpose"
        )
        calibration_set = calibration[(record_id, dimension)]
        fable_set = _sets(fable_rows[record_id][model_field], ";")
        gpt_set = _sets(gpt_rows[record_id][model_field], ";")
        assert _sets(row["calibration_reading"], "|") == calibration_set
        assert _sets(row["fable_reading"], "|") == fable_set
        assert _sets(row["gpt55_reading"], "|") == gpt_set
        assert row["relationship_to_fable"] == (
            "exact_complete_set_match" if calibration_set == fable_set
            else "different_complete_set"
        )
        assert row["relationship_to_gpt55"] == (
            "exact_complete_set_match" if calibration_set == gpt_set
            else "different_complete_set"
        )
    by_id = {}
    for row in audit_rows:
        by_id.setdefault(row["record_id"], set()).add(row["summary_pattern"])
    assert by_id == {
        "2019/015": {"matches_both_models"},
        "2024/248": {"matches_fable_only"},
        "2021/056": {"matches_gpt55_only"},
        "2021/038": {"narrower_than_both_models"},
    }


def test_protocol_and_logs_preserve_preformal_boundaries():
    paragraphs = _docx_paragraphs(PROTOCOL)
    protocol = "\n".join(paragraphs)
    calibration_paragraph = (
        "After the pilot, one short calibration note based on four permanently excluded "
        "pilot records was circulated simultaneously to all three coders. It clarified "
        "existing assignment rules, was framed as neither a scored answer key nor a "
        "request to revise pilot responses, and introduced no new classification rules. "
        "To assess the risk of calibrating coders toward the production model, the four "
        "shared readings were compared against both archived model outputs: one matched "
        "both models, one the production model only, one the comparison model only, and "
        "one adopted a narrower reading than either. The readings were derived from the "
        "written taxonomy rules and visible register evidence rather than selected for "
        "model agreement, so the clarifications were not systematically production-model-"
        "concordant. This is a qualitative bias check, not a statistical test, and reduces "
        "but does not eliminate the possibility that calibration affects later human–model "
        "agreement (Section 12)."
    )
    instrument_paragraph = (
        "Pilot-driven instrument changes have been resolved and documented in the "
        "instrument-change log. The formal instrument will not be frozen or used for "
        "coding until the current candidate has passed fresh live REDCap runtime QA. The "
        "GPT-5.5 comparison used for the model-direction check currently relies on the "
        "provisional 1,309-row pre-collapse snapshot and must be reverified against the "
        "canonical 1,308-row artefact when it is recovered."
    )
    assert calibration_paragraph in paragraphs
    assert instrument_paragraph in paragraphs
    assert any(
        "The trained-panel benchmark reflects coders calibrated through both the initial "
        "training and a shared post-pilot clarification note." in paragraph
        for paragraph in paragraphs
    )
    assert "candidate 0.5" not in protocol
    assert "prepared for equal circulation" not in protocol
    assert "candidate 0.3" not in instrument_paragraph
    with Path(
        "preregistration/package/09_logs_and_templates/coding_clarification_log.csv"
    ).open(encoding="utf-8", newline="") as handle:
        entries = list(csv.DictReader(handle))
    assert len(entries) == 1
    entry = entries[0]
    assert entry["circulation_status"] == "circulated"
    assert entry["circulated_at"] == "2026-07-21"
    assert entry["all_coders_notified"] == "yes"
    assert entry["simultaneous_circulation"] == "yes"
    assert entry["feedback_received_from_all_coders"] == "yes"
    assert entry["no_further_substantive_concerns"] == "yes"
    assert "coder feedback resolved" in entry["status"]
    assert "live REDCap QA pending" in entry["status"]
    assert "qualitative bias check" in entry["conclusion"]


def test_exclusions_and_manifest_entries_remain_coherent():
    exclusions = _csv_rows(EXCLUSIONS)
    assert len(exclusions) == 22
    excluded_ids = {row["record_id"] for row in exclusions}
    assert EXPECTED_IDS <= excluded_ids
    manifest_rows = _csv_rows(MANIFEST)
    by_id = {row["artifact_id"]: row for row in manifest_rows}
    assert by_id["PRO-005"]["version"] == "v0.12"
    assert by_id["PRO-005"]["current_implementation_basis"] == "true"
    assert by_id["PRO-004"]["superseded_by"] == "v0.12"
    for artifact_id in ("PRO-005", "TRN-008", "TRN-012", "TRN-014", "TRN-015", "RED-010", "LOG-003"):
        row = by_id[artifact_id]
        path = Path(row["current_path"])
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
    assert by_id["TRN-014"]["description"].startswith("Coder-facing post-pilot")
    assert "trainer answer key" in by_id["TRN-014"]["notes"]
