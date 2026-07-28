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

DOMAIN_CHOICES = (
    "Labour Market & Employment — Work, employment, earnings, job quality, workforce dynamics, "
    "skills demand and labour-market transitions. / Education & Skills — Education, learning, "
    "training, skills formation and transitions through education systems and into work. / "
    "Health & Social Care — Health, illness, mental health, wellbeing, mortality as a health "
    "outcome, healthcare services and social care. / Crime & Justice — Crime, victimisation, "
    "public safety, policing, courts, sentencing, prisons, probation and justice outcomes. / "
    "Business & Productivity — Firms, business activity, innovation, productivity, "
    "entrepreneurship, trade, investment and business performance. / Poverty, Wealth & Living "
    "Standards — Material resources, poverty, wealth, debt, benefits, deprivation, cost of living "
    "and household income. / Housing & Planning — Housing, homelessness, tenure, residential "
    "conditions and mobility, neighbourhood change and planning systems. / Migration & "
    "Demographics — Population structure and change, migration, fertility, ageing and mortality "
    "as a demographic outcome. / Environment & Agriculture — Environment, climate, energy, "
    "agriculture, land use, pollution, decarbonisation and environmental impacts. / Public "
    "Finance & Taxation — Taxation, government revenue, public spending, fiscal transfers, tax "
    "reliefs and fiscal policy. / Data Infrastructure & Methodology — Data or methodology as the "
    "primary research object, rather than tools used for another question."
)
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
