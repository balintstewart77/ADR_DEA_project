import csv
import re
from pathlib import Path

from analysis.validation.output_schemas import COMMON_COLUMNS, OUTPUT_SHELLS, verify_header_only_shells


ANALYSIS_PACKAGE = Path("preregistration/package/07_analysis")


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_all_prespecified_output_shells_are_header_only():
    verify_header_only_shells(ANALYSIS_PACKAGE)
    for filename in OUTPUT_SHELLS:
        with (ANALYSIS_PACKAGE / filename).open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        assert rows == [list(COMMON_COLUMNS)]


def test_figure_manifest_describes_only_future_outputs():
    rows = read_csv(ANALYSIS_PACKAGE / "figure_output_manifest.csv")
    assert len(rows) >= 8
    assert all(row["status"] == "template only" for row in rows)
    assert all(row["source_table"] in OUTPUT_SHELLS for row in rows)


def test_traceability_covers_every_section_8_subsection_and_allowed_statuses():
    rows = read_csv(ANALYSIS_PACKAGE / "protocol_analysis_traceability.csv")
    assert {row["protocol_subsection"] for row in rows} == {
        "8.1",
        "8.2",
        "8.3",
        "8.4",
        "8.5",
        "8.6",
        "8.7",
        "8.8",
        "8.9",
        "8.10",
    }
    allowed = {
        "Implemented foundation",
        "Tested",
        "Tested foundation",
        "Schema and tested foundation",
        "Vocabulary tested",
        "Output shell prepared",
        "Deferred to Batch 2",
        "Blocked pending real export schema",
        "Genuine protocol ambiguity",
        "Not applicable in Batch 1",
    }
    assert {row["implementation_status"] for row in rows} <= allowed
    assert all(row["implementation_status"] != "Genuine protocol ambiguity" for row in rows)
    assert any(row["implementation_status"] == "Deferred to Batch 2" for row in rows)


def test_synthetic_wide_fixture_uses_current_raw_export_field_names():
    fixture = Path("tests/fixtures/validation_synthetic_export.csv")
    with fixture.open(encoding="utf-8-sig", newline="") as handle:
        fixture_fields = set(csv.DictReader(handle).fieldnames or ())
    with Path("preregistration/package/06_redcap/redcap_expected_export_schema.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        expected_fields = {row["variable"] for row in csv.DictReader(handle)}
    assert fixture_fields <= expected_fields
    assert {
        "assignment_id",
        "reviewer_id",
        "source_record_id",
        "instrument_ver",
        "sc_taxonomy_fit",
        "scratch_coder_complete",
    } <= fixture_fields


def test_synthetic_fixtures_contain_no_real_register_record_ids():
    pattern = re.compile(r"\b20\d{2}/\d{3}\b")
    for path in (
        Path("tests/fixtures/validation_synthetic_export.csv"),
        Path("tests/fixtures/validation_expected_cases.yaml"),
    ):
        assert pattern.search(path.read_text(encoding="utf-8")) is None


def test_no_official_or_formal_identity_outputs_created_by_analysis_package():
    prohibited_fragments = (
        "active_sample",
        "reserve_manifest",
        "formal_assignment",
        "pilot_response",
        "redcap_export",
    )
    names = [path.name.lower() for path in ANALYSIS_PACKAGE.rglob("*") if path.is_file()]
    assert not [name for name in names if any(fragment in name for fragment in prohibited_fragments)]
