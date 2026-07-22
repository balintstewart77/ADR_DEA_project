from importlib.util import module_from_spec, spec_from_file_location
import inspect
import json
from pathlib import Path
import sys

import pytest


PATH = Path(
    "preregistration/package/08_adjudication_and_release/"
    "select_adjudication_audit.py"
)
SPEC = spec_from_file_location("select_adjudication_audit", PATH)
assert SPEC and SPEC.loader
audit = module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def record_ids(n: int) -> tuple[str, ...]:
    return tuple(f"SYN-{index:03d}" for index in range(1, n + 1))


def test_n_zero_selects_nothing_without_rng():
    result = audit.select_adjudication_audit(())
    assert result.random_audit_size == 0
    assert result.random_draw_order == ()
    assert result.unique_second_reviewed_count == 0


@pytest.mark.parametrize(("n", "expected"), [(1, 1), (2, 1), (6, 2), (11, 3)])
def test_small_n_uses_ceiling(n, expected):
    assert audit.random_audit_size(n) == expected


def test_typical_n_is_twenty_percent_with_no_replacement():
    result = audit.select_adjudication_audit(record_ids(35), seed=314159)
    assert result.random_audit_size == 7
    assert len(result.random_draw_order) == len(set(result.random_draw_order)) == 7
    assert set(result.random_draw_order) <= set(result.ordered_universe)


def test_official_wrapper_has_no_seed_override_and_uses_frozen_seed():
    assert "seed" not in inspect.signature(
        audit.select_official_adjudication_audit
    ).parameters
    result = audit.select_official_adjudication_audit(record_ids(35))
    expected = audit.select_adjudication_audit(
        record_ids(35), seed=audit.SEED_ADJUDICATION_AUDIT
    )
    assert result == expected
    assert result.seed == 20260715


def test_stable_order_and_seed_determinism_ignore_input_order():
    ordered = record_ids(23)
    reverse = tuple(reversed(ordered))
    first = audit.select_adjudication_audit(ordered, seed=271828)
    second = audit.select_adjudication_audit(reverse, seed=271828)
    assert first.ordered_universe == ordered
    assert first.random_draw_order == second.random_draw_order
    assert first.random_selected_set == second.random_selected_set


def test_mandatory_overlap_does_not_reduce_random_draw():
    initial = audit.select_adjudication_audit(record_ids(20), seed=161803)
    overlap_id = initial.random_draw_order[0]
    additional_id = next(value for value in initial.ordered_universe if value not in initial.random_selected_set)
    result = audit.select_adjudication_audit(
        record_ids(20), mandatory_record_ids=(additional_id, overlap_id), seed=161803
    )
    assert result.random_audit_size == 4
    assert len(result.random_draw_order) == 4
    assert result.mandatory_review_count == 2
    assert result.overlap == (overlap_id,)
    assert result.overlap_count == 1
    assert result.unique_second_reviewed_count == 5


def test_duplicates_and_mandatory_ids_outside_universe_fail():
    with pytest.raises(ValueError, match="duplicate"):
        audit.select_adjudication_audit(("SYN-001", "SYN-001"))
    with pytest.raises(ValueError, match="outside"):
        audit.select_adjudication_audit(("SYN-001",), mandatory_record_ids=("SYN-002",))


def test_evidence_writer_records_universe_draw_sets_and_overlap(tmp_path):
    result = audit.select_official_adjudication_audit(
        record_ids(20), mandatory_record_ids=("SYN-001", "SYN-002")
    )
    target = tmp_path / "synthetic_audit_evidence.json"
    audit.write_audit_evidence(result, target)
    document = json.loads(target.read_text(encoding="utf-8"))
    assert document["ordered_universe"] == list(result.ordered_universe)
    assert document["selected_draw_order"] == list(result.random_draw_order)
    assert document["final_random_selected_set"] == list(result.random_selected_set)
    assert document["mandatory_review_set"] == list(result.mandatory_selected_set)
    assert document["overlap"] == list(result.overlap)
    assert document["unique_second_reviewed_set"] == list(result.unique_second_reviewed_set)
    assert document["counts"] == {
        "random_audit": result.random_audit_size,
        "mandatory_review": result.mandatory_review_count,
        "overlap": result.overlap_count,
        "unique_second_reviewed": result.unique_second_reviewed_count,
    }
