from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import subprocess
import sys

import pytest


PATH = Path("preregistration/package/07_analysis/run_validation_analysis.py")
SPEC = spec_from_file_location("run_validation_analysis", PATH)
assert SPEC and SPEC.loader
runner = module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


@pytest.mark.git_history
def test_historical_static_check_validates_v0_15_and_closed_gate(git_snapshot, monkeypatch):
    source_root = runner.ROOT
    snapshot = git_snapshot("6337c3e")
    for name, path in list(vars(runner).items()):
        if isinstance(path, Path) and path.is_relative_to(source_root):
            monkeypatch.setattr(runner, name, snapshot / path.relative_to(source_root))
    result = runner.static_check()
    assert result["protocol_version"] == "v0.15"
    assert result["instrument_version"] == "redcap-candidate-0.7"
    assert result["dictionary_fields"] == 150
    assert result["bootstrap_replicates"] == 2000
    assert result["percentile_method"].startswith("Hyndman-Fan Type 7")
    assert result["gate_open"] is False


def test_check_cli_is_read_only_and_run_is_explicitly_not_implemented():
    checked = subprocess.run(
        [sys.executable, "-B", str(PATH), "--check"],
        check=False, capture_output=True, text=True,
    )
    assert checked.returncode == 1
    assert "v0.15 must remain a review_candidate" in checked.stderr
    refused = subprocess.run(
        [sys.executable, "-B", str(PATH), "--run"],
        check=False, capture_output=True, text=True,
    )
    assert refused.returncode == 2
    assert "not implemented in this preregistration preflight scaffold" in refused.stderr
