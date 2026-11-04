"""CORE (core.ac.uk) v3: UK repository full texts.

Checked against the live spec (https://api.core.ac.uk/swagger/v3.json and
https://api.core.ac.uk/docs/v3, "CORE API Query Language") and by probing on
2026-11-03:

* GET ``/v3/search/works/?q=&limit=&offset=`` (trailing slash) or POST
  ``/v3/search/works`` (no slash) with a JSON body; both behave the same.
* Field lookups ``title:``, ``authors:``, ``abstract:``, ``doi:``;
  ``AND``/``OR``/grouping; ranges such as ``yearPublished>=2019``.
* A quoted phrase is honoured as a phrase only inside a boolean query
  (``"Secure Research Service" AND yearPublished>=2018``); on its own the
  same phrase is rejected ("|abstract is not a searchable field") and a lone
  ``field:"..."`` lookup is treated as loose terms. Queries here therefore
  always pair a phrase with a year range.
* ``fullText`` is documented as searchable, but every form tried is rejected
  by the index ("fullText is not a searchable field"): ``fullText:``,
  ``fulltext:``, ``full_text:``, ``_exists_:fullText``, the docs' own
  examples (``fullText:Ontario``), GET and POST, works and outputs. An
  unqualified phrase reaches titles and abstracts only: six-word phrases taken
  from the body of works CORE holds (e.g. "the age structure of the
  population") never returned those works. The client probes once per run and
  uses ``fullText:`` if CORE re-enables it; otherwise phrase and project-ID
  searches run over titles and abstracts, and full text is scanned locally on
  author-centred results, which include ``fullText`` inline.
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
                self.notes.append(f"fullText not searchable at CORE ({str(error)[:110]})")
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
        for phrase in SEARCH_PHRASES:
            query = self.phrase_query(phrase, 2018, fulltext)
            for page in range(MAX_PAGES_PER_PHRASE):
                try:
                    data = self._search(query, offset=page * PAGE_SIZE)
                except QueryRejected as error:
                    self.notes.append(f"phrase query rejected: {phrase} ({str(error)[:80]})")
                    break
                results = data.get("results") or []
                for work in results:
                    candidates.append(self.to_candidate(work, f"phrase:{phrase}"))
                if len(results) < PAGE_SIZE:
                    break
        # Project IDs: one query per project, from the year before accreditation.
        for project in projects:
            query = self.phrase_query(project.project_id, project.accreditation_date.year - 1, fulltext)
            try:
                data = self._search(query)
            except QueryRejected as error:
                self.notes.append(f"project-ID query rejected ({str(error)[:80]})")
                break
            for work in data.get("results") or []:
                candidates.append(self.to_candidate(work, f"project_id:{project.project_id}"))
        if not fulltext:
            self.notes.append("phrase and project-ID searches cover titles and abstracts only (CORE fullText not searchable)")
        return candidates

    @staticmethod
    def phrase_query(phrase: str, from_year: int, fulltext: bool) -> str:
        """A phrase query CORE accepts: always combined with a year range."""
        field = "fullText:" if fulltext else ""
        return f'{field}"{phrase}" AND yearPublished>={from_year}'

    def fetch_by_doi(self, doi: str) -> CandidateOutput | None:
        """Full text for an output found elsewhere (e.g. OpenAlex)."""
        try:
            data = self._search(f'doi:"{doi}"')  # verified: exact DOI lookup
        except QueryRejected:
            return None
        for work in data.get("results") or []:
            if (work.get("doi") or "").lower() == doi.lower():
                return self.to_candidate(work, f"doi:{doi}")
        return None
