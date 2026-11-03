"""Source clients. Each exposes ``collect(projects, snapshot_date) -> list[CandidateOutput]``."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from analysis.publication_linkage.matching import name_match_level, parse_person_name
from analysis.publication_linkage.register_records import ProjectRecord
from analysis.publication_linkage.tiers import add_months


@dataclass
class ResearcherQuery:
    """One unique register researcher across the projects in scope."""

    name: str
    query_name: str  # first given name + family name, for author search
    family: str = ""  # family name as written on the register (particles kept)
    institutions: list[str] = field(default_factory=list)
    record_ids: list[str] = field(default_factory=list)
    window_start: date | None = None
    window_end: date | None = None


def researcher_queries(projects: list[ProjectRecord], snapshot_date: date, months_before: int = 6) -> list[ResearcherQuery]:
    """Unique researchers with the widest publication window across their projects."""
    by_key: dict[str, ResearcherQuery] = {}
    for project in projects:
        start = add_months(project.accreditation_date, -months_before)
        for researcher in project.researchers:
            parsed = parse_person_name(researcher.name)
            if parsed is None:
                continue
            raw_tokens = researcher.name.split()
            # First given name + full family name (particles kept: "Aureo De
            # Paula" -> "Aureo De Paula", "Iain Maitland Atherton" -> "Iain Atherton").
            family_len = max(1, min(len(parsed.family.split()), len(raw_tokens) - 1))
            family = " ".join(raw_tokens[-family_len:])
            query_name = f"{raw_tokens[0]} {family}"
            key = query_name.casefold()
            entry = by_key.setdefault(key, ResearcherQuery(researcher.name, query_name, family=family))
            if researcher.institution and researcher.institution not in entry.institutions:
                entry.institutions.append(researcher.institution)
            if project.record_id not in entry.record_ids:
                entry.record_ids.append(project.record_id)
            entry.window_start = min(filter(None, [entry.window_start, start]))
            entry.window_end = snapshot_date
    return sorted(by_key.values(), key=lambda entry: entry.query_name.casefold())


def author_matches_any(researcher: str, authors: list[str]) -> bool:
    return any(name_match_level(researcher, author) for author in authors)
