import csv
import hashlib
import json
from pathlib import Path

import pytest

import analysis.validation.build_private_human_model_heatmap as hm


RECORD_IDS = [f"SYN-{index:03}" for index in range(1, 11)]


def _human_inputs(first_pattern="unanimous"):
    ready = []
    agreement = []
    for index, record_id in enumerate(RECORD_IDS):
        domain_values = {
            "C01": "Education & Skills",
            "C02": "Education & Skills",
            "C03": "Education & Skills",
        }
        purpose_values = {
            "C01": "Descriptive Monitoring",
            "C02": "Descriptive Monitoring",
            "C03": "Descriptive Monitoring",
        }
        if index == 0 and first_pattern == "two_vs_one":
            domain_values["C03"] = "Health & Social Care"
            purpose_values["C03"] = "Outcome Tracking"
        if index == 0 and first_pattern == "all_sets_distinct":
            domain_values.update({
                "C02": "Health & Social Care",
                "C03": "Crime & Justice",
            })
            purpose_values.update({
                "C02": "Outcome Tracking",
                "C03": "Risk Prediction / Early Identification",
            })
        for coder in hm.CODERS:
            ready.append({
                "record_id": record_id,
                "coder_id": coder,
                "research_domains": domain_values[coder],
                "analytical_purposes": purpose_values[coder],
            })
        for dimension, values in (
            ("Research Domains", domain_values),
            ("Analytical Purposes", purpose_values),
        ):
            pattern = hm.complete_set_pattern(
                [frozenset({values[coder]}) for coder in hm.CODERS]
            )
            agreement.append({
                "record_id": record_id,
                "classification_dimension": dimension,
                "complete_set_pattern": pattern,
                **{f"{coder}_set": values[coder] for coder in hm.CODERS},
            })
    return ready, agreement


def _model_sets(domain="Education & Skills", purpose="Descriptive Monitoring"):
    return {
        (record_id, "Research Domains"): frozenset({domain})
        for record_id in RECORD_IDS
    } | {
        (record_id, "Analytical Purposes"): frozenset({purpose})
        for record_id in RECORD_IDS
    }


def _joined(first_pattern="unanimous", fable=None, gpt=None):
    ready, agreement = _human_inputs(first_pattern)
    record_ids, human, patterns = hm.load_human_rows(ready, agreement)
    return hm.build_joined_rows(
        record_ids,
        human,
        patterns,
        {
            "Fable": fable or _model_sets(),
            "GPT-5.5": gpt or _model_sets(),
        },
    )


def _cell(cells, source, dimension="Research Domains", record_id=RECORD_IDS[0]):
    return next(
        item for item in cells
        if item["record_id"] == record_id
        and item["dimension"] == dimension
        and item["source"] == source
    )


def _write_csv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_model(path, *, source, missing=False, duplicate=False, unknown=False):
    rows = []
    ids = RECORD_IDS[:-1] if missing else RECORD_IDS
    for record_id in ids:
        rows.append({
            "Record ID": record_id,
            "substantive_domains": (
                "Not a canonical label" if unknown and record_id == RECORD_IDS[0]
                else "Education & Skills"
            ),
            "analytical_purpose": "Descriptive Monitoring",
            "gpt_status": "ok",
            "validation_error": "",
        })
    if duplicate:
        rows.append(dict(rows[0]))
    columns = ["Record ID", "substantive_domains", "analytical_purpose"]
    if source == "GPT-5.5":
        columns += ["gpt_status", "validation_error"]
    _write_csv(path, columns, ({column: row[column] for column in columns} for row in rows))
    return len(rows)


def _write_metadata(path, *, source, rows=10, taxonomy="dict-1.0-rc2"):
    expected = {
        "Fable": ("claude-fable-5", "validation_release_fable5_full_register"),
        "GPT-5.5": ("gpt-5.5", "cross_model_hard_case_disagreement_stratum_not_release"),
    }
    model, run_type = expected[source]
    path.write_text(json.dumps({
        "model": model,
        "run_type": run_type,
        "prompt_version": taxonomy,
        "taxonomy_version": taxonomy,
        "n_projects": rows,
    }), encoding="utf-8")


def test_all_ten_records_join_once_to_each_model(tmp_path):
    for source in hm.MODELS:
        path = tmp_path / f"{source}.csv"
        _write_model(path, source=source)
        values, count = hm.load_model_rows(
            path, source=source, expected_record_ids=set(RECORD_IDS)
        )
        assert count == 10
        assert len(values) == 20


def test_missing_model_row_fails(tmp_path):
    path = tmp_path / "fable.csv"
    _write_model(path, source="Fable", missing=True)
    with pytest.raises(hm.HumanModelHeatmapError, match="Missing Fable"):
        hm.load_model_rows(path, source="Fable", expected_record_ids=set(RECORD_IDS))


def test_duplicate_model_row_fails(tmp_path):
    path = tmp_path / "gpt.csv"
    _write_model(path, source="GPT-5.5", duplicate=True)
    with pytest.raises(hm.HumanModelHeatmapError, match="Duplicate GPT-5.5"):
        hm.load_model_rows(path, source="GPT-5.5", expected_record_ids=set(RECORD_IDS))


def test_unknown_taxonomy_label_fails(tmp_path):
    path = tmp_path / "fable.csv"
    _write_model(path, source="Fable", unknown=True)
    with pytest.raises(hm.HumanModelHeatmapError, match="Unknown taxonomy label"):
        hm.load_model_rows(path, source="Fable", expected_record_ids=set(RECORD_IDS))


def test_taxonomy_version_mismatch_fails(tmp_path):
    path = tmp_path / "metadata.json"
    _write_metadata(path, source="Fable", taxonomy="dict-old")
    with pytest.raises(hm.HumanModelHeatmapError, match="taxonomy-version mismatch"):
        hm.verify_model_metadata(
            path,
            source="Fable",
            expected_taxonomy="dict-1.0-rc2",
            row_count=10,
        )


def test_unanimous_humans_matching_and_differing_models():
    gpt = _model_sets()
    gpt[(RECORD_IDS[0], "Research Domains")] = frozenset({"Health & Social Care"})
    cells = hm.build_heatmap_cells(_joined(gpt=gpt))
    assert _cell(cells, "Fable")["cell_color"] == "green"
    assert _cell(cells, "GPT-5.5")["cell_color"] == "red"
    assert all(_cell(cells, coder)["cell_color"] == "green" for coder in hm.CODERS)


def test_two_vs_one_model_matching_pair_and_dissenter():
    fable = _model_sets()
    gpt = _model_sets()
    gpt[(RECORD_IDS[0], "Research Domains")] = frozenset({"Health & Social Care"})
    cells = hm.build_heatmap_cells(_joined("two_vs_one", fable=fable, gpt=gpt))
    assert _cell(cells, "Fable")["cell_color"] == "green"
    assert _cell(cells, "GPT-5.5")["cell_color"] == "red"
    assert _cell(cells, "C03")["agreement_state"] == "human_lone_dissenter"


def test_all_human_sets_distinct_model_matching_c01_and_unique():
    fable = _model_sets()
    gpt = _model_sets()
    gpt[(RECORD_IDS[0], "Research Domains")] = frozenset({"Business & Productivity"})
    cells = hm.build_heatmap_cells(_joined("all_sets_distinct", fable=fable, gpt=gpt))
    assert _cell(cells, "Fable") | {"annotation": "=C01"} == _cell(cells, "Fable")
    assert _cell(cells, "Fable")["cell_color"] == "amber"
    assert _cell(cells, "GPT-5.5")["annotation"] == "unique"
    assert _cell(cells, "GPT-5.5")["cell_color"] == "amber"


def test_fable_and_gpt_identical_and_different_summary():
    gpt = _model_sets()
    gpt[(RECORD_IDS[0], "Research Domains")] = frozenset({"Health & Social Care"})
    summary = hm.build_comparison_summary(_joined(gpt=gpt))
    domains = next(
        row for row in summary
        if row["comparison_type"] == "model_to_model"
        and row["dimension"] == "Research Domains"
    )
    purposes = next(
        row for row in summary
        if row["comparison_type"] == "model_to_model"
        and row["dimension"] == "Analytical Purposes"
    )
    assert domains["fable_gpt_exact_complete_set_agreement_count"] == 9
    assert purposes["fable_gpt_exact_complete_set_agreement_count"] == 10


def test_exactly_ten_by_ten_and_one_hundred_classified_cells():
    cells = hm.build_heatmap_cells(_joined())
    assert len({cell["record_id"] for cell in cells}) == 10
    assert len({(cell["dimension"], cell["source"]) for cell in cells}) == 10
    assert len(cells) == 100
    assert all(cell["cell_color"] in {"green", "red", "amber"} for cell in cells)


def test_full_outputs_are_restricted_and_source_masked_inputs_unchanged(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(hm, "REPOSITORY_ROOT", tmp_path)
    ready, agreement = _human_inputs()
    ready_path = tmp_path / "shared" / "pilot_analysis_ready.csv"
    agreement_path = tmp_path / "shared" / "pilot_record_agreement.csv"
    _write_csv(
        ready_path,
        ["record_id", "coder_id", "research_domains", "analytical_purposes"],
        ready,
    )
    _write_csv(
        agreement_path,
        [
            "record_id", "classification_dimension", "complete_set_pattern",
            "C01_set", "C02_set", "C03_set",
        ],
        agreement,
    )
    pilot_raw = tmp_path / "pilot_raw.csv"
    _write_csv(
        pilot_raw,
        ["source_record_id", "production_ver"],
        ({
            "source_record_id": record_id,
            "production_ver": "dea-validation-production-test-fable5-dict-1.0-rc2",
        } for record_id in RECORD_IDS),
    )
    fable = tmp_path / "fable.csv"
    gpt = tmp_path / "gpt.csv"
    _write_model(fable, source="Fable")
    _write_model(gpt, source="GPT-5.5")
    fable_meta = tmp_path / "fable.json"
    gpt_meta = tmp_path / "gpt.json"
    _write_metadata(fable_meta, source="Fable")
    _write_metadata(gpt_meta, source="GPT-5.5")
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (ready_path, agreement_path)
    }
    output_dir = tmp_path / "preregistration_restricted" / "pilot_private_review"
    result = hm.build_outputs(
        ready_path=ready_path,
        agreement_path=agreement_path,
        pilot_raw_path=pilot_raw,
        fable_path=fable,
        fable_metadata_path=fable_meta,
        gpt55_path=gpt,
        gpt55_metadata_path=gpt_meta,
        output_dir=output_dir,
    )
    assert result["heatmap_cells"] == 100
    assert {path.name for path in output_dir.iterdir()} == {
        "pilot_human_model_classifications.csv",
        "pilot_human_model_comparison_summary.csv",
        "pilot_model_alignment_with_human_disagreements.csv",
        "pilot_human_model_expanded_heatmap.png",
        "pilot_human_model_heatmap_legend.md",
    }
    assert before == {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (ready_path, agreement_path)
    }
    with pytest.raises(hm.HumanModelHeatmapError):
        hm.validate_private_output_path(tmp_path / "shared")
