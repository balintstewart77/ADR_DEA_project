"""Tests for the MSS1 macro helper (synthetic data only)."""
from analysis.macro_substantive_sensitivity_exploratory import run


def test_macro_undefined_replicate_when_any_label_undefined(monkeypatch):
    monkeypatch.setattr(run, "ATTEMPTS", 3)
    point = {("a", m): 0.5 for m in run.METRICS} | {("b", m): 1.0 for m in run.METRICS}
    reps = {}
    for r in (1, 2, 3):
        for m in run.METRICS:
            reps[("a", r, m)] = 0.4
            reps[("b", r, m)] = None if (r == 2 and m == "precision") else 0.8
    out = run.macro(["a", "b"], point, reps)
    assert out["precision"] == 0.75
    assert out["precision_replicates"][1] is None
    assert abs(out["recall_replicates"][0] - 0.6) < 1e-12
    assert out["precision_interval"]["valid"] == 2 and out["precision_interval"]["invalid"] == 1


def test_macro_point_undefined_if_any_label_point_undefined(monkeypatch):
    monkeypatch.setattr(run, "ATTEMPTS", 1)
    point = {("a", m): None if m == "precision" else 0.5 for m in run.METRICS}
    reps = {("a", 1, m): 0.5 for m in run.METRICS}
    assert run.macro(["a"], point, reps)["precision"] is None
