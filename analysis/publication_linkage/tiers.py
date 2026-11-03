"""Evidence collection and tier assignment for project--output pairs.

Tier rules (from the analysis brief):

* **Tier 1, explicit** -- the output quotes the register Project ID (with an
  accreditation context word nearby), confirmed by at least one register
  researcher among the authors or one register dataset named.
* **Tier 2, strong** -- the output names the accreditation route or a secure
  environment, at least one author is a register researcher on that project,
  at least one register dataset (or alias) is named, and the publication date
  is inside the window (6 months before accreditation to the snapshot date).
* **Tier 3, probable** -- author, dataset and date match but no accreditation
  or environment statement. Reported separately; excluded from headline rates.

An environment statement counts for Tier 2 only when it names the project's
own register environment (an SRS statement does not support a SAIL project);
route statements (DEA, Research Accreditation Panel, accredited researcher,
UK Statistics Authority) count for any environment.

Pairs the rules cannot settle are flagged for AI adjudication; Tier 1 never is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from analysis.publication_linkage.config import WINDOW_MONTHS_BEFORE
from analysis.publication_linkage.matching import (
    BOILERPLATE_RE,
    SUPPORTING_PHRASES,
    clean_text,
    find_dataset_mentions,
    find_names_in_text,
    find_phrases,
    find_project_id_mentions,
    name_match_level,
    parse_person_name,
    split_sentences,
    statement_hits,
)
from analysis.publication_linkage.outputs import OutputGroup
from analysis.publication_linkage.register_records import ProjectRecord

# Environments whose research use runs through UKSA/DEA accreditation.
DEA_SPECIFIC_ENVIRONMENTS = frozenset({"SRS", "IDS"})


def add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + (value.month - 1) + months
    year, month = divmod(month_index, 12)
    month += 1
    for day in (value.day, 30, 29, 28):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    raise ValueError(value)


def parse_publication_date(value: object) -> tuple[date | None, date | None, str]:
    """(earliest, latest, precision) for an ISO date, year-month or year."""
    text = clean_text(value)
    if not text:
        return None, None, "none"
    parts = text[:10].split("-")
    try:
        year = int(parts[0])
        if len(parts) >= 3 and parts[2]:
            day = date(year, int(parts[1]), int(parts[2]))
            return day, day, "day"
        if len(parts) >= 2 and parts[1]:
            month = int(parts[1])
            start = date(year, month, 1)
            return start, add_months(start, 1).replace(day=1) if month < 12 else date(year, 12, 31), "month"
        return date(year, 1, 1), date(year, 12, 31), "year"
    except (ValueError, IndexError):
        return None, None, "none"


def window_for(project: ProjectRecord, snapshot_date: date) -> tuple[date, date]:
    return add_months(project.accreditation_date, -WINDOW_MONTHS_BEFORE), snapshot_date


def in_window(publication_date: object, project: ProjectRecord, snapshot_date: date) -> bool | None:
    """True/False, or None when the output has no usable date.

    Year-only dates count as inside when any part of the year overlaps.
    """
    earliest, latest, _ = parse_publication_date(publication_date)
    if earliest is None:
        return None
    start, end = window_for(project, snapshot_date)
    return latest >= start and earliest <= end


@dataclass
class Evidence:
    project_id_mentions: list[str] = field(default_factory=list)  # context strings
    author_matches: list[tuple[str, str, str]] = field(default_factory=list)  # (register, output author, level)
    authors_named_in_text: list[str] = field(default_factory=list)
    dataset_hits: list[tuple[str, str, str]] = field(default_factory=list)  # (dataset, label, kind)
    route_phrases: list[str] = field(default_factory=list)
    environment_phrases: list[str] = field(default_factory=list)  # environment codes found
    environment_consistent: bool = False
    supporting_phrases: list[str] = field(default_factory=list)
    index_phrase_hits: list[str] = field(default_factory=list)  # reported by a search index, no quote
    boilerplate_phrases: list[str] = field(default_factory=list)  # route phrases in boilerplate sentences
    date_in_window: bool | None = None
    publication_date: str | None = None

    @property
    def has_author(self) -> bool:
        return bool(self.author_matches or self.authors_named_in_text)

    @property
    def has_full_name_author(self) -> bool:
        return any(level == "full" for _, _, level in self.author_matches) or bool(self.authors_named_in_text)

    @property
    def has_dataset(self) -> bool:
        return bool(self.dataset_hits)

    @property
    def has_named_dataset(self) -> bool:
        return any(kind == "name" for _, _, kind in self.dataset_hits)

    @property
    def has_statement(self) -> bool:
        return bool(self.route_phrases) or self.environment_consistent

    @property
    def has_index_only_statement(self) -> bool:
        return not self.has_statement and bool(self.index_phrase_hits)

    @property
    def statement_type(self) -> str:
        """route / environment / route+environment / none (for Tier 2 splits)."""
        route = bool(self.route_phrases)
        environment = self.environment_consistent
        if route and environment:
            return "route+environment"
        return "route" if route else ("environment" if environment else "none")


@dataclass(frozen=True)
class TierDecision:
    tier: int | None
    needs_adjudication: bool
    reasons: tuple[str, ...]


def group_statement_hits(group: OutputGroup, statement_text: str):
    """Sentence-level statement hits, computed once per output group."""
    cached = getattr(group, "_statement_hits", None)
    if cached is None:
        cached = statement_hits(statement_text)
        group._statement_hits = cached
    return cached


def collect_evidence(project: ProjectRecord, group: OutputGroup, snapshot_date: date) -> Evidence:
    text = group.matching_text()
    statement_text = group.statement_text() or text
    evidence = Evidence()
    for mention in find_project_id_mentions(statement_text):
        if mention.project_id == project.project_id:
            evidence.project_id_mentions.append(mention.context)

    output_names = [parse_person_name(author) for author in group.authors()]
    for researcher in project.researchers:
        register_name = parse_person_name(researcher.name)
        if register_name is None:
            continue
        best = None
        for author, parsed in zip(group.authors(), output_names):
            level = name_match_level(register_name, parsed)
            if level == "full" or (level == "initial" and best is None):
                best = (researcher.name, author, level)
                if level == "full":
                    break
        if best:
            evidence.author_matches.append(best)
    if not evidence.author_matches and not group.authors():
        # Reports without author metadata (e.g. GOV.UK): names in the body.
        evidence.authors_named_in_text = find_names_in_text(project.researcher_names, statement_text)

    evidence.dataset_hits = [(hit.dataset, hit.label, hit.kind) for hit in find_dataset_mentions(text, project.dataset_terms)]

    kept_hits, boilerplate_hits = group_statement_hits(group, statement_text)
    evidence.boilerplate_phrases = sorted({hit.key for hit in boilerplate_hits})
    for hit in kept_hits:
        if hit.category == "route":
            if hit.key not in evidence.route_phrases:
                evidence.route_phrases.append(hit.key)
        elif hit.environment and hit.environment not in evidence.environment_phrases:
            evidence.environment_phrases.append(hit.environment)
    evidence.environment_consistent = bool(project.environment_code) and project.environment_code in evidence.environment_phrases
    evidence.supporting_phrases = sorted({hit.key for hit in find_phrases(statement_text, SUPPORTING_PHRASES)})
    evidence.index_phrase_hits = group.index_phrase_hits()
    evidence.publication_date = group.publication_date
    evidence.date_in_window = in_window(group.publication_date, project, snapshot_date)
    return evidence


def assign_tier(evidence: Evidence) -> TierDecision:
    """Apply the tier rules; flag pairs the rules cannot settle."""
    reasons: list[str] = []
    if evidence.project_id_mentions and (evidence.has_author or evidence.has_dataset):
        return TierDecision(1, False, ("project_id_quoted",))

    core_match = evidence.has_author and evidence.date_in_window is True
    if core_match and evidence.has_dataset and evidence.has_statement:
        weak = []
        if not evidence.has_full_name_author:
            weak.append("author_initial_only")
        if not evidence.has_named_dataset:
            weak.append("dataset_acronym_only")
        return TierDecision(2, bool(weak), tuple(["route_or_environment_statement", *weak]))

    if core_match and evidence.has_dataset:
        weak = []
        if evidence.environment_phrases and not evidence.environment_consistent:
            weak.append("other_environment_named")
        if not evidence.has_full_name_author:
            weak.append("author_initial_only")
        if not evidence.has_named_dataset:
            weak.append("dataset_acronym_only")
        if evidence.has_index_only_statement:
            # Informational: the index says a phrase matched but no text is
            # available to quote, so an adjudicator could not verify it.
            reasons.append("statement_reported_by_index_without_text")
        return TierDecision(3, bool(weak), tuple(["author_dataset_date", *weak, *reasons]))

    # Near misses worth a look: a route statement (or an SRS/IDS statement
    # matching the project) + author + window, but no dataset found by string
    # rules (it may be described rather than named). SAIL, UKDS SecureLab,
    # NISRA and the Scottish Safe Haven host large non-DEA portfolios, so a
    # statement naming one of them is not enough on its own to queue a pair.
    strong_statement = bool(evidence.route_phrases) or (
        evidence.environment_consistent and set(evidence.environment_phrases) & DEA_SPECIFIC_ENVIRONMENTS
    )
    if core_match and strong_statement and not evidence.has_dataset:
        return TierDecision(None, True, ("statement_author_date_without_dataset",))
    if evidence.project_id_mentions:
        return TierDecision(None, True, ("project_id_quoted_without_author_or_dataset",))
    return TierDecision(None, False, ())


def best_evidence_quote(project: ProjectRecord, group: OutputGroup, evidence: Evidence, max_chars: int = 600) -> str:
    """The verbatim sentence that best supports the pair's tier.

    Order: the sentence quoting the Project ID; a statement sentence (route
    phrase, or the project's own environment) that also names a dataset; any
    such statement sentence; a sentence naming a register dataset.
    """
    if evidence.project_id_mentions:
        target = project.project_id
        for sentence in split_sentences(group.statement_text()):
            if any(m.project_id == target for m in find_project_id_mentions(sentence)):
                return sentence[:max_chars]
        return evidence.project_id_mentions[0][:max_chars]
    best: tuple[int, str] | None = None
    for sentence in split_sentences(group.statement_text()):
        if len(sentence) > 2000:
            continue
        hits = find_phrases(sentence)
        if BOILERPLATE_RE.search(sentence):
            hits = [hit for hit in hits if hit.category != "route"]
        statement = any(
            hit.category == "route" or (hit.environment and hit.environment == project.environment_code)
            for hit in hits
        )
        names_dataset = bool(find_dataset_mentions(sentence, project.dataset_terms))
        rank = 0 if statement and names_dataset else 1 if statement else 2 if names_dataset else None
        if rank is not None and (best is None or rank < best[0]):
            best = (rank, sentence[:max_chars])
            if rank == 0:
                break
    return best[1] if best else ""
