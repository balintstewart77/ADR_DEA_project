"""Text and name matching rules for linking outputs to register projects.

Everything here is a pure function over strings so it can be tested without
network access. The rules are deliberately conservative:

* A ``YYYY/NNN`` string is only a project-ID mention when an accreditation
  context word (project, accreditation, DEA, SRS, ...) sits next to it.
* Accreditation phrases are split into *route* statements (Digital Economy
  Act, Research Accreditation Panel, accredited researcher, UK Statistics
  Authority) and *environment* statements (ONS SRS, IDS, SAIL, NISRA,
  Scottish National Safe Haven, UKDS SecureLab).
* Dataset acronyms match case-sensitively on word boundaries; long names
  match case-insensitively with flexible whitespace and hyphens.
* Author matches need the same family name and a compatible first given name.
"""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

# ---------------------------------------------------------------------------
# Generic text helpers
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_DASHES = str.maketrans({c: "-" for c in "‐‑‒–—―−"})
_QUOTES = str.maketrans({"’": "'", "‘": "'", "`": "'", "“": '"', "”": '"'})


def clean_text(value: object) -> str:
    """Unescape HTML, drop tags, unify dashes/quotes and collapse whitespace."""
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = _TAG_RE.sub(" ", text)
    text = unicodedata.normalize("NFKC", text).translate(_DASHES).translate(_QUOTES)
    # Re-join words hyphenated across PDF line breaks ("Se- cure" -> "Secure").
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return _SPACE_RE.sub(" ", text).strip()


def strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


_REFERENCES_HEADING_RE = re.compile(
    r"(?im)^[ \t]*(?:\d+\.?[ \t]*)?(?:references|bibliography|reference list|works cited)[ \t]*:?[ \t]*$"
)


def strip_references(text: object) -> str:
    """Drop a trailing reference list from raw full text.

    Cuts at the last "References"/"Bibliography" heading on its own line when
    it falls in the second half of the document, so phrases and IDs that only
    occur in citations are not read as statements.
    """
    raw = str(text or "")
    headings = list(_REFERENCES_HEADING_RE.finditer(raw))
    if headings and headings[-1].start() > len(raw) * 0.5:
        return raw[: headings[-1].start()]
    return raw


def normalise_title(title: object) -> str:
    """Key for title de-duplication: accents, case and punctuation removed."""
    text = strip_accents(clean_text(title)).casefold()
    text = re.sub(r"[^\w\s]", " ", text)
    return _SPACE_RE.sub(" ", text).strip()


def normalise_doi(doi: object) -> str | None:
    if doi is None:
        return None
    text = str(doi).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None
    text = re.sub(r"^(?:https?://)?(?:dx\.)?doi\.org/", "", text, flags=re.I)
    text = re.sub(r"^doi:\s*", "", text, flags=re.I)
    text = text.strip().rstrip(".").lower()
    return text if text.startswith("10.") else None


def _flex(phrase: str) -> str:
    """Regex for a phrase with flexible whitespace/hyphens between words."""
    words = [re.escape(word) for word in phrase.split()]
    return r"[\s\-]+".join(words)


# ---------------------------------------------------------------------------
# Accreditation and secure-environment statements
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Phrase:
    key: str
    category: str  # "route" or "environment"
    environment: str | None  # environment code for environment statements
    pattern: re.Pattern


def _phrase(key: str, category: str, regex: str, environment: str | None = None) -> Phrase:
    return Phrase(key, category, environment, re.compile(regex, re.I))


ACCREDITATION_PHRASES: tuple[Phrase, ...] = (
    _phrase("digital_economy_act", "route", r"\bdigital[\s\-]+economy[\s\-]+act\b"),
    _phrase("dea_accredited", "route", r"\bDEA[\s\-]+accredit(?:ed|ation)\b"),
    _phrase("dea_2017", "route", r"\bDEA\s*\(?2017\)?"),
    _phrase("research_accreditation_panel", "route", r"\bresearch[\s\-]+accreditation[\s\-]+panel\b"),
    _phrase("accredited_researcher", "route", r"\baccredited[\s\-]+researchers?\b"),
    _phrase("accredited_research_project", "route", r"\baccredited[\s\-]+research[\s\-]+projects?\b"),
    # Not when cited as an author ("UK Statistics Authority, 2019").
    _phrase(
        "uk_statistics_authority",
        "route",
        r"\b(?:UK|United[\s\-]+Kingdom)[\s\-]+Statistics[\s\-]+Authority\b(?![\s,.]*\(?(?:19|20)\d\d[a-z]?\b)",
    ),
    _phrase(
        "ons_secure_research_service",
        "environment",
        r"\b(?:ONS|Office[\s\-]+for[\s\-]+National[\s\-]+Statistics)(?:'s)?[\s\-]+"
        r"(?:\(ONS\)[\s\-]+)?Secure[\s\-]+Research[\s\-]+Service\b",
        "SRS",
    ),
    _phrase("secure_research_service", "environment", r"\bSecure[\s\-]+Research[\s\-]+Service\b", "SRS"),
    _phrase("srs_project", "environment", r"\bSRS[\s\-]+project\b", "SRS"),
    _phrase("integrated_data_service", "environment", r"\bIntegrated[\s\-]+Data[\s\-]+Service\b", "IDS"),
    _phrase(
        "sail_databank",
        "environment",
        r"\bSAIL[\s\-]+Databank\b|\bSecure[\s\-]+Anonymi[sz]ed[\s\-]+Information[\s\-]+Linkage\b",
        "SAIL",
    ),
    _phrase(
        "nisra_secure_environment",
        "environment",
        r"\b(?:NISRA|Northern[\s\-]+Ireland[\s\-]+Statistics[\s\-]+and[\s\-]+Research[\s\-]+Agency)(?:'s)?"
        r"[\s\-]+(?:\(NISRA\)[\s\-]+)?(?:Secure[\s\-]+Research[\s\-]+Environment|Research[\s\-]+Support[\s\-]+Unit"
        r"|secure[\s\-]+(?:research[\s\-]+)?environment)\b",
        "NISRA",
    ),
    _phrase("scottish_national_safe_haven", "environment", r"\b(?:Scottish[\s\-]+)?National[\s\-]+Safe[\s\-]+Haven\b", "RDS"),
    _phrase(
        "ukds_securelab",
        "environment",
        r"\b(?:UK[\s\-]+Data[\s\-]+Service|UKDS)(?:'s)?[\s\-]+Secure[\s\-]*Lab\b|\bSecure[\s\-]?Lab\b",
        "UKDS",
    ),
)

# Supporting statements: recorded, but they neither name the route nor the
# environment, so they do not satisfy the Tier 2 statement condition.
SUPPORTING_PHRASES: tuple[Phrase, ...] = (
    _phrase(
        "ons_endorsement_disclaimer",
        "supporting",
        r"does[\s\-]+not[\s\-]+imply[\s\-]+the[\s\-]+endorsement[\s\-]+of[\s\-]+the[\s\-]+ONS",
    ),
    _phrase("trusted_research_environment", "supporting", r"\btrusted[\s\-]+research[\s\-]+environments?\b"),
)

# Sentences where a route phrase describes an environment's or a programme's
# standing rather than this project's access: data "made available to
# accredited researchers only" (CVD-COVID-UK / NHS England SDE wording),
# "accredited researchers can apply", or a TRE "accredited under the Digital
# Economy Act". Route phrases inside these sentences are recorded as
# boilerplate and do not count as statements.
BOILERPLATE_RE = re.compile(
    r"made[\s\-]+available[\s\-]+to[\s\-]+accredited[\s\-]+researchers"
    r"|accredited[\s\-]+researchers?[\s\-]+(?:can|may|are[\s\-]+able[\s\-]+to)[\s\-]+apply"
    r"|(?:research[\s\-]+environment|TRE|databank|processing[\s\-]+environment|secure[\s\-]+(?:data|research)[\s\-]+environment)"
    r"\W+(?:\w+\W+){0,6}?accredited[\s\-]+(?:under|by|through)\b"
    r"|accredited[\s\-]+(?:trusted[\s\-]+research[\s\-]+environment|TRE|processing[\s\-]+environment|data[\s\-]+processor)",
    re.I,
)


def statement_hits(text: str) -> tuple[list[PhraseHit], list[PhraseHit]]:
    """(statement hits, boilerplate route hits), judged sentence by sentence."""
    kept: list[PhraseHit] = []
    boilerplate: list[PhraseHit] = []
    for sentence in split_sentences(text):
        hits = find_phrases(sentence)
        if not hits:
            continue
        is_boilerplate = bool(BOILERPLATE_RE.search(sentence))
        for hit in hits:
            (boilerplate if is_boilerplate and hit.category == "route" else kept).append(hit)
    return kept, boilerplate


# Register processing-environment labels -> environment codes.
ENVIRONMENT_CODES = {
    "ONS Secure Research Service (SRS)": "SRS",
    "ONS Secure Research Service": "SRS",
    "Integrated Data Service (IDS)": "IDS",
    "Integrated Data Service": "IDS",
    "SAIL Databank": "SAIL",
    "Northern Ireland Statistics and Research Agency (NISRA)": "NISRA",
    "Northern Ireland Statistics and Research Agency": "NISRA",
    "UK Data Service (UKDS)": "UKDS",
    "UK Data Service": "UKDS",
    "Research Data Scotland": "RDS",
}

# Phrases used as search queries against sources that support phrase search.
SEARCH_PHRASES: tuple[str, ...] = (
    "Digital Economy Act",
    "DEA accredited",
    "Research Accreditation Panel",
    "accredited researcher",
    "ONS Secure Research Service",
    "Secure Research Service",
    "Integrated Data Service",
    "SRS project",
    "UK Statistics Authority",
    "SAIL Databank",
    "NISRA Secure Research Environment",
    "Scottish National Safe Haven",
    "UK Data Service SecureLab",
)


@dataclass(frozen=True)
class PhraseHit:
    key: str
    category: str
    environment: str | None
    matched: str
    start: int
    end: int


def find_phrases(text: str, phrases: Iterable[Phrase] = ACCREDITATION_PHRASES) -> list[PhraseHit]:
    hits: list[PhraseHit] = []
    for phrase in phrases:
        for match in phrase.pattern.finditer(text or ""):
            hits.append(PhraseHit(phrase.key, phrase.category, phrase.environment, match.group(0), match.start(), match.end()))
    hits.sort(key=lambda hit: hit.start)
    return hits


# ---------------------------------------------------------------------------
# Project-ID mentions
# ---------------------------------------------------------------------------

# 2019/003 style; not part of a longer path, number, URL or date.
PROJECT_ID_RE = re.compile(r"(?<![\w/.\-])(20[12]\d)\s?/\s?(\d{3})(?![\w/])")
PROJECT_ID_CONTEXT_RE = re.compile(
    r"\b(?:projects?|accredit\w*|DEA|SRS|IDS|RAP|UKSA|Digital[\s\-]+Economy[\s\-]+Act"
    r"|Research[\s\-]+Accreditation[\s\-]+Panel|Statistics[\s\-]+Authority|Secure[\s\-]+Research[\s\-]+Service)\b",
    re.I,
)
PROJECT_ID_CONTEXT_BEFORE = 80
PROJECT_ID_CONTEXT_AFTER = 40


@dataclass(frozen=True)
class ProjectIdMention:
    project_id: str
    context: str
    start: int


# Context naming the DEA route or an accredited environment specifically, not
# just "project" (university and funder project numbers share the YYYY/NNN form).
DEA_SPECIFIC_CONTEXT_RE = re.compile(
    r"\b(?:DEA|SRS|IDS|RAP|UKSA|Digital[\s\-]+Economy[\s\-]+Act|Research[\s\-]+Accreditation[\s\-]+Panel"
    r"|Statistics[\s\-]+Authority|Secure[\s\-]+Research[\s\-]+Service|Integrated[\s\-]+Data[\s\-]+Service|accredit\w*)\b",
    re.I,
)


def find_project_id_mentions(text: str) -> list[ProjectIdMention]:
    """Register-style IDs with an accreditation context word nearby.

    A bare ``YYYY/NNN`` never counts on its own: one of the context words must
    occur within 80 characters before or 40 characters after the ID.
    """
    text = (text or "").translate(_DASHES)
    mentions: list[ProjectIdMention] = []
    for match in PROJECT_ID_RE.finditer(text):
        before = text[max(0, match.start() - PROJECT_ID_CONTEXT_BEFORE): match.start()]
        after = text[match.end(): match.end() + PROJECT_ID_CONTEXT_AFTER]
        if PROJECT_ID_CONTEXT_RE.search(before) or PROJECT_ID_CONTEXT_RE.search(after):
            context = clean_text(before + match.group(0) + after)
            mentions.append(ProjectIdMention(f"{match.group(1)}/{match.group(2)}", context, match.start()))
    return mentions


def official_project_id(project_or_record_id: str) -> str:
    """``2020/030/a`` (synthetic Record ID) -> ``2020/030`` (published ID)."""
    match = re.match(r"^(20\d\d/\d{3})", str(project_or_record_id).strip())
    return match.group(1) if match else str(project_or_record_id).strip()


# ---------------------------------------------------------------------------
# Dataset terms
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DatasetTerm:
    label: str  # the text being matched, e.g. "Annual Survey of Hours and Earnings"
    dataset: str  # canonical register dataset or linked product it stands for
    kind: str  # "name" or "acronym"
    pattern: re.Pattern = field(compare=False, hash=False, repr=False)


# Acronyms that are too ambiguous to count as a dataset mention on their own.
AMBIGUOUS_ACRONYMS = frozenset({
    "X", "LS", "WAS", "ABS", "APS", "CIS", "MES", "ONS", "NHS", "DFE", "DWP", "HMRC", "UK",
    "IDS", "SRS", "LEO2", "PAYE", "BOE", "UCAS",
    # Topics, not datasets: "COVID-19" is the normaliser's family key for the
    # COVID-19 Infection Survey and would match every pandemic paper.
    "COVID-19", "COVID", "SARS-COV-2",
    # Common outside the register's meaning (GRADE evidence ratings, a
    # multidimensional poverty index, credit agencies, end of life).
    "GRADE", "MPI", "CRA", "EOL",
})
# Single-word names that are too generic to match alone.
GENERIC_NAMES = frozenset({
    "census", "survey", "dataset", "data", "linked", "database", "registrations", "births", "deaths",
    "family court", "crown court", "magistrates court",
    # Reviewed against every short term in the 20261021 register: everyday
    # research phrases, a funder and a parsing remnant, not dataset names.
    "longitudinal study", "innovation panel", "capital stock", "capital stocks", "firm productivity",
    "wellcome trust", "uk: 2023",
})
# Product names made of everyday words: match only in their own capitalisation
# ("Data First" the MoJ programme, not "the data first became available").
CASE_SENSITIVE_NAMES = frozenset({"Data First", "Family Man", "Next Steps"})
_ACRONYM_SUFFIX_RE = re.compile(r"^(?P<name>.*?)\s*\((?P<acronym>[A-Za-z0-9&|/\- ]{2,15})\)\s*$")
_TRAILING_QUALIFIER_RE = re.compile(
    r"\s+(?:-\s+.*|Longitudinal|Person|Persons|Household|Households|X|2|Iteration\s+\d+"
    r"|Waves?\s+[\d\-\s&,]+.*|(?:19|20)\d\d(?:\s*[-/]\s*(?:19|20)?\d\d)?)$",
    re.I,
)


def _is_acronym(value: str) -> bool:
    letters = re.sub(r"[^A-Za-z]", "", value)
    return bool(letters) and value.upper() == value and " " not in value.strip() and len(value) <= 10


def dataset_name_variants(name: str) -> list[tuple[str, str]]:
    """(label, kind) variants for one register dataset or alias spelling."""
    name = clean_text(name).strip(" ,;:")
    if not name or len(name) > 90:
        return []
    variants: list[tuple[str, str]] = []
    pending = [name]
    match = _ACRONYM_SUFFIX_RE.match(name)
    if match:
        pending = [match.group("name").strip()]
        acronym = match.group("acronym").strip()
        if _is_acronym(acronym):
            variants.append((acronym, "acronym"))
    seen: set[str] = set()
    while pending:
        current = pending.pop().strip(" ,;:-")
        if not current or current.casefold() in seen:
            continue
        seen.add(current.casefold())
        if _is_acronym(current):
            variants.append((current, "acronym"))
        else:
            variants.append((current, "name"))
        stripped = _TRAILING_QUALIFIER_RE.sub("", current).strip()
        # Census names keep their year: different censuses are different data.
        if stripped and stripped != current and "census" not in current.casefold():
            pending.append(stripped)
        year_match = re.match(r"^(Census)(?:\s+Wales)?\s+((?:19|20)\d\d)$", current, re.I)
        if year_match:
            variants.append((f"{year_match.group(2)} Census", "name"))
    usable: list[tuple[str, str]] = []
    for label, kind in variants:
        if kind == "acronym":
            if len(re.sub(r"[^A-Za-z]", "", label)) < 2 or label.upper() in AMBIGUOUS_ACRONYMS:
                continue
        else:
            words = label.split()
            if len(words) < 2 and label.casefold() not in {"echild", "rapid", "grade", "guie"}:
                continue
            if len(label) < 8 or label.casefold() in GENERIC_NAMES:
                continue
        if (label, kind) not in usable:
            usable.append((label, kind))
    return usable


def build_dataset_terms(spellings_by_dataset: dict[str, Iterable[str]]) -> list[DatasetTerm]:
    """Compile match terms; ``spellings_by_dataset`` maps a canonical dataset
    (or linked product) to every spelling that should count as naming it."""
    terms: dict[tuple[str, str], DatasetTerm] = {}
    for dataset, spellings in spellings_by_dataset.items():
        for spelling in [dataset, *spellings]:
            for label, kind in dataset_name_variants(spelling):
                key = (label.casefold() if kind == "name" else label, dataset)
                if key in terms:
                    continue
                if kind == "acronym":
                    pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(label)}(?![A-Za-z0-9])")
                elif label in CASE_SENSITIVE_NAMES:
                    pattern = re.compile(rf"(?<![\w]){_flex(label)}(?![\w])")
                else:
                    pattern = re.compile(rf"(?<![\w]){_flex(label)}(?![\w])", re.I)
                terms[key] = DatasetTerm(label, dataset, kind, pattern)
    return list(terms.values())


@dataclass(frozen=True)
class DatasetHit:
    dataset: str
    label: str
    kind: str


def find_dataset_mentions(text: str, terms: Iterable[DatasetTerm]) -> list[DatasetHit]:
    hits: dict[tuple[str, str], DatasetHit] = {}
    for term in terms:
        if term.pattern.search(text or ""):
            hits.setdefault((term.dataset, term.label), DatasetHit(term.dataset, term.label, term.kind))
    return sorted(hits.values(), key=lambda hit: (hit.dataset, hit.kind, hit.label))


# ---------------------------------------------------------------------------
# Author names
# ---------------------------------------------------------------------------

_PARTICLES = {"van", "von", "der", "de", "del", "della", "da", "di", "dos", "du", "la", "le", "bin", "al", "st"}
_HONORIFICS = re.compile(r"^(?:dr|prof|professor|mr|mrs|ms|miss|sir|dame)\.?\s+", re.I)


@dataclass(frozen=True)
class PersonName:
    given: tuple[str, ...]  # normalised given-name tokens (may be initials)
    family: str  # normalised family name, particles included

    @property
    def family_key(self) -> str:
        """Last family token: robust to particles and double-barrelled order."""
        return self.family.split()[-1] if self.family else ""

    @property
    def first_given(self) -> str:
        return self.given[0] if self.given else ""


def _name_tokens(value: str) -> list[str]:
    text = strip_accents(clean_text(value)).casefold()
    text = _HONORIFICS.sub("", text)
    text = re.sub(r"\([^)]*\)", " ", text)  # drop bracketed nicknames/ORCIDs
    text = text.replace(".", ". ").replace("-", " ")
    text = re.sub(r"[^\w\s,']", " ", text)
    return text.split()


def parse_person_name(value: object) -> PersonName | None:
    """Parse "Given Family", "Family, Given" or "Family GI" (initials)."""
    raw = clean_text(value)
    if not raw:
        return None
    if "," in raw:
        family_part, given_part = raw.split(",", 1)
        family_tokens = _name_tokens(family_part)
        given_tokens = _name_tokens(given_part)
    else:
        tokens = _name_tokens(raw)
        if len(tokens) < 2:
            return None
        raw_last = re.sub(r"[^A-Za-z]", "", raw.split()[-1])
        # "Smith JA" / "Smith J" (Europe PMC / GtR style): trailing initials.
        if len(tokens) == 2 and 1 <= len(raw_last) <= 3 and raw_last.isupper():
            family_tokens = [tokens[0]]
            given_tokens = list(tokens[1])
        else:
            # Particles before the last token belong to the family name.
            cut = len(tokens) - 1
            while cut > 1 and tokens[cut - 1] in _PARTICLES:
                cut -= 1
            given_tokens, family_tokens = tokens[:cut], tokens[cut:]
    given = tuple(token.strip(".'") for token in given_tokens if token.strip(".'"))
    family = " ".join(token.strip(".'") for token in family_tokens if token.strip(".'"))
    if not family or not given:
        return None
    return PersonName(given, family)


def name_match_level(left: object, right: object) -> str | None:
    """"full", "initial" or None for two personal names."""
    a = left if isinstance(left, PersonName) else parse_person_name(left)
    b = right if isinstance(right, PersonName) else parse_person_name(right)
    if a is None or b is None:
        return None
    family_ok = a.family_key == b.family_key or a.family.replace(" ", "") == b.family.replace(" ", "")
    if not family_ok:
        # "Costa Dias, Monica" vs "Monica Costa Dias" or swapped double names.
        family_ok = a.family_key in b.family.split() and b.family_key in a.family.split()
    if not family_ok:
        return None
    ga, gb = a.first_given, b.first_given
    if not ga or not gb or ga[0] != gb[0]:
        return None
    if len(ga) == 1 or len(gb) == 1:
        return "initial"
    if ga == gb or (min(len(ga), len(gb)) >= 3 and (ga.startswith(gb) or gb.startswith(ga))):
        return "full"
    return None


def find_names_in_text(names: Iterable[str], text: str) -> list[str]:
    """Register names that appear verbatim (accent/case-insensitive) in text."""
    haystack = strip_accents(clean_text(text)).casefold()
    found = []
    for name in names:
        needle = strip_accents(clean_text(name)).casefold()
        if len(needle.split()) >= 2 and re.search(rf"(?<!\w){_flex(needle)}(?!\w)", haystack):
            found.append(name)
    return found


# ---------------------------------------------------------------------------
# Evidence snippets
# ---------------------------------------------------------------------------

# Sentence ends: punctuation + space + capital, or (PDF/abstract run-ons such
# as "interventions.Records") a lower-case word, full stop, capital, lower.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"'])|(?<=[a-z]{3}[.!?])(?=[A-Z][a-z])")
_STATEMENT_CUE_RE = re.compile(
    r"acknowledg|data availability|data access|data statement|crown copyright|disclaimer|"
    r"accredit|secure research|secure lab|securelab|safe haven|trusted research",
    re.I,
)


def split_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in _SENTENCE_SPLIT_RE.split(clean_text(text)) if sentence.strip()]


def extract_statement_snippets(text: str, *, max_snippets: int = 4, max_chars: int = 600) -> list[str]:
    """Sentences carrying accreditation/environment statements or project IDs.

    Priority: project-ID mentions, then route/environment phrases, then other
    acknowledgement/data-statement cues. Returned verbatim (whitespace
    collapsed) so they can serve as evidence quotes.
    """
    ranked: list[tuple[int, int, str]] = []
    for position, sentence in enumerate(split_sentences(text)):
        if len(sentence) > 2000:
            continue
        if find_project_id_mentions(sentence):
            rank = 0
        elif find_phrases(sentence):
            rank = 1
        elif find_phrases(sentence, SUPPORTING_PHRASES):
            rank = 2
        elif _STATEMENT_CUE_RE.search(sentence):
            rank = 3
        else:
            continue
        ranked.append((rank, position, sentence[:max_chars]))
    ranked.sort()
    unique: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for item in ranked:
        key = item[2].casefold()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    chosen = sorted(unique[:max_snippets], key=lambda item: item[1])
    return [sentence for _, _, sentence in chosen]


def title_similarity(left: object, right: object) -> float:
    """Jaccard similarity of content words in two titles (0-1)."""
    stop = {"the", "of", "and", "in", "a", "an", "to", "for", "on", "with", "by", "from", "at", "using", "uk", "england"}
    a = {word for word in normalise_title(left).split() if word not in stop and len(word) > 2}
    b = {word for word in normalise_title(right).split() if word not in stop and len(word) > 2}
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
