"""CORE (core.ac.uk) v3: UK repository full texts.

Verified against https://api.core.ac.uk/docs/v3 and live behaviour on
2026-11-03:

* ``GET /v3/search/works/?q=<query>&limit=<n>&offset=<n>``; field lookups
  ``title:``, ``authors:``, ``yearPublished>=``; boolean ``AND``/``OR``.
* Documented ``fullText:`` and ``abstract:`` lookups (and unqualified queries,
  which search all fields) currently fail server-side with "fullText/abstract
  is not a searchable field". The client probes once per run; while the probe
  fails, phrase and project-ID searches fall back to ``title:`` and the
  author-centred route carries the load.
* Results include ``fullText`` inline when CORE holds it (authenticated users
  only). Acknowledgement/data-statement sentences are extracted locally.
* Rate limit: registered personal keys get 1,000 tokens/day, 25/minute; the
  client spaces calls 2.6 s apart and honours ``X-RateLimit-*`` headers.
* Authentication: ``CORE_API_KEY`` as a Bearer token when set; otherwise no
  header (the network proxy attaches the key).
"""

from __future__ import annotations

from datetime import date

from analysis.publication_linkage import config
from analysis.publication_linkage.http_client import CachedClient, QueryRejected
from analysis.publication_linkage.matching import SEARCH_PHRASES
from analysis.publication_linkage.outputs import CandidateOutput
from analysis.publication_linkage.register_records import ProjectRecord
from analysis.publication_linkage.sources import author_matches_any, researcher_queries

BASE = "https://api.core.ac.uk/v3/search/works/"
PAGE_SIZE = 50
MAX_PAGES_PER_AUTHOR = 2
MAX_PAGES_PER_PHRASE = 4


class CoreSource:
    name = "core"

    def __init__(self, *, offline: bool = False, cache_dir=config.CACHE_DIR):
        headers = {"Accept": "application/json"}
        key = config.core_api_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        self.client = CachedClient("core", headers=headers, offline=offline, cache_dir=cache_dir)
        self.notes: list[str] = []
        self.fulltext_search_available: bool | None = None

    # -- helpers -------------------------------------------------------------
    def _search(self, query: str, offset: int = 0) -> dict:
        data, _ = self.client.get_json(BASE, params={"q": query, "limit": PAGE_SIZE, "offset": offset})
        return data or {}

    def probe_fulltext_search(self) -> bool:
        if self.fulltext_search_available is None:
            try:
                self._search('fullText:"Secure Research Service" AND yearPublished>=2018')
                self.fulltext_search_available = True
            except QueryRejected as error:
                self.fulltext_search_available = False
                self.notes.append(f"fullText search unavailable at CORE ({str(error)[:120]}); title-only phrase search used")
        return self.fulltext_search_available

    @staticmethod
    def to_candidate(work: dict, query: str) -> CandidateOutput:
        journals = work.get("journals") or []
        venue = None
        if journals and isinstance(journals[0], dict):
            venue = journals[0].get("title")
        if not venue:
            venue = work.get("publisher")
        authors = [a.get("name", "") for a in work.get("authors") or [] if isinstance(a, dict) and a.get("name")]
        links = work.get("links") or []
        url = work.get("downloadUrl") or next(
            (link.get("url") for link in links if isinstance(link, dict) and link.get("url")), None
        )
        return CandidateOutput(
            source="core",
            source_id=str(work.get("id")),
            title=work.get("title") or "",
            year=work.get("yearPublished"),
            publication_date=(work.get("publishedDate") or "")[:10] or None,
            doi=work.get("doi"),
            authors=authors,
            venue=venue,
            type_raw=work.get("documentType"),
            abstract=work.get("abstract"),
            full_text=work.get("fullText"),
            url=url,
            query=query,
        )

    # -- collection ------------------------------------------------------------
    def collect(self, projects: list[ProjectRecord], snapshot_date: date) -> list[CandidateOutput]:
        candidates: list[CandidateOutput] = []
        for researcher in researcher_queries(projects, snapshot_date):
            y0 = researcher.window_start.year
            query = f'authors:"{researcher.query_name}" AND yearPublished>={y0} AND yearPublished<={snapshot_date.year}'
            for page in range(MAX_PAGES_PER_AUTHOR):
                data = self._search(query, offset=page * PAGE_SIZE)
                results = data.get("results") or []
                for work in results:
                    candidate = self.to_candidate(work, f"author:{researcher.query_name}")
                    if author_matches_any(researcher.name, candidate.authors):
                        candidates.append(candidate)
                if len(results) < PAGE_SIZE or (page + 1) * PAGE_SIZE >= int(data.get("totalHits") or 0):
                    break

        fulltext = self.probe_fulltext_search()
        field_name = "fullText" if fulltext else "title"
        for phrase in SEARCH_PHRASES:
            query = f'{field_name}:"{phrase}" AND yearPublished>=2018'
            for page in range(MAX_PAGES_PER_PHRASE):
                try:
                    data = self._search(query, offset=page * PAGE_SIZE)
                except QueryRejected as error:
                    self.notes.append(f"phrase query rejected: {phrase} ({str(error)[:80]})")
                    break
                results = data.get("results") or []
                for work in results:
                    candidate = self.to_candidate(work, f"phrase:{field_name}:{phrase}")
                    candidates.append(candidate)
                if len(results) < PAGE_SIZE:
                    break
        if fulltext:
            # Project-ID patterns need full-text search: one query per project.
            for project in projects:
                query = f'fullText:"{project.project_id}" AND yearPublished>={project.accreditation_date.year - 1}'
                try:
                    data = self._search(query)
                except QueryRejected:
                    break
                for work in data.get("results") or []:
                    candidates.append(self.to_candidate(work, f"project_id:{project.project_id}"))
        else:
            self.notes.append("project-ID full-text search skipped: CORE fullText search unavailable")
        return candidates

    def fetch_by_doi(self, doi: str) -> CandidateOutput | None:
        """Full text for an output found elsewhere (e.g. OpenAlex)."""
        try:
            data = self._search(f'doi:"{doi}"')
        except QueryRejected:
            return None
        for work in data.get("results") or []:
            if (work.get("doi") or "").lower() == doi.lower():
                return self.to_candidate(work, f"doi:{doi}")
        return None
