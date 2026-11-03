"""Semantic Scholar Graph API: enrichment only (DOIs, abstracts, de-duplication).

* ``POST /graph/v1/paper/batch?fields=...`` with ``{"ids": ["DOI:..."]}``
  (up to 500 IDs per call).
* Unauthenticated use shares a pool of about 1 request/second; the client
  spaces calls 1.1 s apart and backs off on 429.
"""

from __future__ import annotations

from analysis.publication_linkage import config
from analysis.publication_linkage.http_client import CachedClient
from analysis.publication_linkage.outputs import CandidateOutput, OutputGroup

BASE = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,abstract,year,publicationDate,externalIds,authors,venue,publicationTypes"
BATCH = 400


class SemanticScholarEnricher:
    name = "semanticscholar"

    def __init__(self, *, offline: bool = False, cache_dir=config.CACHE_DIR):
        self.client = CachedClient("semanticscholar", offline=offline, cache_dir=cache_dir)
        self.notes: list[str] = []

    @staticmethod
    def to_candidate(paper: dict) -> CandidateOutput:
        external = paper.get("externalIds") or {}
        types = paper.get("publicationTypes") or []
        return CandidateOutput(
            source="semanticscholar",
            source_id=str(paper.get("paperId")),
            title=paper.get("title") or "",
            year=paper.get("year"),
            publication_date=paper.get("publicationDate"),
            doi=external.get("DOI"),
            authors=[a.get("name", "") for a in paper.get("authors") or [] if a.get("name")],
            venue=paper.get("venue"),
            type_raw="journal-article" if "JournalArticle" in types else (types[0] if types else None),
            abstract=paper.get("abstract"),
            query="enrichment:doi",
        )

    def enrich(self, groups: list[OutputGroup]) -> list[CandidateOutput]:
        """Records for groups that have a DOI but no abstract or full text."""
        wanted = [g.doi for g in groups if g.doi and not any((m.abstract or m.full_text) for m in g.members)]
        added: list[CandidateOutput] = []
        for offset in range(0, len(wanted), BATCH):
            ids = [f"DOI:{doi}" for doi in wanted[offset: offset + BATCH]]
            data, _ = self.client.post_json(f"{BASE}/paper/batch", {"ids": ids}, params={"fields": FIELDS})
            for paper in data or []:
                if paper:
                    added.append(self.to_candidate(paper))
        return added
