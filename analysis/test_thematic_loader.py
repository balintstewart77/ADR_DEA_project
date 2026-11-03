"""Thematic release loading: missing files degrade, logic errors surface."""

import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from dashboard.config import CLASSIFICATION_DIR
from dashboard.data import thematic

ROOT = Path(__file__).resolve().parents[1]


def test_missing_release_is_unavailable_with_the_full_structure(tmp_path):
    data, available = thematic.load_thematic_data(str(tmp_path / "missing"))
    real, real_available = thematic.load_thematic_data(CLASSIFICATION_DIR)
    assert real_available is True and available is False
    assert set(data) == set(real)
    assert data["THEMATIC_PROJECT_COUNT"] == 0
    assert data["df_thematic_projects"].empty
    assert all(option["value"] == "ALL" for option in data["_THEMATIC_DOMAIN_OPTIONS"])


def test_a_malformed_release_raises_instead_of_hiding_the_tab(tmp_path):
    release = tmp_path / "release"
    shutil.copytree(CLASSIFICATION_DIR, release)
    classifications = release / "layer_classifications.csv"
    frame = pd.read_csv(classifications, encoding="utf-8-sig")
    frame.drop(columns=["substantive_domains"]).to_csv(
        classifications, index=False, encoding="utf-8-sig",
    )
    with pytest.raises(KeyError, match="substantive_domains"):
        thematic.load_thematic_data(str(release))


def test_dashboard_starts_without_a_classification_release(tmp_path):
    script = (
        "import dashboard.config as config\n"
        f"config.CLASSIFICATION_DIR = {str(tmp_path / 'missing')!r}\n"
        "import dashboard.app\n"
        "from dashboard.data import thematic\n"
        "assert thematic.THEMATIC_DATA_AVAILABLE is False\n"
        "print('ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip().splitlines()[-1] == "ok"
