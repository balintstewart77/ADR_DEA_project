#!/usr/bin/env python3
"""Apply the approved candidate-0.4 wording alignment to the two canonical DOCX files.

The updater is offline, target-limited and idempotent.  It changes only
word/document.xml in each DOCX and refuses unexpected source wording.
"""

from __future__ import annotations

import html
import re
import tempfile
import zipfile
from pathlib import Path

try:
    import scripts.build_project_owner_redcap_candidate_0_4 as candidate
except ModuleNotFoundError:  # Direct execution places scripts/ on sys.path.
    import build_project_owner_redcap_candidate_0_4 as candidate


ROOT = Path(__file__).resolve().parents[1]
MATERIALS = ROOT / "preregistration/package/06_redcap/participant_materials"
CONSENT = MATERIALS / "Project_Owner_Participant_Information_and_Consent_v3.docx"
QUESTIONNAIRE = MATERIALS / "Project_Owner_Review_Questionnaire_v3.docx"
WORD_DOCUMENT = "word/document.xml"

ACKNOWLEDGEMENT_WORDING = (
    "We would like to acknowledge the researchers who contributed to this study. "
    "Would you like to be acknowledged by name in resulting publications? Choosing to be "
    "acknowledged makes your involvement in this study permanently and publicly identifiable. "
    "Your answer does not affect your participation. If you decline acknowledgement, the study "
    "team will not name or acknowledge you in resulting outputs."
)
ACKNOWLEDGEMENT_OPTIONS = (
    "Response options: Yes, I would like to be acknowledged by name / No, I would prefer not to "
    "be named / I would prefer to decide later. Please contact me about this"
)

DOMAIN_CHOICES = candidate.owner_domain_questionnaire_choices()
PURPOSE_CHOICES = (
    "Descriptive Monitoring — Measuring and describing levels, distributions, patterns or trends "
    "across places, populations or time, without primarily testing an exposure–outcome "
    "relationship. / Outcome Tracking — Linking a naturally occurring exposure, condition or "
    "event to a later outcome, where the exposure is not a deliberate policy or programme. / "
    "Life-Course / Trajectory Analysis — Following people, households, firms or cases over time "
    "to understand trajectories, transitions or cumulative outcomes. / Service Interaction / "
    "Systems Analysis — How people, cases or organisations access, use, move through or are "
    "processed by public services. / Policy Evaluation / Impact Analysis — Assessing the "
    "implementation, effects or consequences of a specific named policy, programme, regulation "
    "or intervention. / Risk Prediction / Early Identification — Predicting risk or identifying "
    "at-risk people, groups or places for screening or early targeting. / Methodological / "
    "Infrastructure Research — Developing, testing, validating or improving research methods, "
    "measures, linkage approaches, infrastructure or data assets."
)
TAG_CHOICES = (
    "Demographic disparities / equity tag — Comparisons across demographic or equality-relevant "
    "groups are central; socioeconomic inequality alone or routine subgroup breakdowns do not "
    "qualify. / COVID-19 & Pandemic — COVID-19 or pandemic conditions are a central research focus "
    "or lens, not merely the period covered by the data."
)

TAG_DEFINITIONS = {
    "5.1 Demographic disparities / equity tag": (
        "A cross-cutting tag for projects whose research question centres on comparing outcomes, "
        "experiences, risks, access, or trajectories across demographic or equality-relevant "
        "groups. Routine subgroup breakdowns do not qualify, and socioeconomic or "
        "deprivation-based inequality alone is insufficient unless comparison across demographic "
        "or equality-relevant groups is central."
    ),
    "5.2 COVID-19 & Pandemic": (
        "A cross-cutting tag for projects where COVID-19, the COVID-19 pandemic, pandemic "
        "conditions, infection surveillance, vaccination, lockdowns, social distancing, "
        "pandemic-related public support, or pandemic consequences are a central condition or "
        "lens for the research question. Research does not qualify merely because its data cover "
        "the pandemic period or because COVID-19 is mentioned incidentally."
    ),
}

PREVIOUS_CLASSIFICATION_INTRO_PARAGRAPHS = (
    "How the classifications work",
    "Research Domains describe what the project is about. Several may apply, and they are not ranked.",
    "Analytical Purposes describe what the project is trying to do analytically. One or two may apply.",
    (
        "Cross-cutting tags show whether Demographic disparities / equity or COVID-19 & Pandemic "
        "is a central feature of the research question. Either, both or neither may apply."
    ),
    (
        "Each proposed classification is shown with a definition. Please judge each one "
        "independently against the actual project and then assess whether its basis is visible "
        "in the public register entry."
    ),
)
CLASSIFICATION_INTRO_PARAGRAPHS = (
    "How the classifications work",
    "Research Domains describe what the project is about. Several may apply, and they are not ranked.",
    "Analytical Purposes describe what the project is trying to do analytically. One or two may apply.",
    (
        "A Research Domain or Analytical Purpose should be treated as applying only when it is "
        "a substantive focus of the project’s research question or analytical aims—not merely "
        "because related terms, datasets, variables, methods or outcomes are mentioned or used."
    ),
    (
        "Cross-cutting tags show whether Demographic disparities / equity or COVID-19 & Pandemic "
        "is a central feature of the research question. Either, both or neither may apply."
    ),
    (
        "Each proposed classification is shown with a definition. Please judge each one "
        "independently against the actual project and then assess whether its basis is visible "
        "in the public register entry."
    ),
)
SUBSTANTIVE_FOCUS_PHRASE = (
    "only when it is a substantive focus of the project’s research question or analytical aims"
)
MISSING_DOMAIN_REMINDER_PHRASE = "a substantive subject of the project"
MISSING_DOMAIN_REMINDER = (
    "Select a missing Research Domain only if it represents "
    f"{MISSING_DOMAIN_REMINDER_PHRASE}, not merely a dataset, variable, population "
    "characteristic or contextual factor used in the research."
)
MISSING_PURPOSE_REMINDER_PHRASE = "a substantive analytical aim of the project"
MISSING_PURPOSE_REMINDER = (
    "Select a missing Analytical Purpose only if it represents "
    f"{MISSING_PURPOSE_REMINDER_PHRASE}, not merely a method, analytical step or secondary "
    "feature of the work."
)

QUESTION_REPLACEMENTS = {
    "Q2d.": (
        "Q2d. Please briefly explain why the basis for this Research Domain is only partly "
        "visible, not visible, or unclear in the public project title and listed datasets.  "
        "[Optional]"
    ),
    "Q3d.": (
        "Q3d. Please briefly explain why the basis for this Analytical Purpose is only partly "
        "visible, not visible, or unclear in the public project title and listed datasets.  "
        "[Optional]"
    ),
    "Q4c.": (
        "Q4c. Is the basis for the proposed status of the Demographic disparities / equity tag "
        "visible in the public project title and datasets listed above?  [Required]"
    ),
    "Q4d.": (
        "Q4d. Please briefly explain why the basis for this proposed tag status is only partly "
        "visible, not visible, or unclear in the public project title and listed datasets.  "
        "[Optional]"
    ),
    "Q5b.": (
        "Q5b. Please briefly explain why the proposed status for the COVID-19 & Pandemic tag does "
        "not fit the actual project.  [Required]"
    ),
    "Q5c.": (
        "Q5c. Is the basis for the proposed status of the COVID-19 & Pandemic tag visible in the "
        "public project title and datasets listed above?  [Required]"
    ),
    "Q5d.": (
        "Q5d. Please briefly explain why the basis for this proposed tag status is only partly "
        "visible, not visible, or unclear in the public project title and listed datasets.  "
        "[Optional]"
    ),
    "Q6b.": "Q6b. Which Research Domain label or labels are missing?  [Required]",
    "Q6c.": (
        "Q6c. Please briefly explain why the selected Research Domain label or labels should be "
        "included.  [Optional]"
    ),
    "Q7b.": "Q7b. Which Analytical Purpose label or labels are missing?  [Required]",
    "Q7c.": (
        "Q7c. Please briefly explain why the selected Analytical Purpose label or labels should "
        "be included.  [Optional]"
    ),
    "Q8c.": (
        "Q8c. Please briefly explain why the selected tag or tags should have been assigned or "
        "applied differently.  [Optional]"
    ),
    "Q9b.": (
        "Q9b. What important information is missing or unclear in the public register entry?  "
        "[Optional]"
    ),
    "Q10a.": (
        "Q10a. Did any of your answers rely on relevant project knowledge that is not visible in "
        "the public register entry?  [Required]"
    ),
    "Q10b.": (
        "Q10b. Please briefly describe the type of additional context that informed your answer.  "
        "[Optional]"
    ),
    "Q12.": (
        "Q12. Do you have any other comments about the proposed classifications, the public "
        "register entry, or the taxonomy?  [Optional]"
    ),
}

APPENDIX_B_CONSENT = (
    "Affirmative intended-recipient confirmation, all ten consent confirmations and affirmative "
    "final consent must be recorded once at owner level, with the Owner Consent instrument "
    "complete. The resulting valid owner-level consent record is joined to each repeating project "
    "review."
)


PARAGRAPH_RE = re.compile(rb"<w:p(?:\s[^>]*)?>.*?</w:p>", re.DOTALL)
RUN_RE = re.compile(rb"<w:r(?:\s[^>]*)?>.*?</w:r>", re.DOTALL)
TEXT_RE = re.compile(rb"(<w:t(?:\s[^>]*)?>)(.*?)(</w:t>)", re.DOTALL)


def paragraph_text(paragraph: bytes) -> str:
    return "".join(
        html.unescape(match.group(2).decode("utf-8"))
        for match in TEXT_RE.finditer(paragraph)
    )


def set_paragraph_text(paragraph: bytes, value: str) -> bytes:
    matches = list(TEXT_RE.finditer(paragraph))
    if not matches:
        raise RuntimeError("target paragraph contains no Word text nodes")
    escaped = html.escape(value, quote=False).encode("utf-8")
    pieces: list[bytes] = []
    cursor = 0
    for index, match in enumerate(matches):
        pieces.append(paragraph[cursor : match.start()])
        pieces.append(match.group(1))
        if index == 0:
            pieces.append(escaped)
        pieces.append(match.group(3))
        cursor = match.end()
    pieces.append(paragraph[cursor:])
    return b"".join(pieces)


def set_run_text(run: bytes, value: str) -> bytes:
    matches = list(TEXT_RE.finditer(run))
    if not matches:
        raise RuntimeError("target Word run contains no text nodes")
    escaped = html.escape(value, quote=False).encode("utf-8")
    pieces: list[bytes] = []
    cursor = 0
    for index, match in enumerate(matches):
        pieces.append(run[cursor : match.start()])
        pieces.append(match.group(1))
        if index == 0:
            pieces.append(escaped)
        pieces.append(match.group(3))
        cursor = match.end()
    pieces.append(run[cursor:])
    return b"".join(pieces)


def set_run_bold(run: bytes, bold: bool) -> bytes:
    run = re.sub(rb"<w:b(?:Cs)?(?:\s[^>]*)?\s*/>", b"", run)
    if not bold:
        return run
    match = re.search(rb"<w:rPr(?:\s[^>]*)?>", run)
    if match:
        return run[: match.end()] + b"<w:b/><w:bCs/>" + run[match.end() :]
    opening = re.match(rb"<w:r(?:\s[^>]*)?>", run)
    if not opening:
        raise RuntimeError("invalid Word run")
    return run[: opening.end()] + b"<w:rPr><w:b/><w:bCs/></w:rPr>" + run[opening.end() :]


def set_paragraph_parts(
    paragraph: bytes, parts: tuple[tuple[str, bool], ...]
) -> bytes:
    runs = list(RUN_RE.finditer(paragraph))
    text_runs = [match for match in runs if TEXT_RE.search(match.group())]
    if not text_runs:
        raise RuntimeError("target paragraph contains no Word text runs")
    template = text_runs[0].group()
    replacement = b"".join(
        set_run_bold(set_run_text(template, text), bold)
        for text, bold in parts
        if text
    )
    first = text_runs[0]
    pieces = [paragraph[: first.start()], replacement]
    cursor = first.end()
    for match in text_runs[1:]:
        pieces.append(paragraph[cursor : match.start()])
        cursor = match.end()
    pieces.append(paragraph[cursor:])
    return b"".join(pieces)


def formatted_paragraph(
    template: bytes, text: str, bold_phrase: str
) -> bytes:
    if text.count(bold_phrase) != 1:
        raise RuntimeError(f"expected one bold phrase {bold_phrase!r}")
    before, after = text.split(bold_phrase)
    return set_paragraph_parts(
        template, ((before, False), (bold_phrase, True), (after, False))
    )


def replace_unique_prefix(xml: bytes, prefix: str, replacement: str) -> bytes:
    paragraphs = list(PARAGRAPH_RE.finditer(xml))
    candidates = [
        match
        for match in paragraphs
        if paragraph_text(match.group()).startswith(prefix)
    ]
    if not candidates:
        aligned = [
            match
            for match in paragraphs
            if paragraph_text(match.group()) == replacement
        ]
        if len(aligned) == 1:
            return xml
    if len(candidates) != 1:
        raise RuntimeError(f"expected one paragraph beginning {prefix!r}; found {len(candidates)}")
    match = candidates[0]
    if paragraph_text(match.group()) == replacement:
        return xml
    updated = set_paragraph_text(match.group(), replacement)
    return xml[: match.start()] + updated + xml[match.end() :]


def replace_response_after_question(
    xml: bytes, question_prefix: str, replacement: str
) -> bytes:
    matches = list(PARAGRAPH_RE.finditer(xml))
    question_indexes = [
        index
        for index, match in enumerate(matches)
        if paragraph_text(match.group()).startswith(question_prefix)
    ]
    if len(question_indexes) != 1:
        raise RuntimeError(f"expected one question {question_prefix!r}")
    for match in matches[question_indexes[0] + 1 :]:
        text = paragraph_text(match.group())
        if text.startswith("Response options:"):
            updated = set_paragraph_text(match.group(), replacement)
            return xml[: match.start()] + updated + xml[match.end() :]
        if re.match(r"Q\d", text):
            break
    raise RuntimeError(f"no response-options paragraph after {question_prefix!r}")


def replace_definition_after_heading(
    xml: bytes, heading: str, replacement: str
) -> bytes:
    """Replace the first non-empty paragraph after a unique section heading."""

    matches = list(PARAGRAPH_RE.finditer(xml))
    heading_indexes = [
        index
        for index, match in enumerate(matches)
        if paragraph_text(match.group()) == heading
    ]
    if len(heading_indexes) != 1:
        raise RuntimeError(f"expected one section heading {heading!r}")
    for match in matches[heading_indexes[0] + 1 :]:
        text = paragraph_text(match.group()).strip()
        if not text:
            continue
        if text == replacement:
            return xml
        if text.startswith("Q") or re.match(r"^\d+\.\d+\s", text):
            raise RuntimeError(f"no definition paragraph after {heading!r}")
        updated = set_paragraph_text(match.group(), replacement)
        return xml[: match.start()] + updated + xml[match.end() :]
    raise RuntimeError(f"no definition paragraph after {heading!r}")


def insert_block_before_prefix(
    xml: bytes, target_prefix: str, block: tuple[str, ...]
) -> bytes:
    matches = list(PARAGRAPH_RE.finditer(xml))
    targets = [
        match
        for match in matches
        if paragraph_text(match.group()).startswith(target_prefix)
    ]
    if len(targets) != 1:
        raise RuntimeError(
            f"expected one paragraph beginning {target_prefix!r}; found {len(targets)}"
        )
    target = targets[0]
    before = [paragraph_text(match.group()) for match in matches if match.end() <= target.start()]
    if tuple(before[-len(block) :]) == block:
        return xml
    existing = [text for text in before if text in block]
    if existing:
        raise RuntimeError(
            f"classification-intro block is partially present before {target_prefix!r}: {existing}"
        )
    inserted = b"".join(set_paragraph_text(target.group(), text) for text in block)
    return xml[: target.start()] + inserted + xml[target.start() :]


def update_classification_intro(xml: bytes) -> bytes:
    matches = list(PARAGRAPH_RE.finditer(xml))
    targets = [
        (index, match)
        for index, match in enumerate(matches)
        if paragraph_text(match.group()).startswith("Read-only classification overview:")
    ]
    if len(targets) != 1:
        raise RuntimeError("expected one read-only classification overview")
    target_index, target = targets[0]
    preceding = matches[:target_index]
    texts = tuple(paragraph_text(match.group()) for match in preceding)
    if texts[-len(CLASSIFICATION_INTRO_PARAGRAPHS) :] == CLASSIFICATION_INTRO_PARAGRAPHS:
        return xml
    if texts[-len(PREVIOUS_CLASSIFICATION_INTRO_PARAGRAPHS) :] != PREVIOUS_CLASSIFICATION_INTRO_PARAGRAPHS:
        raise RuntimeError("expected the aligned predecessor classification-intro block")
    old = preceding[-len(PREVIOUS_CLASSIFICATION_INTRO_PARAGRAPHS) :]
    substantive = formatted_paragraph(
        old[2].group(), CLASSIFICATION_INTRO_PARAGRAPHS[3], SUBSTANTIVE_FOCUS_PHRASE
    )
    replacement = b"".join(
        [old[0].group(), old[1].group(), old[2].group(), substantive, old[3].group(), old[4].group()]
    )
    return xml[: old[0].start()] + replacement + xml[old[-1].end() :]


def insert_formatted_reminder(
    xml: bytes, target_prefix: str, text: str, bold_phrase: str
) -> bytes:
    matches = list(PARAGRAPH_RE.finditer(xml))
    targets = [
        (index, match)
        for index, match in enumerate(matches)
        if paragraph_text(match.group()).startswith(target_prefix)
    ]
    if len(targets) != 1:
        raise RuntimeError(f"expected one paragraph beginning {target_prefix!r}")
    target_index, target = targets[0]
    if target_index and paragraph_text(matches[target_index - 1].group()) == text:
        return xml
    if any(paragraph_text(match.group()) == text for match in matches):
        raise RuntimeError(f"reminder for {target_prefix!r} is not immediately before its target")
    reminder = formatted_paragraph(target.group(), text, bold_phrase)
    return xml[: target.start()] + reminder + xml[target.start() :]


def update_docx(path: Path, transform) -> None:
    resolved = path.resolve()
    if resolved.parent != MATERIALS.resolve() or not resolved.is_file():
        raise RuntimeError(f"unsafe or missing DOCX target: {resolved}")
    with zipfile.ZipFile(resolved, "r") as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]
    old_xml = dict((info.filename, data) for info, data in entries)[WORD_DOCUMENT]
    new_xml = transform(old_xml)
    if new_xml == old_xml:
        return
    with tempfile.NamedTemporaryFile(
        prefix=path.stem + ".", suffix=".tmp", dir=resolved.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w") as target:
            for info, data in entries:
                target.writestr(info, new_xml if info.filename == WORD_DOCUMENT else data)
        with zipfile.ZipFile(temporary_path, "r") as check:
            if check.testzip() is not None:
                raise RuntimeError(f"invalid rewritten DOCX: {temporary_path}")
            check.read(WORD_DOCUMENT)
        temporary_path.replace(resolved)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def update_consent(xml: bytes) -> bytes:
    xml = replace_unique_prefix(
        xml,
        "Acknowledgement preference shown in REDCap:",
        "Acknowledgement preference shown in REDCap: " + ACKNOWLEDGEMENT_WORDING,
    )
    return replace_unique_prefix(xml, "• Yes, I would like", ACKNOWLEDGEMENT_OPTIONS)


def update_questionnaire(xml: bytes) -> bytes:
    for heading, definition in TAG_DEFINITIONS.items():
        xml = replace_definition_after_heading(xml, heading, definition)
    for prefix, replacement in QUESTION_REPLACEMENTS.items():
        xml = replace_unique_prefix(xml, prefix, replacement)
    xml = replace_response_after_question(
        xml, "Q4c.", "Response options: Clearly visible / Partly visible / Not visible / Unsure"
    )
    xml = replace_response_after_question(
        xml, "Q5c.", "Response options: Clearly visible / Partly visible / Not visible / Unsure"
    )
    xml = replace_response_after_question(xml, "Q6b.", "Response options: " + DOMAIN_CHOICES)
    xml = replace_response_after_question(xml, "Q7b.", "Response options: " + PURPOSE_CHOICES)
    xml = replace_response_after_question(xml, "Q8b.", "Response options: " + TAG_CHOICES)
    xml = replace_response_after_question(
        xml,
        "Q11b.",
        "Response options: Missing or inadequately represented category / Ambiguous or "
        "overlapping category boundaries / Other taxonomy problem",
    )
    xml = update_classification_intro(xml)
    xml = insert_formatted_reminder(
        xml, "Q6b.", MISSING_DOMAIN_REMINDER, MISSING_DOMAIN_REMINDER_PHRASE
    )
    xml = insert_formatted_reminder(
        xml, "Q7b.", MISSING_PURPOSE_REMINDER, MISSING_PURPOSE_REMINDER_PHRASE
    )
    return replace_unique_prefix(
        xml,
        "affirmative intended-recipient confirmation and consent recorded once at owner level",
        APPENDIX_B_CONSENT,
    )


def main() -> int:
    update_docx(CONSENT, update_consent)
    update_docx(QUESTIONNAIRE, update_questionnaire)
    print(CONSENT.relative_to(ROOT).as_posix())
    print(QUESTIONNAIRE.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
