"""Small manifest helper for deterministic analysis outputs."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _git_value(args: list[str]) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def git_state() -> dict[str, Any]:
    """Return the current commit and dirty-worktree status."""
    commit = _git_value(["rev-parse", "HEAD"])
    status = _git_value(["status", "--porcelain"])
    return {
        "commit": commit,
        "dirty": bool(status),
        "status_porcelain": status or "",
    }


def build_manifest(
    *,
    run_type: str,
    model: str | None = None,
    reference_table_version: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_type": run_type,
        "model": model,
        "reference_table_version": reference_table_version,
        "git": git_state(),
    }
    if extra:
        manifest.update(extra)
    return manifest


def write_manifest(
    output_dir: str | Path,
    *,
    run_type: str,
    model: str | None = None,
    reference_table_version: str | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Write manifest.json into an output directory and return its path."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    manifest_path = path / "manifest.json"
    manifest = build_manifest(
        run_type=run_type,
        model=model,
        reference_table_version=reference_table_version,
        extra=extra,
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path
