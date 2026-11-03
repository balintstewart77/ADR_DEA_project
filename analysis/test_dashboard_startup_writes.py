"""The dashboard must start without writing files (read-only deployments)."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Fail on any DataFrame CSV write, then import the whole app in a fresh
# interpreter so module-level loading runs exactly as it does at startup.
_IMPORT_APP_WITHOUT_WRITES = """
import pandas as pd

def _refuse(*args, **kwargs):
    raise AssertionError("dashboard startup wrote a CSV")

pd.DataFrame.to_csv = _refuse
import dashboard.app  # noqa: F401
print("ok")
"""


def test_dashboard_import_writes_no_csv_files():
    result = subprocess.run(
        [sys.executable, "-c", _IMPORT_APP_WITHOUT_WRITES],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip().splitlines()[-1] == "ok"
