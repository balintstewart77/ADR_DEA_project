import csv
import io
import subprocess
import tempfile
import zipfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def git_snapshot(tmp_path_factory):
    snapshots = {}

    def extract(commit):
        if commit not in snapshots:
            result = subprocess.run(
                ["git", "archive", "--format=zip", commit], cwd=Path(__file__).parent,
                capture_output=True, check=True,
            )
            destination = tmp_path_factory.mktemp("historical_inputs")
            with zipfile.ZipFile(io.BytesIO(result.stdout)) as archive:
                archive.extractall(destination)
            snapshots[commit] = destination
        return snapshots[commit]

    return extract


def pytest_addoption(parser):
    parser.addoption("--require-private", action="store_true", help="Fail if a marked private input is missing")
    parser.addoption("--require-history", action="store_true", help="Require a full Git checkout for provenance tests")
    parser.addoption("--require-browser", action="store_true", help="Fail if Playwright or Chromium is unavailable")


def pytest_configure(config):
    from dashboard import config as dashboard_config

    outputs = tempfile.TemporaryDirectory(prefix="adr_pytest_cleaning_")
    patch = pytest.MonkeyPatch()
    patch.setattr(dashboard_config, "CLEANING_OUTPUT_DIR", outputs.name)
    config.add_cleanup(outputs.cleanup)
    config.add_cleanup(patch.undo)


def pytest_runtest_setup(item):
    root = Path(__file__).parent
    for marker in item.iter_markers("private_data"):
        missing = []
        for value in marker.args:
            if str(value).startswith("manifest:"):
                with (root / "preregistration/preregistration_artifact_manifest.csv").open(encoding="utf-8") as handle:
                    row = next(row for row in csv.DictReader(handle) if row["artifact_id"] == value.split(":", 1)[1])
                value = row["current_path"]
            if not (root / value).is_file():
                missing.append(str(value))
        if missing:
            reason = "Private/untracked inputs unavailable: " + ", ".join(missing)
            if item.config.getoption("--require-private"):
                pytest.fail(reason)
            pytest.skip(reason)
    if item.get_closest_marker("git_history"):
        result = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"], cwd=root,
            capture_output=True, text=True, check=False,
        )
        if result.returncode or result.stdout.strip() != "false":
            reason = "Historical provenance requires a full Git checkout (fetch-depth: 0)"
            if item.config.getoption("--require-history"):
                pytest.fail(reason)
            pytest.skip(reason)
