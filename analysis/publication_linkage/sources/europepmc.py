"""Europe PMC: health-related DEA work.

REST API (https://europepmc.org/RestfulWebService):

* ``GET /europepmc/webservices/rest/search?query=...&format=json&resultType=core
  &pageSize=1000&cursorMark=*`` -- the default query field covers titles,
  abstracts and open-access full text; ``PUB_YEAR:[a TO b]`` bounds dates.
* ``GET /europepmc/webservices/rest/{PMCID}/fullTextXML`` -- open-access
  full text, from which acknowledgement and data-statement sentences are
  taken.

Field names checked against ``/rest/fields`` on 2026-11-03 (ACK_FUND,
METHODS, BODY, PUB_YEAR, DOI, OPEN_ACCESS, ...). A bare quoted ID such as
``"2022/139"`` matches loosely (618 hits), so project-ID queries pair the ID
with accreditation terms; the rules then require a context word beside it.
"""

from __future__ import annotations

import re
from datetime import date

from analysis.publication_linkage import config
from analysis.publication_linkage.http_client import CachedClient, QueryRejected, SourceBlocked
from analysis.publication_linkage.matching import SEARCH_PHRASES, clean_text, parse_person_name
from analysis.publication_linkage.outputs import CandidateOutput
from analysis.publication_linkage.register_records import ProjectRecord

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
PAGE_SIZE = 1000
MAX_PAGES_PER_PHRASE = 3
MAX_FULLTEXTS = 2000
ID_CONTEXT = (
    '"Digital Economy Act" OR "Research Accreditation Panel" OR "Secure Research Service" OR '
    '"Integrated Data Service" OR "UK Statistics Authority" OR "SAIL Databank" OR accredited OR accreditation'
)


def xml_to_text(xml: str) -> str:
    """Body text of a JATS document (references dropped)."""
    xml = re.sub(r"<ref-list.*?</ref-list>", " ", xml or "", flags=re.S)
    xml = re.sub(r"<(?:title|p|sec|ack|fn|caption)[^>]*>", "\n", xml)
    return clean_text(xml)


class EuropePmcSource:
    name = "europepmc"

    def __init__(self, *, offline: bool = False, cache_dir=config.CACHE_DIR):
        self.client = CachedClient("europepmc", offline=offline, cache_dir=cache_dir)
        self.notes: list[str] = []

    @staticmethod
    def to_candidate(result: dict, query: str) -> CandidateOutput:
        author_list = ((result.get("authorList") or {}).get("author")) or []
        authors = [a.get("fullName") or f"{a.get('lastName', '')} {a.get('initials', '')}".strip() for a in author_list]
        if not authors and result.get("authorString"):
            authors = [part.strip() for part in str(result["authorString"]).rstrip(".").split(",") if part.strip()]
        journal = ((result.get("journalInfo") or {}).get("journal") or {}).get("title")
        pub_types = ((result.get("pubTypeList") or {}).get("pubType")) or []
        type_raw = "preprint" if result.get("source") == "PPR" else ("; ".join(pub_types) if pub_types else None)
        return CandidateOutput(
            source="europepmc",
            source_id=f"{result.get('source', '')}:{result.get('id', '')}",
            title=result.get("title") or "",
            year=int(result["pubYear"]) if str(result.get("pubYear") or "").isdigit() else None,
            publication_date=result.get("firstPublicationDate"),
            doi=result.get("doi"),
            authors=[a for a in authors if a],
            venue=journal or (result.get("bookOrReportDetails") or {}).get("publisher"),
            type_raw=type_raw,
            abstract=result.get("abstractText"),
            url=f"https://europepmc.org/article/{result.get('source', '')}/{result.get('id', '')}",
            query=query,
            extra={"pmcid": result.get("pmcid"), "is_open_access": result.get("isOpenAccess")},
        )

    def search(self, query: str) -> list[dict]:
        results: list[dict] = []
        cursor = "*"
        for _ in range(MAX_PAGES_PER_PHRASE):
            data, _ = self.client.get_json(
                f"{BASE}/search",
                params={"query": query, "format": "json", "resultType": "core", "pageSize": PAGE_SIZE, "cursorMark": cursor},
            )
            data = data or {}
            page = ((data.get("resultList") or {}).get("result")) or []
            results.extend(page)
            next_cursor = data.get("nextCursorMark")
            if not page or not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
        return results

    def fetch_by_doi(self, doi: str) -> CandidateOutput | None:
        """Open-access full text for an output found elsewhere."""
        results = self.search(f'DOI:"{doi}"')
        for result in results:
            if (result.get("doi") or "").lower() == doi.lower():
                candidate = self.to_candidate(result, f"doi:{doi}")
                pmcid = result.get("pmcid")
                if pmcid and result.get("isOpenAccess") == "Y":
                    candidate.full_text = self.full_text(pmcid)
                return candidate
        return None

    def full_text(self, pmcid: str) -> str:
        """Open-access XML as text; one failing document is skipped, not fatal."""
        try:
            text, record = self.client.get_text(f"{BASE}/{pmcid}/fullTextXML")
        except SourceBlocked:
            if self.client.stats.blocked:
                raise
            self.notes.append(f"full text unavailable (failed in the live run, so not cached): {pmcid}")
            return ""
        except (RuntimeError, QueryRejected) as error:
            self.notes.append(f"full text skipped after retries: {pmcid} ({str(error)[:60]})")
            return ""
        return xml_to_text(text) if record.get("status") == 200 else ""

    def collect(self, projects: list[ProjectRecord], snapshot_date: date) -> list[CandidateOutput]:
        earliest = min(project.accreditation_date for project in projects).year - 1
        candidates: dict[str, CandidateOutput] = {}
        for phrase in SEARCH_PHRASES:
            query = f'"{phrase}" AND PUB_YEAR:[{earliest} TO {snapshot_date.year}]'
            for result in self.search(query):
                candidate = self.to_candidate(result, f"phrase:{phrase}")
                candidates.setdefault(candidate.source_id, candidate)
        for project in projects:
            query = f'"{project.project_id}" AND ({ID_CONTEXT}) AND PUB_YEAR:[{project.accreditation_date.year - 1} TO {snapshot_date.year}]'
            for result in self.search(query):
                candidate = self.to_candidate(result, f"project_id:{project.project_id}")
                candidate = candidates.setdefault(candidate.source_id, candidate)
                if project.project_id not in candidate.index_project_id_hits:
                    candidate.index_project_id_hits.append(project.project_id)
        # Full text only where a link is possible: an author family name shared
        # with a register researcher in scope, or a project-ID hit.
        families = {
            parsed.family_key
            for project in projects for researcher in project.researchers
            if (parsed := parse_person_name(researcher.name))
        }

        def could_link(candidate: CandidateOutput) -> bool:
            if candidate.index_project_id_hits:
                return True
            return any((parsed := parse_person_name(a)) and parsed.family_key in families for a in candidate.authors)

        fetched = 0
        for candidate in candidates.values():
            pmcid = candidate.extra.get("pmcid")
            if not could_link(candidate):
                continue
            if pmcid and candidate.extra.get("is_open_access") == "Y" and fetched < MAX_FULLTEXTS:
                candidate.full_text = self.full_text(pmcid)
                fetched += 1
        if fetched >= MAX_FULLTEXTS:
            self.notes.append(f"full-text fetch capped at {MAX_FULLTEXTS}")
        return list(candidates.values())
