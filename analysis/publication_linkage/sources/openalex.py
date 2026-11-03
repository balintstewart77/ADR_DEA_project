"""OpenAlex: main breadth source.

Parameters follow the OpenAlex API reference as published in 2026
(developers.openalex.org; checked via search on 2026-11-03 because the docs
host was not reachable from the run environment):

* Key: ``api_key`` query parameter (required since 13 February 2026).
* Pricing: singleton lookups free; list/filter calls $0.0001; ``search``
  calls $0.001. Each response reports its cost in ``meta.cost`` (and the
  ``X-RateLimit-Credits-Used`` header); the ledger in
  :class:`~analysis.publication_linkage.http_client.OpenAlexBudget` stops
  calls before the daily free $1 is used. PDF/content downloads are never used.
* ``/works?search=...`` covers title, abstract and full text;
  ``/authors?search=...`` resolves names; works by author use the
  ``authorships.author.id`` filter (OR-joined with ``|``) plus
  ``from_publication_date`` / ``to_publication_date``.

Two routes:

(a) phrase search for accreditation statements (project independent);
(b) author-centred: resolve each register researcher (name + institution) to
    OpenAlex author IDs, then pull their works in the window and keep those
    whose title or abstract names a register dataset or alias.
"""

from __future__ import annotations

from datetime import date

from analysis.publication_linkage import config
from analysis.publication_linkage.http_client import BudgetExhausted, CachedClient, OpenAlexBudget
from analysis.publication_linkage.matching import (
    SEARCH_PHRASES,
    clean_text,
    find_dataset_mentions,
    find_phrases,
    name_match_level,
    normalise_title,
)
from analysis.publication_linkage.outputs import CandidateOutput
from analysis.publication_linkage.register_records import ProjectRecord
from analysis.publication_linkage.sources import researcher_queries
from dashboard.institution_normalisation import describe_institution_normalisation

BASE = "https://api.openalex.org"
WORK_FIELDS = (
    "id,doi,display_name,publication_year,publication_date,type,authorships,"
    "primary_location,abstract_inverted_index,has_fulltext,ids"
)
AUTHOR_FIELDS = "id,display_name,display_name_alternatives,last_known_institutions,affiliations,works_count"
PER_PAGE = 200
MAX_PHRASE_PAGES = 25  # 5,000 works per phrase at most
MAX_AUTHOR_CANDIDATES = 3
AUTHOR_IDS_PER_CALL = 50


def reconstruct_abstract(inverted: dict | None) -> str:
    if not inverted:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indexes in inverted.items():
        positions.extend((index, word) for index in indexes)
    return " ".join(word for _, word in sorted(positions))


def institution_key(name: str) -> str:
    canonical = str(describe_institution_normalisation(name)["institution"] or name)
    return normalise_title(canonical)


def institutions_compatible(register_institutions: list[str], openalex_institutions: list[str]) -> bool:
    register_keys = {institution_key(name) for name in register_institutions if name}
    for name in openalex_institutions:
        key = institution_key(name)
        if not key:
            continue
        for register_key in register_keys:
            if key == register_key or (len(key) > 8 and (key in register_key or register_key in key)):
                return True
            a, b = set(key.split()), set(register_key.split())
            if a and b and len(a & b) / len(a | b) >= 0.6:
                return True
    return False


class OpenAlexSource:
    name = "openalex"

    def __init__(self, *, offline: bool = False, cache_dir=config.CACHE_DIR):
        self.client = CachedClient("openalex", secret_params=("api_key",), offline=offline, cache_dir=cache_dir)
        self.budget = OpenAlexBudget(cache_dir)
        self.notes: list[str] = []
        self.author_resolution: list[dict] = []
        key = config.openalex_api_key()
        if not key:
            self.notes.append("OPENALEX_API_KEY not set")
        self._key = key

    def _get(self, path: str, params: dict, kind: str) -> dict:
        params = {**params, "api_key": self._key} if self._key else dict(params)
        data, _ = self.client.get_json(
            f"{BASE}{path}",
            params=params,
            budget=self.budget,
            expected_cost=config.OPENALEX_PRICE_USD[kind],
            cost_kind=kind,
        )
        return data or {}

    @staticmethod
    def to_candidate(work: dict, query: str, phrase: str | None = None) -> CandidateOutput:
        authorships = work.get("authorships") or []
        authors = [
            (a.get("author") or {}).get("display_name") or a.get("raw_author_name") or ""
            for a in authorships
        ]
        location = work.get("primary_location") or {}
        source = location.get("source") or {}
        return CandidateOutput(
            source="openalex",
            source_id=str(work.get("id", "")).rsplit("/", 1)[-1],
            title=work.get("display_name") or work.get("title") or "",
            year=work.get("publication_year"),
            publication_date=work.get("publication_date"),
            doi=work.get("doi"),
            authors=[a for a in authors if a],
            venue=source.get("display_name"),
            type_raw=work.get("type"),
            abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
            url=location.get("landing_page_url"),
            query=query,
            index_phrase_hits=[phrase] if phrase else [],
            extra={
                "has_fulltext": work.get("has_fulltext"),
                "affiliations": sorted({
                    inst.get("display_name", "")
                    for a in authorships for inst in a.get("institutions") or [] if inst.get("display_name")
                }),
            },
        )

    # -- (a) phrase search -------------------------------------------------
    def phrase_search(self, phrase: str, from_date: date) -> list[CandidateOutput]:
        found: list[CandidateOutput] = []
        cursor = "*"
        for _ in range(MAX_PHRASE_PAGES):
            data = self._get(
                "/works",
                {
                    "search": f'"{phrase}"',
                    "filter": f"from_publication_date:{from_date.isoformat()}",
                    "per_page": PER_PAGE,
                    "cursor": cursor,
                    "select": WORK_FIELDS,
                },
                "search",
            )
            results = data.get("results") or []
            for work in results:
                candidate = self.to_candidate(work, f"phrase:{phrase}")
                # The index says the phrase matched (possibly in full text we
                # cannot see); record it, and check visible text ourselves.
                if not find_phrases(candidate.matching_text()):
                    candidate.index_phrase_hits = [phrase]
                found.append(candidate)
            cursor = (data.get("meta") or {}).get("next_cursor")
            if not results or not cursor:
                break
        return found

    # -- (b) author-centred ---------------------------------------------------
    def resolve_author(self, name: str, institutions: list[str]) -> list[str]:
        data = self._get("/authors", {"search": name, "per_page": 25, "select": AUTHOR_FIELDS}, "search")
        matches: list[tuple[int, str, str]] = []
        for author in data.get("results") or []:
            names = [author.get("display_name") or "", *(author.get("display_name_alternatives") or [])]
            levels = [name_match_level(name, candidate) for candidate in names]
            if "full" not in levels:
                continue
            oa_institutions = [inst.get("display_name", "") for inst in author.get("last_known_institutions") or []]
            oa_institutions += [
                (aff.get("institution") or {}).get("display_name", "") for aff in author.get("affiliations") or []
            ]
            compatible = institutions_compatible(institutions, oa_institutions)
            matches.append((0 if compatible else 1, -(author.get("works_count") or 0), author.get("id", "")))
        matches.sort()
        institution_matched = [m for m in matches if m[0] == 0]
        chosen = institution_matched[:MAX_AUTHOR_CANDIDATES]
        basis = "name+institution"
        if not chosen and len(matches) == 1:
            chosen, basis = matches, "name_only_unique"
        ids = [m[2].rsplit("/", 1)[-1] for m in chosen if m[2]]
        self.author_resolution.append({"name": name, "institutions": "; ".join(institutions), "author_ids": "|".join(ids), "basis": basis if ids else "unresolved", "candidates": len(matches)})
        return ids

    def works_for_authors(self, author_ids: list[str], start: date, end: date) -> list[dict]:
        works: list[dict] = []
        for offset in range(0, len(author_ids), AUTHOR_IDS_PER_CALL):
            batch = author_ids[offset: offset + AUTHOR_IDS_PER_CALL]
            cursor = "*"
            while cursor:
                data = self._get(
                    "/works",
                    {
                        "filter": (
                            f"authorships.author.id:{'|'.join(batch)},"
                            f"from_publication_date:{start.isoformat()},to_publication_date:{end.isoformat()}"
                        ),
                        "per_page": PER_PAGE,
                        "cursor": cursor,
                        "select": WORK_FIELDS,
                    },
                    "list",
                )
                works.extend(data.get("results") or [])
                cursor = (data.get("meta") or {}).get("next_cursor") if data.get("results") else None
        return works

    def collect(self, projects: list[ProjectRecord], snapshot_date: date) -> list[CandidateOutput]:
        candidates: list[CandidateOutput] = []
        by_record = {project.record_id: project for project in projects}
        earliest = min(project.accreditation_date for project in projects)
        try:
            for phrase in SEARCH_PHRASES:
                candidates.extend(self.phrase_search(phrase, date(earliest.year - 1, 1, 1)))
            for researcher in researcher_queries(projects, snapshot_date):
                ids = self.resolve_author(researcher.query_name, researcher.institutions)
                if not ids:
                    continue
                terms = [term for record_id in researcher.record_ids for term in by_record[record_id].dataset_terms]
                for work in self.works_for_authors(ids, researcher.window_start, snapshot_date):
                    candidate = self.to_candidate(work, f"author:{researcher.query_name}")
                    title_abstract = f"{candidate.title} {clean_text(candidate.abstract)}"
                    if find_dataset_mentions(title_abstract, terms) or find_phrases(title_abstract):
                        candidates.append(candidate)
        except BudgetExhausted as error:
            self.notes.append(f"stopped for the day: {error}")
        return candidates
