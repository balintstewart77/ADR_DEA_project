"""UKRI Gateway to Research (GtR-2 API): funded projects and reported outputs.

GtR-2 API (https://gtr.ukri.org/resources/gtrapi2.html, v1.7.x guide):

* Base ``https://gtr.ukri.org/gtr/api``; JSON needs
  ``Accept: application/vnd.rcuk.gtr.json-v7``.
* Search: ``/persons?q=<term>&f=per.sn&s=<size>&p=<page>`` (``f`` selects the
  field; ``per.sn`` = surname). Resources link to related resources through
  ``links.link[]`` entries with ``rel`` and ``href``.
* ``/projects/{id}`` gives title, abstract and links to outcomes;
  publication outcomes live at ``/outcomes/publications/{id}``.

Matching a grant to a register project needs (i) the register researcher as
an investigator on the grant, (ii) grant activity overlapping the window,
and (iii) title similarity >= 0.15 or a register dataset named in the grant
title/abstract. Publications reported against matched grants become
candidates and are then tiered like any other output.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from analysis.publication_linkage import config
from analysis.publication_linkage.http_client import CachedClient
from analysis.publication_linkage.matching import (
    clean_text,
    find_dataset_mentions,
    name_match_level,
    title_similarity,
)
from analysis.publication_linkage.outputs import CandidateOutput
from analysis.publication_linkage.register_records import ProjectRecord
from analysis.publication_linkage.sources import researcher_queries
from analysis.publication_linkage.tiers import window_for

BASE = "https://gtr.ukri.org/gtr/api"
ACCEPT = "application/vnd.rcuk.gtr.json-v7"
PAGE_SIZE = 100
INVESTIGATOR_RELS = {"PI_PER", "COI_PER", "FELLOW_PER", "RESEARCHER_PER", "PM_PER", "STUDENT_PER", "SUPER_PER"}
TITLE_SIMILARITY_MIN = 0.15


def _links(resource: dict) -> list[dict]:
    links = (resource.get("links") or {}).get("link") or []
    return [link for link in links if isinstance(link, dict)]


def _epoch_ms_to_date(value: object) -> date | None:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).date()
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _id_from_href(href: str) -> str:
    return str(href).rstrip("/").rsplit("/", 1)[-1]


class GtrSource:
    name = "gtr"

    def __init__(self, *, offline: bool = False, cache_dir=config.CACHE_DIR):
        self.client = CachedClient("gtr", headers={"Accept": ACCEPT}, offline=offline, cache_dir=cache_dir)
        self.notes: list[str] = []
        self.grant_links: list[dict] = []

    def _get(self, path: str, params: dict | None = None) -> dict:
        data, _ = self.client.get_json(f"{BASE}{path}", params=params)
        return data or {}

    def persons(self, surname: str) -> list[dict]:
        data = self._get("/persons", {"q": surname, "f": "per.sn", "s": PAGE_SIZE, "p": 1})
        return data.get("person") or []

    def project(self, project_id: str) -> dict:
        return self._get(f"/projects/{project_id}")

    def publication(self, publication_id: str) -> dict:
        return self._get(f"/outcomes/publications/{publication_id}")

    @staticmethod
    def grant_dates(grant: dict) -> tuple[date | None, date | None]:
        start = _epoch_ms_to_date(grant.get("start"))
        end = _epoch_ms_to_date(grant.get("end"))
        for link in _links(grant):
            if link.get("rel") == "FUND":
                start = start or _epoch_ms_to_date(link.get("start"))
                end = end or _epoch_ms_to_date(link.get("end"))
        return start, end

    def grant_matches(self, grant: dict, project: ProjectRecord, snapshot_date: date) -> tuple[bool, float, list[str]]:
        text = f"{grant.get('title', '')} {clean_text(grant.get('abstractText'))}"
        similarity = title_similarity(grant.get("title"), project.title)
        datasets = [hit.dataset for hit in find_dataset_mentions(text, project.dataset_terms)]
        start, end = self.grant_dates(grant)
        window_start, window_end = window_for(project, snapshot_date)
        overlaps = True
        if start and end:
            overlaps = end >= window_start.replace(year=window_start.year - 1) and start <= window_end
        return overlaps and (similarity >= TITLE_SIMILARITY_MIN or bool(datasets)), similarity, datasets

    def to_candidate(self, publication: dict, grant_id: str) -> CandidateOutput:
        authors = [part.strip() for part in str(publication.get("author") or "").split(",") if part.strip()]
        published = _epoch_ms_to_date(publication.get("datePublished"))
        return CandidateOutput(
            source="gtr",
            source_id=str(publication.get("id") or publication.get("outcomeId") or ""),
            title=publication.get("title") or "",
            publication_date=published.isoformat() if published else None,
            year=published.year if published else None,
            doi=publication.get("doi"),
            authors=authors,
            venue=publication.get("journalTitle"),
            type_raw=publication.get("type"),
            query=f"grant:{grant_id}",
            extra={"grant_id": grant_id},
        )

    def collect(self, projects: list[ProjectRecord], snapshot_date: date) -> list[CandidateOutput]:
        by_record = {project.record_id: project for project in projects}
        candidates: list[CandidateOutput] = []
        seen_publications: set[str] = set()
        for researcher in researcher_queries(projects, snapshot_date):
            surname = researcher.query_name.split()[-1]
            for person in self.persons(surname):
                full = f"{person.get('firstName', '')} {person.get('surname', '')}".strip()
                if name_match_level(researcher.name, full) != "full":
                    continue
                grant_ids = [_id_from_href(link["href"]) for link in _links(person) if link.get("rel") in INVESTIGATOR_RELS and link.get("href")]
                for grant_id in dict.fromkeys(grant_ids):
                    grant = self.project(grant_id)
                    if not grant:
                        continue
                    for record_id in researcher.record_ids:
                        matched, similarity, datasets = self.grant_matches(grant, by_record[record_id], snapshot_date)
                        if not matched:
                            continue
                        self.grant_links.append({
                            "Record ID": record_id, "grant_id": grant_id, "grant_title": grant.get("title", ""),
                            "researcher": researcher.name, "title_similarity": round(similarity, 3),
                            "datasets_in_grant": "; ".join(datasets),
                        })
                        for link in _links(grant):
                            if link.get("rel") != "PUBLICATION" or not link.get("href"):
                                continue
                            publication_id = _id_from_href(link["href"])
                            if publication_id in seen_publications:
                                continue
                            seen_publications.add(publication_id)
                            publication = self.publication(publication_id)
                            if publication:
                                candidates.append(self.to_candidate(publication, grant_id))
        return candidates
