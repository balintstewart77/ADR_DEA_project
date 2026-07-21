import csv
import hashlib
import json
import subprocess
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

from analysis.crossmodel_comparison import CANONICAL_TAGS, split_label_set
from analysis.validation.schema import DOMAIN_LABELS, PURPOSE_LABELS, UNCLEAR


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
RETAINED_PAIRS = {"2020/030", "2022/036", "2024/014", "2024/095"}


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


def test_protocol_and_formal_docs_no_longer_have_a_recovery_blocker():
    protocol = _docx_text(
        Path("preregistration/package/00_protocol/Validation_Protocol_PreReg_v0.12.docx")
    )
    assert (
        "The model-direction check was reverified against the frozen canonical "
        "1,308-row GPT-5.5 artefact before preregistration."
    ) in protocol
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
