import csv
import copy
import hashlib
import json
import subprocess
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from analysis.crossmodel_comparison import CANONICAL_TAGS, split_label_set
from analysis.llm_theme_analysis_v3 import _build_static_prompt
from analysis.validation.schema import DOMAIN_LABELS, PURPOSE_LABELS, UNCLEAR
from analysis.register_manifest import (
    CURRENT_POINTER,
    FROZEN_CLEANED_PATH,
    FROZEN_CLEANED_SHA256,
    FROZEN_SOURCE_CSV_SHA256,
    FROZEN_SOURCE_XLSX_SHA256,
    FROZEN_VALIDATION_POINTER,
    _validate_v2_manifest,
    load_manifest,
    snapshot_record,
    verify_frozen_validation_binding,
)


RELEASE = Path(
    "analysis/releases/gpt55_crossmodel_20260707/gpt55_classifications.csv"
)
ORIGINAL = Path("analysis/outputs/gpt55_classifications.csv")
POPULATION = Path(
    "preregistration/package/01_source_and_cleaning/"
    "dea_accredited_projects_20260601_cleaned_1308.csv"
)
RECEIPT = RELEASE.with_name("release_receipt.json")
EXPECTED_SHA256 = "5bb4379174e1c9b9cf7faf611712c53648bc57eea7ba1d28127ecedab16b5ded"
POPULATION_SHA256 = "a334bd7f06e23db4cc8497274b36c0c483f6f0db7b079013e18729cd189ff9c1"
ORIGINAL_XLSX = Path("data/dea_accredited_projects_20260601.xlsx")
ORIGINAL_CSV = Path("data/dea_accredited_projects_20260601.csv")
RETAINED_PAIRS = {"2020/030", "2022/036", "2024/014", "2024/095"}
PROMPT = Path(
    "preregistration/package/02_taxonomy_prompt_and_model/"
    "production_prompt_dict-1.0-rc2.txt"
)
PROMPT_SHA256 = "8fd34b5e80a748dce114ebe636d9861662c4cd8d3f0ce053ef458b95d9593861"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _docx_text(path: Path) -> str:
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    return "\n".join(
        "".join(node.text or "" for node in paragraph.iter(namespace + "t"))
        for paragraph in root.iter(namespace + "p")
    )


def test_release_is_the_exact_recovered_source_bytes():
    source = ORIGINAL.read_bytes()
    release = RELEASE.read_bytes()
    assert source == release
    assert len(release) == 920480
    assert release.startswith(b"\xef\xbb\xbf")
    assert hashlib.sha256(release).hexdigest() == EXPECTED_SHA256
    assert release.count(b"\r\n") == 1309
    assert release.count(b"\n") - release.count(b"\r\n") == 333


def test_standalone_prompt_is_byte_exact_frozen_builder_output():
    stored = PROMPT.read_bytes()
    rendered = _build_static_prompt().encode("utf-8")
    assert stored == rendered
    assert len(stored) == len(rendered) == 28551
    assert hashlib.sha256(stored).hexdigest() == PROMPT_SHA256


def test_release_matches_the_canonical_population_and_duplicate_structure():
    assert hashlib.sha256(POPULATION.read_bytes()).hexdigest() == POPULATION_SHA256
    gpt = _rows(RELEASE)
    population = _rows(POPULATION)
    gpt_ids = [row["Record ID"] for row in gpt]
    population_ids = [row["Record ID"] for row in population]
    assert len(gpt) == len(population) == 1308
    assert len(set(gpt_ids)) == len(set(population_ids)) == 1308
    assert set(gpt_ids) == set(population_ids)
    assert all(
        record_id == record_id.strip()
        and not any(ord(character) <= 31 or ord(character) == 127 for character in record_id)
        for record_id in gpt_ids
    )
    assert len({row["Project ID"] for row in gpt}) == 1304
    assert len({row["Project ID"] for row in population}) == 1304
    assert Counter(row["Project ID"] for row in gpt) == Counter(
        row["Project ID"] for row in population
    )
    assert gpt_ids.count("2023/211") == 1
    assert "2023/211/a" not in gpt_ids and "2023/211/b" not in gpt_ids
    for project_id in RETAINED_PAIRS:
        assert {f"{project_id}/a", f"{project_id}/b"} <= set(gpt_ids)
    doubled = {
        project_id
        for project_id, count in Counter(row["Project ID"] for row in gpt).items()
        if count == 2
    }
    assert doubled == RETAINED_PAIRS


def test_frozen_validation_source_binding_is_immutable_and_independent_of_live_pointer():
    assert verify_frozen_validation_binding() == {
        "raw_xlsx_sha256": FROZEN_SOURCE_XLSX_SHA256,
        "canonical_csv_sha256": FROZEN_SOURCE_CSV_SHA256,
        "cleaned_population_sha256": FROZEN_CLEANED_SHA256,
    }
    manifest = load_manifest()
    live = snapshot_record(manifest, CURRENT_POINTER)
    frozen = snapshot_record(manifest, FROZEN_VALIDATION_POINTER)
    binding = manifest["pointers"][FROZEN_VALIDATION_POINTER]
    assert live["canonical_csv_sha256"] == (
        "918117144c4b01908dfdefc411c2baef81431cf3f0dd42d0c20a1b7d9e942acd"
    )
    assert binding["raw_xlsx_sha256"] == FROZEN_SOURCE_XLSX_SHA256
    assert binding["canonical_csv_sha256"] == FROZEN_SOURCE_CSV_SHA256
    assert binding["cleaned_population_sha256"] == FROZEN_CLEANED_SHA256
    assert binding["cleaned_population_path"] == FROZEN_CLEANED_PATH
    assert frozen["raw_xlsx_sha256"] == FROZEN_SOURCE_XLSX_SHA256
    assert frozen["canonical_csv_sha256"] == FROZEN_SOURCE_CSV_SHA256
    assert frozen["raw_xlsx_path"] == ORIGINAL_XLSX.name
    assert frozen["canonical_csv_path"] == ORIGINAL_CSV.name
    assert live["snapshot_id"] != frozen["snapshot_id"]
    assert hashlib.sha256(ORIGINAL_XLSX.read_bytes()).hexdigest() == FROZEN_SOURCE_XLSX_SHA256
    canonical_lf_bytes = ORIGINAL_CSV.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(canonical_lf_bytes).hexdigest() == FROZEN_SOURCE_CSV_SHA256
    assert hashlib.sha256(POPULATION.read_bytes()).hexdigest() == FROZEN_CLEANED_SHA256
    assert POPULATION_SHA256 == FROZEN_CLEANED_SHA256

    repointed = copy.deepcopy(manifest)
    repointed["pointers"][FROZEN_VALIDATION_POINTER] = copy.deepcopy(
        repointed["pointers"][CURRENT_POINTER]
    )
    repointed["pointers"][FROZEN_VALIDATION_POINTER].update({
        "cleaned_population_path": POPULATION.as_posix(),
        "cleaned_population_sha256": POPULATION_SHA256,
    })
    with pytest.raises(ValueError, match="Frozen validation source pointer changed"):
        _validate_v2_manifest(repointed, "mutated test manifest")


def test_validation_workflows_do_not_resolve_through_mutable_live_pointer():
    from analysis.validation import owner_sampling_frame
    from scripts import draw_validation_samples, generate_formal_validation_assignments

    manifest = load_manifest()
    frozen_input = manifest["pointers"][FROZEN_VALIDATION_POINTER][
        "cleaned_population_path"
    ]
    assert frozen_input == POPULATION.as_posix()
    declared_inputs = (
        draw_validation_samples.REAL_CLEANED_PATH.as_posix(),
        generate_formal_validation_assignments.POPULATION.as_posix(),
        owner_sampling_frame.FROZEN_POPULATION.relative_to(Path.cwd()).as_posix(),
    )
    assert declared_inputs == (frozen_input, frozen_input, frozen_input)
    for path in (
        Path("scripts/draw_validation_samples.py"),
        Path("scripts/generate_formal_validation_assignments.py"),
        Path("analysis/validation/owner_sampling_frame.py"),
    ):
        text = path.read_text(encoding="utf-8")
        assert "current_latest_revision" not in text
        assert "CURRENT_POINTER" not in text
        assert POPULATION.name in text

    guarded_consumers = {
        Path("scripts/draw_validation_samples.py"): "inputs = validate_inputs(",
        Path("scripts/generate_formal_validation_assignments.py"): "metadata = generate(",
        Path("analysis/validation/owner_sampling_frame.py"): "frozen = pd.read_csv(",
    }
    for path, consumption in guarded_consumers.items():
        text = path.read_text(encoding="utf-8")
        guard = text.rfind("verify_frozen_validation_binding()", 0, text.index(consumption))
        assert guard >= 0, f"{path} consumes the frozen population without the shared guard"

    changed_live = copy.deepcopy(manifest)
    changed_live["pointers"][CURRENT_POINTER] = {
        "snapshot_id": manifest["content_snapshots"][0]["snapshot_id"],
        "raw_xlsx_sha256": manifest["content_snapshots"][0]["raw_xlsx_sha256"],
        "canonical_csv_sha256": manifest["content_snapshots"][0]["canonical_csv_sha256"],
    }
    assert changed_live["pointers"][FROZEN_VALIDATION_POINTER] == (
        manifest["pointers"][FROZEN_VALIDATION_POINTER]
    )
    assert changed_live["pointers"][FROZEN_VALIDATION_POINTER][
        "cleaned_population_path"
    ] == frozen_input


def test_each_frozen_hash_entry_is_required_and_directly_protected():
    manifest = load_manifest()
    expected = {
        "raw_xlsx_sha256": FROZEN_SOURCE_XLSX_SHA256,
        "canonical_csv_sha256": FROZEN_SOURCE_CSV_SHA256,
        "cleaned_population_sha256": FROZEN_CLEANED_SHA256,
    }
    assert {
        key: manifest["pointers"][FROZEN_VALIDATION_POINTER][key]
        for key in expected
    } == expected
    for key in expected:
        changed = copy.deepcopy(manifest)
        changed["pointers"][FROZEN_VALIDATION_POINTER][key] = "0" * 64
        with pytest.raises(ValueError):
            _validate_v2_manifest(changed, f"mutated {key}")


def test_release_schema_and_dict_rc2_values_are_valid():
    expected_header = [
        "Project ID", "Record ID", "Title", "Datasets Used",
        "Accreditation Date", "Year", "gpt_status", "substantive_domains",
        "analytical_purpose", "cross_cutting_tags", "rationale",
        "validation_error", "raw_classification",
    ]
    with RELEASE.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == expected_header
        rows = list(reader)
    population = {row["Record ID"]: row for row in _rows(POPULATION)}
    for row in rows:
        record_id = row["Record ID"]
        assert row["gpt_status"] == "ok"
        assert not row["validation_error"].strip()
        assert all(row[field].strip() for field in (
            "Project ID", "Record ID", "Title", "substantive_domains",
            "analytical_purpose", "rationale",
        ))
        domains = split_label_set(
            row["substantive_domains"], field="domain", allowed=DOMAIN_LABELS
        )
        purposes = split_label_set(
            row["analytical_purpose"], field="purpose", allowed=PURPOSE_LABELS
        )
        split_label_set(row["cross_cutting_tags"], field="tag", allowed=CANONICAL_TAGS)
        assert domains and purposes
        assert not (UNCLEAR in domains and len(domains) > 1)
        assert not (UNCLEAR in purposes and len(purposes) > 1)
        assert len(purposes) <= 2
        if record_id == "2023/214":
            assert row["Datasets Used"] == population[record_id]["Datasets Used"] == ""


def test_receipt_attributes_and_formal_pointers_designate_the_release():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    artefact = receipt["artefact"]
    assert artefact["sha256"] == EXPECTED_SHA256
    assert artefact["row_count"] == 1308
    assert artefact["unique_record_id_count"] == 1308
    assert artefact["unique_project_id_count"] == 1304
    attributes = subprocess.run(
        ["git", "check-attr", "text", "eol", "--", str(RELEASE)],
        check=True, capture_output=True, text=True,
    ).stdout
    assert "text: unset" in attributes and "eol: unset" in attributes
    release_path = RELEASE.as_posix()
    for path in (
        Path("analysis/regenerate_crossmodel_evidence.py"),
        Path("analysis/validation/build_private_human_model_heatmap.py"),
        Path("analysis/validation/build_private_pilot_case_review.py"),
    ):
        text = path.read_text(encoding="utf-8")
        assert release_path in text
        assert "classifications_1309_precollapse_PROVISIONAL.csv" not in text


def test_lean_protocol_and_formal_docs_have_no_recovery_blocker():
    protocol = _docx_text(
        Path("preregistration/package/00_protocol/Validation_Protocol_PreReg_v0.15.docx")
    )
    assert "must be reverified against the canonical 1,308-row artefact" not in protocol
    formal_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            Path("preregistration/package/03_preexisting_model_evidence/README.md"),
            Path("preregistration/package/05_training_and_pilot/README.md"),
            Path("preregistration/package/02_taxonomy_prompt_and_model/production_release_manifest.yaml"),
        )
    )
    assert RELEASE.as_posix() in formal_text
    assert "must be reverified" not in formal_text
    assert "provisional_1309_intermediate_required: false" in formal_text
