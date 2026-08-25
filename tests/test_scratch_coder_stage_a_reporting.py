from __future__ import annotations

import pandas as pd

from analysis.scratch_coder_stage_a.config import OUTPUT_DIR
from analysis.scratch_coder_stage_a.report import regenerate_headline_summary


def test_headline_regeneration_renders_existing_hard_case_rows_deterministically():
    path = regenerate_headline_summary()
    first = path.read_bytes()
    assert regenerate_headline_summary().read_bytes() == first
    text = first.decode("utf-8")

    assert "### Random-baseline replacement analysis" in text
    assert "### Hard-case replacement analysis — diagnostic" in text
    assert "deliberately enriched for cross-model disagreement and is non-representative" in text
    assert "do not activate or override the preregistered population-level review triggers" in text

    panels = pd.read_csv(OUTPUT_DIR / "replacement_panel_results.csv")
    deltas = pd.read_csv(OUTPUT_DIR / "replacement_delta_results.csv")
    section = text.split("### Hard-case replacement analysis — diagnostic", 1)[1].split("### Preregistered exposure sensitivity", 1)[0]
    assert "Mechanical review-trigger indicators" not in section
    assert all(name not in section for name in ("domain_only", "purpose_only", "both"))
    for dimension in (
        "Research Domains", "Analytical Purposes",
        "Demographic disparities / equity", "COVID-19 & Pandemic",
    ):
        panel = panels[(panels.population == "hard_case") & (panels.dimension == dimension)]
        delta = deltas[(deltas.population == "hard_case") & (deltas.dimension == dimension) & (deltas.delta == "delta_min")].iloc[0]
        assert len(panel) == 4 and set(panel.n_records) == {75}
        assert int(delta.n_records) == 75
        assert f"| {dimension} | 75 |" in section
        assert f"{float(delta.point_estimate):.3f}" in section
        assert f"[{float(delta.ci_lower):.3f}, {float(delta.ci_upper):.3f}]" in section
