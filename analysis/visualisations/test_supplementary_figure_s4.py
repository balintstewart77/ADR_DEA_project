"""Supplementary Figure S4: extraction, hard-stop checks, caption and a render smoke test."""

import shutil

import pytest

from analysis.visualisations import build_supplementary_figure_s4 as s4


def test_extraction_reads_the_four_panels_verbatim():
    rows = s4.extract()
    assert len(rows) == 2 * 2 * (6 + 3)
    first = next(r for r in rows if r["population"] == "baseline" and r["dimension"] == "Research Domains" and r["quantity"] == "alpha_AB")
    assert first["source_table_id"] == "PWA1T001" and first["parsed_value"] == "0.5209151240617209"
    assert first["pair"] == "C01 versus C02" and first["estimate_status"] == "R" and first["interval_status"] == "R"
    d_b = next(r for r in rows if r["population"] == "hard_case" and r["dimension"] == "Analytical Purposes" and r["quantity"] == "D_B")
    assert d_b["source_table_id"] == "PWA1T024" and d_b["pair"] == "Fable 5 replacing C02"


def test_checks_pass_on_the_committed_run():
    checks = s4.run_checks(s4.extract())
    assert checks["check_5_orderings"]["agree_all_cells"] == 7 and checks["check_5_orderings"]["cells_total"] == 8
    assert [c["dimension"] for c in checks["check_5_orderings"]["exceptions"]] == ["Demographic disparities / equity"]
    assert all(abs(v["recomputed"] - v["exported"]) <= 1e-12 for v in checks["check_4_D_recomputed"]["values"])


def test_a_changed_value_is_caught(tmp_path):
    source = tmp_path / "pairwise"
    shutil.copytree(s4.SOURCE_DIR, source, ignore=shutil.ignore_patterns("__pycache__"))
    path = source / "PWA1T002.csv"
    path.write_text(path.read_text(encoding="utf-8").replace("0.6062800556575332", "0.6062800556575333", 1), encoding="utf-8")
    rows = s4.extract(source)
    with pytest.raises(s4.CheckFailed, match="check 1|check 4"):
        s4.run_checks(rows, source)


def test_ascending_order_marks_exact_ties():
    assert s4.ascending_order({"A": 0.1, "B": -0.2, "C": 0.3}) == "B < A < C"
    assert s4.ascending_order({"A": 0.0, "B": 0.0, "C": 0.047}) == "A = B < C"


def test_caption_section_is_inserted_once_before_the_supplementary_tables(tmp_path):
    captions = tmp_path / "draft_captions_pass2.md"
    captions.write_text(
        "# Draft captions — pass 3\n\n## Supplementary Figure S3\n\ntext\n\n## Supplementary Table S1a\n\ntable\n",
        encoding="utf-8",
    )
    s4.update_captions(captions, ["first bullet"])
    s4.update_captions(captions, ["second bullet"])
    text = captions.read_text(encoding="utf-8")
    assert text.count("## Supplementary Figure S4") == 1 and "second bullet" in text and "first bullet" not in text
    assert text.index("## Supplementary Figure S3") < text.index("## Supplementary Figure S4") < text.index("## Supplementary Table S1a")


def test_render_and_text_checks(tmp_path):
    rows = s4.extract()
    checks = s4.run_checks(rows)
    metrics, keys = s4.render(rows, tmp_path / s4.SLUG, "DejaVu Sans")
    assert keys["status"] == "PASS"
    assert (tmp_path / f"{s4.SLUG}.svg").exists() and (tmp_path / f"{s4.SLUG}.png").exists()
    result = s4.text_checks(metrics, s4.caption_bullets(rows, checks))
    assert result["status"] == "PASS" and metrics["minimum_effective_pt"] >= 8.0
