from __future__ import annotations

from collections import Counter

from scripts import generate_formal_validation_assignments as assignments


def active_rows(count: int, family: str, prefix: str) -> list[dict[str, str]]:
    return [
        {
            "record_id": f"{prefix}-{index:03d}",
            "official_project_id": f"PROJECT-{prefix}-{index:03d}",
            "sample_family": family,
            "sample_status": "active",
            "hard_case_stratum": "domain_only" if family == "hard_case" else "",
            "draw_stage": "3_hard_active" if family == "hard_case" else "1_baseline_active",
            "draw_rank": str(index),
            "validation_included": "yes",
        }
        for index in range(1, count + 1)
    ]


def test_deterministic_three_coder_assignment_contract() -> None:
    active = assignments.validate_active_rows(
        active_rows(150, "baseline", "BASE"),
        active_rows(75, "hard_case", "HARD"),
    )
    population = {
        row["record_id"]: {
            "official_project_id": row["official_project_id"],
            "project_title": f"Public title {row['record_id']}",
            "datasets_used": "Public dataset description",
        }
        for row in active
    }
    first_import, first_crosswalk = assignments.build_rows(active, population)
    second_import, second_crosswalk = assignments.build_rows(active, population)
    assert first_import == second_import
    assert first_crosswalk == second_crosswalk
    assertions = assignments.validate_generated(first_import, first_crosswalk, active)
    assert all(assertions.values())
    assert Counter(row["reviewer_id"] for row in first_import) == {
        "C01": 225,
        "C02": 225,
        "C03": 225,
    }
    assert len({row["assignment_id"] for row in first_import}) == 675


def test_import_contract_omits_sampling_model_and_response_fields() -> None:
    assignments.validate_import_schema(
        assignments.canonical_header(assignments.ROOT / assignments.IMPORT_TEMPLATE),
        assignments.dictionary_fields(assignments.ROOT / assignments.DATA_DICTIONARY),
    )
    assert not (assignments.FORBIDDEN_IMPORT_COLUMNS & set(assignments.IMPORT_COLUMNS))
    assert not any(column.startswith(("sc_", "po_")) for column in assignments.IMPORT_COLUMNS)
    assert assignments.CODER_SEEDS == {"C01": 101, "C02": 102, "C03": 103}


def test_builder_never_names_reserve_inputs() -> None:
    source = (assignments.ROOT / "scripts/generate_formal_validation_assignments.py").read_text(
        encoding="utf-8"
    )
    assert "baseline_reserve.csv" not in source
    assert "hard_reserve.csv" not in source
