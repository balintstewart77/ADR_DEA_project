"""How the dashboard is served: compression, bundled assets, bind address."""

import gzip
import json
import runpy
from pathlib import Path
from unittest import mock

import pytest

from dashboard.app import app

ROOT = Path(__file__).resolve().parents[1]


def test_responses_are_compressed_for_clients_that_accept_it():
    client = app.server.test_client()
    response = client.get("/_dash-layout", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers.get("Content-Encoding") == "gzip"
    assert json.loads(gzip.decompress(response.data))  # still the same layout JSON

    plain = client.get("/_dash-layout")
    assert "Content-Encoding" not in plain.headers


def test_bootstrap_is_bundled_not_loaded_from_a_cdn():
    assert app.config.external_stylesheets == []
    page = app.server.test_client().get("/").get_data(as_text=True)
    assert "cdn.jsdelivr.net" not in page
    assert "/assets/bootstrap-5.3.6.min.css" in page
    # Asset CSS loads in filename order: Bootstrap must precede the overrides.
    assert page.index("bootstrap-5.3.6.min.css") < page.index("styles.css")
    css = (ROOT / "dashboard/assets/bootstrap-5.3.6.min.css").read_text(encoding="utf-8")
    assert "Bootstrap  v5.3.6" in css and "Licensed under MIT" in css


@pytest.mark.parametrize("env, expected", [({}, "127.0.0.1"), ({"HOST": "0.0.0.0"}, "0.0.0.0")])
def test_dev_server_binds_locally_unless_host_is_set(monkeypatch, env, expected):
    monkeypatch.delenv("HOST", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    with mock.patch("dash.Dash.run") as run:
        runpy.run_path(str(ROOT / "dashboard/app.py"), run_name="__main__")
    assert run.call_args.kwargs["host"] == expected
