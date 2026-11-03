"""Cached HTTP client, source parsers and pilot sampling (no network)."""

import json

import pandas as pd
import pytest
import requests
from requests.structures import CaseInsensitiveDict

from analysis.publication_linkage import http_client
from analysis.publication_linkage.http_client import (
    BudgetExhausted,
    CachedClient,
    OpenAlexBudget,
    QueryRejected,
    SourceBlocked,
)
from analysis.publication_linkage.pilot import allocate, allocate_two_stage
from analysis.publication_linkage.sources.core import CoreSource
from analysis.publication_linkage.sources.europepmc import EuropePmcSource, xml_to_text
from analysis.publication_linkage.sources.govuk import GovUkSource
from analysis.publication_linkage.sources.gtr import GtrSource
from analysis.publication_linkage.sources.openalex import (
    OpenAlexSource,
    institutions_compatible,
    reconstruct_abstract,
)


def response(status=200, body=None, headers=None):
    r = requests.Response()
    r.status_code = status
    r._content = json.dumps(body if body is not None else {}).encode() if not isinstance(body, str) else body.encode()
    r.headers = CaseInsensitiveDict(headers or {"Content-Type": "application/json"})
    return r


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(http_client.time, "sleep", lambda seconds: None)


def test_cache_hit_and_secret_never_stored(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "sekret-key-123")
    session = FakeSession([response(200, {"results": [1], "echo": "sekret-key-123"})])
    client = CachedClient("openalex", cache_dir=tmp_path, secret_params=("api_key",), session=session, min_interval=0)
    first, _ = client.get_json("https://api.example/works", params={"search": "x", "api_key": "sekret-key-123"})
    second, _ = client.get_json("https://api.example/works", params={"search": "x", "api_key": "other"})
    assert first["results"] == [1] and second["results"] == [1]
    assert len(session.calls) == 1 and client.stats.cached_calls == 1
    stored = "".join(p.read_text() for p in tmp_path.rglob("*.json*"))
    stored += (tmp_path / "call_log.jsonl").read_text()
    assert "sekret-key-123" not in stored


def test_policy_block_marks_source_blocked(tmp_path):
    error = requests.exceptions.ProxyError("Unable to connect to proxy: Tunnel connection failed: 403 Forbidden")
    session = FakeSession([error])
    client = CachedClient("gtr", cache_dir=tmp_path, session=session, min_interval=0)
    with pytest.raises(SourceBlocked):
        client.get_json("https://gtr.example/persons")
    with pytest.raises(SourceBlocked):
        client.get_json("https://gtr.example/other")
    assert len(session.calls) == 1 and client.stats.blocked


def test_transient_errors_are_retried(tmp_path):
    session = FakeSession([response(503, {}), response(429, {}, {"Retry-After": "1"}), response(200, {"ok": True})])
    client = CachedClient("europepmc", cache_dir=tmp_path, session=session, min_interval=0)
    data, _ = client.get_json("https://epmc.example/search")
    assert data == {"ok": True} and client.stats.retries == 2


def test_query_errors_are_not_retried(tmp_path):
    body = {"message": "Illegal arguments in query request: fullText is not a searchable field"}
    session = FakeSession([response(500, body)])
    client = CachedClient("core", cache_dir=tmp_path, session=session, min_interval=0)
    with pytest.raises(QueryRejected):
        client.get_json("https://core.example/search", params={"q": "fullText:x"})
    assert len(session.calls) == 1


def test_openalex_budget_stops_before_ceiling(tmp_path):
    budget = OpenAlexBudget(tmp_path, stop_at_usd=0.002)
    budget.record(0.0015, "search")
    budget.check(0.0001)
    with pytest.raises(BudgetExhausted):
        budget.check(0.001)


def test_openalex_reported_cost_is_recorded(tmp_path):
    session = FakeSession([response(200, {"meta": {"cost": 0.001}, "results": []})])
    client = CachedClient("openalex", cache_dir=tmp_path, session=session, min_interval=0)
    budget = OpenAlexBudget(tmp_path)
    client.get_json("https://api.example/works", params={"search": "y"}, budget=budget, expected_cost=0.0005, cost_kind="search")
    assert budget.spent_today() == pytest.approx(0.001)


# --- parsers --------------------------------------------------------------------

def test_openalex_work_parsing():
    work = {
        "id": "https://openalex.org/W123",
        "doi": "https://doi.org/10.1/XYZ",
        "display_name": "Returns to degrees",
        "publication_year": 2022,
        "publication_date": "2022-03-01",
        "type": "article",
        "authorships": [{"author": {"display_name": "Jack Britton"}, "institutions": [{"display_name": "Institute for Fiscal Studies"}]}],
        "primary_location": {"source": {"display_name": "Labour Economics"}, "landing_page_url": "https://x"},
        "abstract_inverted_index": {"We": [0], "use": [1], "LEO": [2]},
    }
    candidate = OpenAlexSource.to_candidate(work, "author:x")
    assert candidate.source_id == "W123" and candidate.doi == "10.1/xyz"
    assert candidate.abstract == "We use LEO" and candidate.output_type == "journal article"
    assert reconstruct_abstract(None) == ""


def test_openalex_institution_compatibility():
    assert institutions_compatible(["University College London"], ["UCL"])
    assert institutions_compatible(["Institute for Fiscal Studies"], ["Institute for Fiscal Studies"])
    assert not institutions_compatible(["University of York"], ["University of Oxford"])


def test_core_work_parsing():
    work = {
        "id": 42, "title": "A paper", "yearPublished": 2021, "publishedDate": "2021-02-03T00:00:00",
        "doi": "10.1/a", "authors": [{"name": "Britton, Jack"}], "journals": [{"title": "IFS Working Papers"}],
        "documentType": "working paper", "fullText": "text", "links": [{"type": "display", "url": "https://core/42"}],
    }
    candidate = CoreSource.to_candidate(work, "q")
    assert candidate.publication_date == "2021-02-03" and candidate.url == "https://core/42"
    assert candidate.output_type == "working paper"


def test_europepmc_parsing_and_xml_text():
    result = {
        "id": "123", "source": "MED", "pmcid": "PMC1", "doi": "10.1/b", "title": "Health paper", "pubYear": "2022",
        "firstPublicationDate": "2022-04-01", "authorList": {"author": [{"fullName": "Lyons RA"}]},
        "journalInfo": {"journal": {"title": "BMJ Open"}}, "pubTypeList": {"pubType": ["research-article", "Journal Article"]},
        "isOpenAccess": "Y",
    }
    candidate = EuropePmcSource.to_candidate(result, "phrase:x")
    assert candidate.authors == ["Lyons RA"] and candidate.year == 2022 and candidate.output_type == "journal article"
    xml = "<article><body><p>Data via the SAIL Databank.</p></body><back><ref-list><ref>Digital Economy Act</ref></ref-list></back></article>"
    assert xml_to_text(xml) == "Data via the SAIL Databank."


def test_gtr_publication_parsing_and_dates():
    publication = {"id": "P1", "title": "Grant output", "datePublished": 1640995200000, "doi": "10.1/c", "author": "Britton J, Lee A", "journalTitle": "Fiscal Studies"}
    candidate = GtrSource(offline=True).to_candidate(publication, "G1")
    assert candidate.publication_date == "2022-01-01" and candidate.authors == ["Britton J", "Lee A"]


def test_govuk_body_text():
    page = {"description": "Summary", "details": {"body": "<p>Analysis in the <b>Secure Research Service</b>.</p>"}}
    assert "Secure Research Service" in GovUkSource.body_text(page)


# --- sampling ----------------------------------------------------------------------

def test_largest_remainder_allocation():
    counts = pd.Series({"a": 50, "b": 30, "c": 20})
    assert allocate(counts, 10).to_dict() == {"a": 5, "b": 3, "c": 2}
    assert allocate(counts, 7).sum() == 7


def test_two_stage_allocation_keeps_every_year():
    rows = [{"accreditation_year": 2019, "sector_group": "academic"}] * 3
    rows += [{"accreditation_year": 2020, "sector_group": s} for s in ["academic"] * 60 + ["government"] * 37]
    allocation = allocate_two_stage(pd.DataFrame(rows), 10)
    assert allocation.sum() == 10
    assert allocation["2019 | academic"] >= 1
