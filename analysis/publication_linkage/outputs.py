"""Candidate outputs, output-type classification and de-duplication."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from analysis.publication_linkage.matching import (
    clean_text,
    extract_statement_snippets,
    normalise_doi,
    normalise_title,
    strip_references,
)

OUTPUT_TYPES = ("journal article", "working paper", "preprint", "report", "thesis", "other")


@dataclass
class CandidateOutput:
    """One output as returned by one source (before de-duplication)."""

    source: str
    source_id: str
    title: str
    year: int | None = None
    publication_date: str | None = None  # ISO date (may be year-only "YYYY")
    doi: str | None = None
    authors: list[str] = field(default_factory=list)
    venue: str | None = None
    type_raw: str | None = None
    abstract: str | None = None
    full_text: str | None = None  # never exported; snippets are
    url: str | None = None
    query: str = ""  # how the source found it
    index_phrase_hits: list[str] = field(default_factory=list)  # phrases the index says matched
    index_project_id_hits: list[str] = field(default_factory=list)  # project IDs the index says matched
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.title = clean_text(self.title)
        self.doi = normalise_doi(self.doi)
        if self.year is None and self.publication_date:
            match = re.match(r"^(\d{4})", str(self.publication_date))
            self.year = int(match.group(1)) if match else None

    @property
    def output_type(self) -> str:
        return classify_output_type(self.source, self.type_raw, self.venue, self.title, self.doi, self.url)

    def matching_text(self) -> str:
        """Everything a rule may search: title, abstract, full text."""
        return " \n ".join(part for part in (self.title, clean_text(self.abstract), self.body_text()) if part)

    def body_text(self) -> str:
        """Full text without its reference list."""
        return strip_references(self.full_text) if self.full_text else ""

    def snippets(self) -> list[str]:
        return extract_statement_snippets(" ".join(part for part in (clean_text(self.abstract), self.body_text()) if part))


_WORKING_PAPER_RE = re.compile(
    r"working paper|discussion paper|briefing note|occasional paper|\bwp\b|\b(?:NBER|CEPR|IZA|IFS|CEP)\b", re.I
)
_PREPRINT_RE = re.compile(r"preprint|medrxiv|biorxiv|socarxiv|osf preprints|arxiv|ssrn|research square|preprints\.org|wellcome open", re.I)
_REPORT_RE = re.compile(r"\breport\b|technical|statistics release|official statistics|research and analysis|policy paper", re.I)
_THESIS_RE = re.compile(r"thesis|dissertation|doctoral|phd", re.I)


def classify_output_type(
    source: str,
    type_raw: object,
    venue: object = None,
    title: object = None,
    doi: object = None,
    url: object = None,
) -> str:
    """Map source-specific type fields to the six analysis types."""
    raw = clean_text(type_raw).casefold()
    venue_text = clean_text(venue)
    doi_text = str(doi or "")
    url_text = str(url or "")
    if _THESIS_RE.search(raw):
        return "thesis"
    if source == "govuk":
        return "report"
    if raw in {"preprint", "posted-content", "ppr"} or _PREPRINT_RE.search(venue_text) or _PREPRINT_RE.search(url_text):
        return "preprint"
    if doi_text.startswith(("10.1101/", "10.31235/", "10.2139/ssrn", "10.21203/", "10.48550/")):
        return "preprint"
    if "working paper" in raw or _WORKING_PAPER_RE.search(venue_text) or "/wp." in doi_text:
        return "working paper"
    if raw in {"report", "report-component", "technical report", "reports"} or "/re.ifs" in doi_text:
        return "report"
    if raw in {
        "article", "journal-article", "journal article", "research article", "research-article",
        "review", "review-article", "letter", "editorial", "journal", "research-article; journal article",
    }:
        if raw == "article" and not venue_text and _REPORT_RE.search(clean_text(title)):
            return "report"
        return "journal article"
    if raw in {"book", "book-chapter", "chapter", "conference", "proceedings-article", "dataset", "other", "paratext"}:
        return "other"
    if "journal" in raw or "article" in raw:
        return "journal article"
    if _REPORT_RE.search(raw):
        return "report"
    if venue_text:
        return "journal article"
    return "other"


@dataclass
class OutputGroup:
    """De-duplicated output: one or more source records of the same work."""

    output_key: str
    members: list[CandidateOutput]

    @property
    def primary(self) -> CandidateOutput:
        # Prefer the richest record: has DOI, then longest text, then source order.
        order = {"openalex": 0, "europepmc": 1, "core": 2, "semanticscholar": 3, "gtr": 4, "govuk": 5}
        return sorted(
            self.members,
            key=lambda m: (m.doi is None, -len(m.full_text or "") - len(m.abstract or ""), order.get(m.source, 9)),
        )[0]

    @property
    def sources(self) -> list[str]:
        return sorted({member.source for member in self.members})

    @property
    def doi(self) -> str | None:
        return next((m.doi for m in self.members if m.doi), None)

    @property
    def year(self) -> int | None:
        years = [m.year for m in self.members if m.year]
        return min(years) if years else None

    @property
    def publication_date(self) -> str | None:
        dates = sorted(str(m.publication_date) for m in self.members if m.publication_date)
        return dates[0] if dates else (str(self.year) if self.year else None)

    @property
    def output_type(self) -> str:
        # A journal version wins over working-paper/preprint versions.
        types = {member.output_type for member in self.members}
        for preferred in ("journal article", "working paper", "preprint", "report", "thesis"):
            if preferred in types:
                return preferred
        return "other"

    def authors(self) -> list[str]:
        seen: dict[str, str] = {}
        for member in self.members:
            for author in member.authors:
                seen.setdefault(clean_text(author).casefold(), clean_text(author))
        return list(seen.values())

    def matching_text(self) -> str:
        return " \n ".join(member.matching_text() for member in self.members)

    def statement_text(self) -> str:
        """Abstracts and full texts only (titles excluded)."""
        return " ".join(
            part for member in self.members for part in (clean_text(member.abstract), member.body_text()) if part
        )

    def snippets(self) -> list[str]:
        return extract_statement_snippets(self.statement_text())

    def index_phrase_hits(self) -> list[str]:
        return sorted({hit for member in self.members for hit in member.index_phrase_hits})

    def index_project_id_hits(self) -> list[str]:
        return sorted({hit for member in self.members for hit in member.index_project_id_hits})


def title_year_key(output: CandidateOutput) -> str | None:
    title = normalise_title(output.title)
    # Generic short titles ("Introduction", "Editorial") must not merge works.
    if len(title) < 15 or len(title.split()) < 3 or not output.year:
        return None
    return f"{title}|{output.year}"


def output_key_for(doi: str | None, title_key: str | None, fallback: str) -> str:
    if doi:
        return f"doi:{doi}"
    basis = title_key or fallback
    return "title:" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def dedupe_outputs(outputs: list[CandidateOutput]) -> list[OutputGroup]:
    """Group records of the same work: by DOI first, then normalised title + year.

    Union-find over both keys, so a record carrying a DOI and another with
    only the same title and year end up in one group.
    """
    parent = list(range(len(outputs)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)

    first_by_key: dict[str, int] = {}
    for index, output in enumerate(outputs):
        keys = []
        if output.doi:
            keys.append(f"doi:{output.doi}")
        title_key = title_year_key(output)
        if title_key:
            keys.append(f"ty:{title_key}")
        keys.append(f"src:{output.source}:{output.source_id}")
        for key in keys:
            if key in first_by_key:
                union(index, first_by_key[key])
            else:
                first_by_key[key] = index

    groups: dict[int, list[CandidateOutput]] = {}
    for index, output in enumerate(outputs):
        groups.setdefault(find(index), []).append(output)
    result = []
    for members in groups.values():
        doi = next((m.doi for m in members if m.doi), None)
        title_key = next((title_year_key(m) for m in members if title_year_key(m)), None)
        fallback = f"{members[0].source}:{members[0].source_id}"
        result.append(OutputGroup(output_key_for(doi, title_key, fallback), members))
    result.sort(key=lambda group: group.output_key)
    return result
