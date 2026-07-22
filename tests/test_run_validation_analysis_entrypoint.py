from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import subprocess
import sys


PATH = Path("preregistration/package/07_analysis/run_validation_analysis.py")
SPEC = spec_from_file_location("run_validation_analysis", PATH)
assert SPEC and SPEC.loader
runner = module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def test_static_check_validates_v0_14_frozen_instrument_and_closed_gate():
    result = runner.static_check()
    assert result["protocol_version"] == "v0.14"
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
    assert checked.returncode == 0, checked.stderr
    assert "gate_open: false" in checked.stdout
    refused = subprocess.run(
        [sys.executable, "-B", str(PATH), "--run"],
        check=False, capture_output=True, text=True,
    )
    assert refused.returncode == 2
    assert "not implemented in this preregistration preflight scaffold" in refused.stderr
