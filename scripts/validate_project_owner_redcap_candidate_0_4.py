#!/usr/bin/env python3
"""Validate owner-redcap-candidate-0.4 entirely offline."""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import re
import sys
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping
from xml.etree import ElementTree

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import scripts.build_project_owner_redcap_candidate_0_4 as builder
    import scripts.validate_project_owner_redcap_candidate_0_3 as predecessor
except ModuleNotFoundError:  # Direct execution places scripts/ on sys.path.
    import build_project_owner_redcap_candidate_0_4 as builder
    import validate_project_owner_redcap_candidate_0_3 as predecessor


ROOT = Path(__file__).resolve().parents[1]
REDCAP_STRUCTURAL_FIELDS = {
    "redcap_repeat_instrument",
    "redcap_repeat_instance",
    "owner_consent_complete",
    "project_review_complete",
}
MISSING_DOMAIN_REVIEW = (
    builder.PACKAGE
    / "project_owner_missing_domain_microdefinitions_candidate_0.4_review.md"
)
DOMAIN_CONCORDANCE = (
    builder.PACKAGE / "project_owner_domain_wording_concordance_candidate_0.4.md"
)


class ValidationError(RuntimeError):
    pass


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        header = list(reader.fieldnames or [])
    if not header or any(None in row for row in rows):
        raise ValidationError(f"malformed CSV: {path}")
    return rows, header


def normalise_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("’", "'").replace("‘", "'")
    value = value.replace("–", "-").replace("—", "-")
    value = re.sub(r"\s+", " ", value).strip()
    return re.sub(r"\s+([.,;:!?])", r"\1", value)


def plain_redcap_label(value: str) -> str:
    """Return participant-visible REDCap HTML as normalised plain text."""
    value = re.sub(r"(?i)<br\s*/?>", " ", value)
    value = re.sub(r"<[^>]+>", "", value)
    return normalise_text(html.unescape(value))


def docx_paragraphs(path: Path, *, strip_checkbox: bool = False) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace))
        if text.strip():
            if strip_checkbox:
                text = text.lstrip("☐ ")
            paragraphs.append(normalise_text(text))
    return paragraphs


def docx_paragraph_run_formatting(path: Path) -> list[tuple[str, list[tuple[str, bool]]]]:
    """Return paragraph text and explicit run-level bold state from a DOCX."""

    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    result: list[tuple[str, list[tuple[str, bool]]]] = []
    for paragraph in root.findall(".//w:p", namespace):
        runs: list[tuple[str, bool]] = []
        for run in paragraph.findall("./w:r", namespace):
            text = "".join(node.text or "" for node in run.findall(".//w:t", namespace))
            if not text:
                continue
            bold_node = run.find("./w:rPr/w:b", namespace)
            bold = bold_node is not None and bold_node.get(
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "true"
            ).lower() not in {"0", "false", "off"}
            runs.append((text, bold))
        text = normalise_text("".join(value for value, _ in runs))
        if text:
            result.append((text, runs))
    return result


def validate_exact_docx_bold_phrase(
    path: Path, paragraph_text: str, bold_phrase: str, label: str
) -> list[str]:
    matches = [
        runs
        for text, runs in docx_paragraph_run_formatting(path)
        if text == normalise_text(paragraph_text)
    ]
    if len(matches) != 1:
        return [f"{label} paragraph occurs {len(matches)} times in canonical DOCX"]
    bold_text = normalise_text("".join(text for text, bold in matches[0] if bold))
    if bold_text != normalise_text(bold_phrase):
        return [f"{label} DOCX bold text differs: {bold_text!r}"]
    if all(bold for _, bold in matches[0]):
        return [f"{label} entire paragraph is bold"]
    return []


def participant_doc_paragraphs() -> list[str]:
    return docx_paragraphs(builder.PARTICIPANT_SOURCE, strip_checkbox=True)


def questionnaire_doc_paragraphs() -> list[str]:
    return docx_paragraphs(builder.QUESTIONNAIRE_SOURCE)


def markdown_table_rows(path: Path) -> list[dict[str, str]]:
    """Parse the first Markdown table in an audit artefact."""
    lines = path.read_text(encoding="utf-8").splitlines()
    table = [line for line in lines if line.startswith("| ")]
    if len(table) < 2:
        raise ValidationError(f"Markdown table is absent: {path}")
    headers = [cell.strip() for cell in table[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table[1:]:
        if set(line.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        cells = [cell.strip().replace("\\|", "|") for cell in line.strip("|").split("|")]
        if len(cells) != len(headers):
            raise ValidationError(f"Markdown table is malformed: {path}")
        rows.append(dict(zip(headers, cells, strict=True)))
    return rows


def missing_domain_review_rows() -> list[dict[str, str]]:
    return markdown_table_rows(MISSING_DOMAIN_REVIEW)


def domain_concordance_rows() -> list[dict[str, str]]:
    return markdown_table_rows(DOMAIN_CONCORDANCE)


QUESTIONNAIRE_LABEL_MAP = {
    "Q2a.": "po_d01_fit",
    "Q2b.": "po_d01_correct_explain",
    "Q2c.": "po_d01_vis",
    "Q2d.": "po_d01_vis_explain",
    "Q3a.": "po_p01_fit",
    "Q3b.": "po_p01_correct_explain",
    "Q3c.": "po_p01_vis",
    "Q3d.": "po_p01_vis_explain",
    "Q4a.": "po_t01_correct",
    "Q4b.": "po_t01_correct_explain",
    "Q4c.": "po_t01_vis",
    "Q4d.": "po_t01_vis_explain",
    "Q5a.": "po_t02_correct",
    "Q5b.": "po_t02_correct_explain",
    "Q5c.": "po_t02_vis",
    "Q5d.": "po_t02_vis_explain",
    "Q6a.": "po_miss_domain",
    "Q6b.": "po_miss_domains",
    "Q6c.": "po_miss_domain_basis",
    "Q7a.": "po_miss_purpose",
    "Q7b.": "po_miss_purposes",
    "Q7c.": "po_miss_purpose_basis",
    "Q8a.": "po_miss_tag",
    "Q8b.": "po_miss_tags",
    "Q8c.": "po_miss_tag_basis",
    "Q9a.": "po_sufficiency",
    "Q9b.": "po_suff_explain",
    "Q10a.": "po_nonpublic",
    "Q10b.": "po_nonpublic_note",
    "Q11a.": "po_taxonomy_fit",
    "Q11b.": "po_tax_issue",
    "Q11c.": "po_tax_explain",
    "Q12.": "po_other_comment",
}
QUESTIONNAIRE_CHOICE_MAP = {
    key: QUESTIONNAIRE_LABEL_MAP[key]
    for key in (
        "Q2a.", "Q2c.", "Q3a.", "Q3c.", "Q4a.", "Q4c.", "Q5a.",
        "Q5c.", "Q6a.", "Q6b.", "Q7a.", "Q7b.", "Q8a.", "Q8b.",
        "Q9a.", "Q10a.", "Q11a.", "Q11b.",
    )
}
QUESTIONNAIRE_BRANCH_MAP = {
    "Q2b.": ("Branching: Shown if Q2a is Does not fit.", "[po_d01_fit] = '2'"),
    "Q2d.": (
        "Branching: Shown if Q2c is Partly visible, Not visible or Unsure.",
        "[po_d01_vis] = '1' or [po_d01_vis] = '0' or [po_d01_vis] = '3'",
    ),
    "Q3b.": ("Branching: Shown if Q3a is Does not fit.", "[po_p01_fit] = '2'"),
    "Q3d.": (
        "Branching: Shown if Q3c is Partly visible, Not visible or Unsure.",
        "[po_p01_vis] = '1' or [po_p01_vis] = '0' or [po_p01_vis] = '3'",
    ),
    "Q4b.": ("Branching: Shown if Q4a is No.", "[po_t01_correct] = '0'"),
    "Q4d.": (
        "Branching: Shown if Q4c is Partly visible, Not visible or Unsure.",
        "[po_t01_vis] = '1' or [po_t01_vis] = '0' or [po_t01_vis] = '3'",
    ),
    "Q5b.": ("Branching: Shown if Q5a is No.", "[po_t02_correct] = '0'"),
    "Q5d.": (
        "Branching: Shown if Q5c is Partly visible, Not visible or Unsure.",
        "[po_t02_vis] = '1' or [po_t02_vis] = '0' or [po_t02_vis] = '3'",
    ),
    "Q6b.": ("Branching: Shown if Q6a is Yes; at least one option is required when shown.", "[po_miss_domain] = '1'"),
    "Q7b.": ("Branching: Shown if Q7a is Yes; at least one option is required when shown.", "[po_miss_purpose] = '1'"),
    "Q8b.": ("Branching: Shown if Q8a is Yes; at least one option is required when shown.", "[po_miss_tag] = '1'"),
    "Q9b.": ("Branching: Shown if Q9a is Partial or Insufficient.", "[po_sufficiency] = '2' or [po_sufficiency] = '3'"),
    "Q10b.": ("Branching: Shown if Q10a is Yes or Unsure.", "[po_nonpublic] = '1' or [po_nonpublic] = '2'"),
    "Q11b.": ("Branching: Shown if Q11a is Partial Fit or No Fit.", "[po_taxonomy_fit] = '2' or [po_taxonomy_fit] = '3'"),
    "Q11c.": ("Branching: Shown if Q11a is Partial Fit or No Fit.", "[po_taxonomy_fit] = '2' or [po_taxonomy_fit] = '3'"),
}


def _question_index(paragraphs: list[str], prefix: str) -> int:
    indexes = [index for index, text in enumerate(paragraphs) if text.startswith(prefix)]
    if len(indexes) != 1:
        raise ValidationError(f"questionnaire has {len(indexes)} occurrences of {prefix}")
    return indexes[0]


def _question_following(paragraphs: list[str], prefix: str, marker: str) -> str:
    index = _question_index(paragraphs, prefix)
    for text in paragraphs[index + 1 :]:
        if text.startswith(marker):
            return text
        if re.match(r"^Q\d", text):
            break
    raise ValidationError(f"questionnaire {prefix} has no following {marker}")


def _documented_question_label(paragraphs: list[str], prefix: str) -> str:
    text = paragraphs[_question_index(paragraphs, prefix)][len(prefix) :].strip()
    return re.sub(r"\s+\[(Required|Optional)\]$", "", text).strip()


def _definition_after_heading(paragraphs: list[str], heading: str) -> str:
    indexes = [index for index, text in enumerate(paragraphs) if text == heading]
    if len(indexes) != 1:
        raise ValidationError(
            f"questionnaire has {len(indexes)} occurrences of heading {heading!r}"
        )
    return paragraphs[indexes[0] + 1]


def _dictionary_label_for_document(row: Mapping[str, str]) -> str:
    text = re.sub(r"^Optional:\s*", "", row["Field Label"])
    replacements = {
        "[prop_d01_label]": "[proposed Research Domain label]",
        "[prop_p01_label]": "[proposed Analytical Purpose label]",
        "[prop_t01_label]": "Demographic disparities / equity tag",
        "[prop_t02_label]": "COVID-19 & Pandemic",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def validate_participant_documents(by: Mapping[str, Mapping[str, str]]) -> list[str]:
    errors: list[str] = []
    consent = participant_doc_paragraphs()
    consent_text = "\n".join(consent).lower()
    for obsolete in (
        "your participation will not be disclosed",
        "declining means your participation will not be disclosed",
    ):
        if obsolete in consent_text:
            errors.append(f"consent document retains obsolete wording: {obsolete}")
    ack_paragraph = next(
        (text for text in consent if text.startswith("Acknowledgement preference shown in REDCap:")),
        "",
    )
    documented_ack = ack_paragraph.removeprefix(
        "Acknowledgement preference shown in REDCap:"
    ).strip()
    if documented_ack != normalise_text(by["ack_pref"]["Field Label"]):
        errors.append("consent-document acknowledgement label differs from dictionary")
    ack_options = next((text for text in consent if text.startswith("Response options: Yes, I would")), "")
    expected_ack_options = " / ".join(parse_choices(by["ack_pref"]["Choices, Calculations, OR Slider Labels"]).values())
    if ack_options.removeprefix("Response options:").strip() != normalise_text(expected_ack_options):
        errors.append("consent-document acknowledgement options differ from dictionary")

    questionnaire = questionnaire_doc_paragraphs()
    questionnaire_text = "\n".join(questionnaire).lower()
    for obsolete in ("q13", "po_quote_permission", "quotation permission", "may the study use a short anonymised quotation"):
        if obsolete in questionnaire_text:
            errors.append(f"questionnaire retains obsolete quotation item: {obsolete}")
    intro = [normalise_text(item) for item in builder.CLASSIFICATION_INTRO_PARAGRAPHS]
    intro_indexes = [
        index for index, paragraph in enumerate(questionnaire) if paragraph == intro[0]
    ]
    overview_indexes = [
        index
        for index, paragraph in enumerate(questionnaire)
        if paragraph.startswith("Read-only classification overview:")
    ]
    if len(intro_indexes) != 1:
        errors.append("questionnaire does not contain the classification orientation exactly once")
    elif questionnaire[intro_indexes[0] : intro_indexes[0] + len(intro)] != intro:
        errors.append("questionnaire classification orientation is not the exact contiguous block")
    if len(overview_indexes) != 1:
        errors.append("questionnaire does not contain one read-only classification overview")
    elif len(intro_indexes) == 1 and intro_indexes[0] + len(intro) != overview_indexes[0]:
        errors.append("questionnaire orientation is not immediately before the overview")
    if plain_redcap_label(by["po_intro"]["Field Label"]) != normalise_text(
        " ".join(builder.CLASSIFICATION_INTRO_PARAGRAPHS)
    ):
        errors.append("dictionary po_intro differs from the canonical questionnaire block")
    if by["po_intro"]["Field Label"].count(
        f"<strong>{builder.SUBSTANTIVE_FOCUS_PHRASE}</strong>"
    ) != 1:
        errors.append("po_intro does not strongly emphasise the exact governing phrase once")
    errors.extend(
        validate_exact_docx_bold_phrase(
            builder.QUESTIONNAIRE_SOURCE,
            builder.SUBSTANTIVE_FOCUS_PARAGRAPH,
            builder.SUBSTANTIVE_FOCUS_PHRASE,
            "substantive-focus rule",
        )
    )
    reminder_specs = (
        ("Q6b.", "po_miss_domain_reminder", builder.MISSING_DOMAIN_REMINDER, builder.MISSING_DOMAIN_REMINDER_PHRASE),
        ("Q7b.", "po_miss_purpose_reminder", builder.MISSING_PURPOSE_REMINDER, builder.MISSING_PURPOSE_REMINDER_PHRASE),
    )
    for prefix, variable, reminder, phrase in reminder_specs:
        question_index = _question_index(questionnaire, prefix)
        if not question_index or questionnaire[question_index - 1] != normalise_text(reminder):
            errors.append(f"questionnaire {variable} is not immediately before {prefix}")
        errors.extend(
            validate_exact_docx_bold_phrase(
                builder.QUESTIONNAIRE_SOURCE, reminder, phrase, variable
            )
        )
    if "save & return later" in by["po_intro"]["Field Label"].lower():
        errors.append("po_intro duplicates Save & Return Later guidance")
    for obsolete in (
        "synthetic-qa placeholder",
        "attach or link the final formatted owner-facing taxonomy reference",
        "taxonomy reference pdf",
    ):
        if obsolete in questionnaire_text:
            errors.append(f"questionnaire retains taxonomy-reference text: {obsolete}")
    for prefix, variable in QUESTIONNAIRE_LABEL_MAP.items():
        documented = _documented_question_label(questionnaire, prefix)
        expected = normalise_text(_dictionary_label_for_document(by[variable]))
        if documented != expected:
            errors.append(f"questionnaire {prefix}/{variable} label differs")
    for prefix, variable in QUESTIONNAIRE_CHOICE_MAP.items():
        documented = _question_following(questionnaire, prefix, "Response options:")
        expected = " / ".join(
            parse_choices(by[variable]["Choices, Calculations, OR Slider Labels"]).values()
        )
        if documented.removeprefix("Response options:").strip() != normalise_text(expected):
            errors.append(f"questionnaire {prefix}/{variable} response options differ")
    for prefix, (documented_branch, dictionary_branch) in QUESTIONNAIRE_BRANCH_MAP.items():
        variable = QUESTIONNAIRE_LABEL_MAP[prefix]
        if _question_following(questionnaire, prefix, "Branching:") != documented_branch:
            errors.append(f"questionnaire {prefix}/{variable} branching prose differs")
        if by[variable]["Branching Logic (Show field only if...)"] != dictionary_branch:
            errors.append(f"dictionary {variable} branching differs from questionnaire semantics")
    if normalise_text(builder.APPENDIX_B_CONSENT_WORDING) not in questionnaire:
        errors.append("questionnaire Appendix B omits full candidate-0.4 consent validity")
    if "or unclear" not in _documented_question_label(questionnaire, "Q3d."):
        errors.append("Q3d does not include or unclear")
    if "or unclear" not in _documented_question_label(questionnaire, "Q4d."):
        errors.append("Q4d does not include or unclear")
    headings = {
        "5.1 Demographic disparities / equity tag": builder.OPERATIONAL_TAGS[0],
        "5.2 COVID-19 & Pandemic": builder.OPERATIONAL_TAGS[1],
    }
    for heading, label in headings.items():
        expected = normalise_text(builder.TAG_DEFINITIONS[label])
        if _definition_after_heading(questionnaire, heading) != expected:
            errors.append(f"questionnaire {heading} full definition differs")
        if questionnaire.count(expected) != 2:
            errors.append(
                f"questionnaire main section and Appendix A do not contain two exact {label} definitions"
            )
    return errors


def load_dictionary(path: Path = builder.DICTIONARY) -> list[dict[str, str]]:
    rows, header = read_csv(path)
    if header != builder.base.HEADERS:
        raise ValidationError("candidate 0.4 dictionary header differs")
    return rows


def dictionary_by_name() -> dict[str, dict[str, str]]:
    rows = load_dictionary()
    return {row["Variable / Field Name"]: row for row in rows}


def parse_choices(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    if not value:
        return result
    for item in value.split(" | "):
        code, label = item.split(", ", 1)
        result[code] = label
    return result


def consent_items_complete(owner: Mapping[str, object]) -> bool:
    return all(str(owner.get(name, "")) == "1" for name in builder.CONSENT_NAMES)


def valid_owner_consent(owner: Mapping[str, object]) -> bool:
    return (
        str(owner.get("intended_recipient", "")) == "1"
        and consent_items_complete(owner)
        and str(owner.get("owner_consent", "")) == "1"
        and str(owner.get("owner_consent_complete", "")) == "2"
    )


def analytical_completion_missing(
    review: Mapping[str, object], owner: Mapping[str, object]
) -> list[str]:
    legacy_owner = {
        "intended_recipient": "1",
        "owner_consent": "1",
    }
    missing = [
        item
        for item in predecessor.analytical_completion_missing(review, legacy_owner)
        if item not in {"joined_intended_recipient", "joined_owner_consent"}
    ]
    if str(owner.get("intended_recipient", "")) != "1":
        missing.insert(0, "joined_intended_recipient")
    for name in builder.CONSENT_NAMES:
        if str(owner.get(name, "")) != "1":
            missing.append(f"joined_{name}")
    if not consent_items_complete(owner):
        missing.append("joined_consent_items_complete")
    if str(owner.get("owner_consent", "")) != "1":
        missing.append("joined_owner_consent")
    if str(owner.get("owner_consent_complete", "")) != "2":
        missing.append("joined_owner_consent_complete")
    return list(dict.fromkeys(missing))


def prepare_long_export(
    rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    materialised = [dict(row) for row in rows]
    owner_rows = [
        row for row in materialised if not str(row.get("redcap_repeat_instrument", ""))
    ]
    review_rows = [
        row
        for row in materialised
        if row.get("redcap_repeat_instrument") == "project_review"
    ]
    owners = {str(row.get("owner_id")): row for row in owner_rows}
    joined: list[dict[str, object]] = []
    for review in review_rows:
        owner = owners.get(str(review.get("owner_id")), {})
        item = dict(review)
        item["joined_intended_recipient"] = owner.get("intended_recipient", "")
        for name in builder.CONSENT_NAMES:
            item[f"joined_{name}"] = owner.get(name, "")
        item["joined_consent_items_complete"] = (
            "1" if consent_items_complete(owner) else "0"
        )
        item["joined_owner_consent"] = owner.get("owner_consent", "")
        item["joined_owner_consent_complete"] = owner.get(
            "owner_consent_complete", ""
        )
        missing = analytical_completion_missing(review, owner)
        item["analytical_completion_missing"] = missing
        item["analytically_complete"] = not missing
        item["substantive_analysis_eligible"] = not missing
        joined.append(item)
    return owner_rows, joined


def validate_dictionary() -> dict[str, object]:
    rows = load_dictionary()
    errors: list[str] = []
    names = [row["Variable / Field Name"] for row in rows]
    counts = Counter(row["Form Name"] for row in rows)
    if tuple(dict.fromkeys(row["Form Name"] for row in rows)) != builder.base.FORMS:
        errors.append("dictionary does not contain exactly the intended two instruments")
    if counts != Counter({"owner_consent": 22, "project_review": 97}):
        errors.append(f"field counts differ: {dict(counts)}")
    if len(rows) != 119 or len(names) != len(set(names)):
        errors.append("total field count or uniqueness differs")
    by = {row["Variable / Field Name"]: row for row in rows}
    if set(builder.CONSENT_NAMES) - set(by):
        errors.append("one or more consent confirmation variables are absent")
    document_paragraphs = set(participant_doc_paragraphs())
    for name, wording in builder.CONSENT_ITEMS:
        row = by.get(name, {})
        if row.get("Form Name") != "owner_consent":
            errors.append(f"{name} is not owner-level")
        if normalise_text(row.get("Field Label", "")) != normalise_text(wording):
            errors.append(f"{name} wording differs")
        if normalise_text(wording) not in document_paragraphs:
            errors.append(f"{name} is not present in Participant Information v3")
        if row.get("Branching Logic (Show field only if...)") != "[intended_recipient] = '1'":
            errors.append(f"{name} intended-recipient branch differs")
        if parse_choices(row.get("Choices, Calculations, OR Slider Labels", "")) != {
            "1": "Confirmed",
            "0": "Not confirmed",
        }:
            errors.append(f"{name} response codes differ")
    if by["consent_items_complete"]["Choices, Calculations, OR Slider Labels"] != builder.ALL_CONFIRMED_EXPRESSION:
        errors.append("all-confirmed expression differs")
    if by["consent_items_complete"]["Field Type"] != "calc":
        errors.append("all-confirmed field is not calculated")
    if normalise_text(by["owner_consent"]["Field Label"]) != normalise_text(builder.FINAL_CONSENT_LABEL):
        errors.append("final consent wording differs")
    if parse_choices(by["owner_consent"]["Choices, Calculations, OR Slider Labels"]) != {
        "1": "Yes, I agree to take part",
        "0": "No, I do not wish to take part",
    }:
        errors.append("final consent codes differ")
    if by["owner_consent"]["Branching Logic (Show field only if...)"] != "[intended_recipient] = '1'":
        errors.append("active decline is not available after intended-recipient Yes")
    if by["ack_pref"]["Required Field?"]:
        errors.append("acknowledgement is not optional")
    if by["ack_pref"]["Branching Logic (Show field only if...)"] != (
        "[intended_recipient] = '1' and [consent_items_complete] = '1' and "
        "[owner_consent] = '1'"
    ):
        errors.append("acknowledgement branch differs")
    ack = normalise_text(by["ack_pref"]["Field Label"])
    if "If you decline acknowledgement, the study team will not name or acknowledge you in resulting outputs." not in ack:
        errors.append("corrected acknowledgement wording absent")
    if "participation will not be disclosed" in ack.lower():
        errors.append("obsolete acknowledgement wording retained")
    if by["ack_pref"]["Choices, Calculations, OR Slider Labels"] != builder.ACKNOWLEDGEMENT_CHOICES:
        errors.append("acknowledgement response labels differ")
    if "po_quote_permission" in by:
        errors.append("obsolete quotation-permission field retained")
    if "po_taxonomy_ref" in by:
        errors.append("non-production taxonomy-reference field retained")
    if names.count("po_intro") != 1 or by["po_intro"]["Form Name"] != "project_review":
        errors.append("po_intro is not exactly one Project Review field")
    if not (
        names.index("datasets_used")
        < names.index("po_intro")
        < names.index("po_classification_overview")
    ):
        errors.append("participant-visible orientation/overview order differs")
    reminder_expectations = (
        ("po_miss_domain_reminder", "po_miss_domains", builder.MISSING_DOMAIN_REMINDER_HTML, builder.MISSING_DOMAIN_REMINDER, builder.MISSING_DOMAIN_REMINDER_PHRASE, "[po_miss_domain] = '1'"),
        ("po_miss_purpose_reminder", "po_miss_purposes", builder.MISSING_PURPOSE_REMINDER_HTML, builder.MISSING_PURPOSE_REMINDER, builder.MISSING_PURPOSE_REMINDER_PHRASE, "[po_miss_purpose] = '1'"),
    )
    for reminder, target, markup, plain, phrase, branch in reminder_expectations:
        row = by.get(reminder, {})
        if names.count(reminder) != 1 or row.get("Form Name") != "project_review":
            errors.append(f"{reminder} is not exactly one Project Review field")
            continue
        if row.get("Field Type") != "descriptive" or row.get("Required Field?"):
            errors.append(f"{reminder} field type/requiredness differs")
        if row.get("Field Label") != markup or plain_redcap_label(row.get("Field Label", "")) != normalise_text(plain):
            errors.append(f"{reminder} wording or markup differs")
        if row.get("Field Label", "").count(f"<strong>{phrase}</strong>") != 1:
            errors.append(f"{reminder} does not strongly emphasise only its governing phrase")
        if row.get("Branching Logic (Show field only if...)") != branch:
            errors.append(f"{reminder} branching differs")
        if names.index(reminder) + 1 != names.index(target):
            errors.append(f"{reminder} is not immediately before {target}")
    if names[-2:] != ["po_other_comment", "po_final_warning"]:
        errors.append("final warning is not immediately after final comments")
    if "quotation permission" in by["po_final_warning"]["Field Label"].lower():
        errors.append("final warning still refers to quotation permission")
    direct_names = {
        name for name in names if re.search(r"(^|_)(name|email|affiliation)($|_)", name)
    }
    if direct_names:
        errors.append(f"direct-identifier fields introduced: {sorted(direct_names)}")
    errors.extend(validate_participant_documents(by))

    predecessor_rows, _ = read_csv(builder.base.ROOT / "preregistration/package/06_redcap/project_owner_redcap_data_dictionary_candidate_0.3.csv")
    old_review = {
        row["Variable / Field Name"]: row
        for row in predecessor_rows
        if row["Form Name"] == "project_review"
        and row["Variable / Field Name"] not in {"po_quote_permission", "po_taxonomy_ref"}
    }
    new_review = {
        row["Variable / Field Name"]: row
        for row in rows
        if row["Form Name"] == "project_review"
    }
    old_review["po_other_comment"] = dict(old_review["po_other_comment"])
    old_review["po_other_comment"]["Section Header"] = "Final comments"
    for name, label in builder.QUESTIONNAIRE_FIELD_LABELS.items():
        old_review[name] = dict(old_review[name])
        old_review[name]["Field Label"] = label
    old_review["po_intro"] = dict(old_review["po_intro"])
    old_review["po_intro"]["Field Label"] = builder.CLASSIFICATION_INTRO_LABEL
    for reminder in ("po_miss_domain_reminder", "po_miss_purpose_reminder"):
        old_review[reminder] = new_review[reminder]
    old_review["po_miss_domains"] = dict(old_review["po_miss_domains"])
    old_review["po_miss_domains"][
        "Choices, Calculations, OR Slider Labels"
    ] = builder.owner_domain_redcap_choices()
    old_review["po_tax_issue"] = dict(old_review["po_tax_issue"])
    old_review["po_tax_issue"]["Choices, Calculations, OR Slider Labels"] = (
        "1, Missing or inadequately represented category | "
        "2, Ambiguous or overlapping category boundaries | 5, Other taxonomy problem"
    )
    if old_review != new_review:
        errors.append("Project Review changed beyond documented candidate-0.4 participant alignment")
    if errors:
        raise ValidationError("\n".join(errors))
    return {"fields": len(rows), "forms": dict(counts), "consent_items": 10}


def validate_specs_and_fixture() -> dict[str, object]:
    errors: list[str] = []
    branch = yaml.safe_load(builder.BRANCH_SPEC.read_text(encoding="utf-8"))
    if branch["survey_queue"]["project_review"]["condition"] != builder.QUEUE_CONDITION:
        errors.append("Survey Queue condition differs")
    consent = branch.get("owner_consent_v3", {})
    if consent.get("all_confirmed_calculation") != builder.ALL_CONFIRMED_EXPRESSION:
        errors.append("branch specification all-confirmed expression differs")
    if consent.get("confirmation_fields") != list(builder.CONSENT_NAMES):
        errors.append("branch specification consent-item order differs")
    if consent.get("participant_document_sha256") != builder.PARTICIPANT_SOURCE_SHA256:
        errors.append("branch specification consent-document hash differs")
    if consent.get("participant_document_size_bytes") != builder.PARTICIPANT_SOURCE_SIZE:
        errors.append("branch specification consent-document size differs")
    review_document = branch.get("project_review_v3", {})
    if review_document.get("participant_document_sha256") != builder.QUESTIONNAIRE_SOURCE_SHA256:
        errors.append("branch specification questionnaire hash differs")
    if review_document.get("participant_document_size_bytes") != builder.QUESTIONNAIRE_SOURCE_SIZE:
        errors.append("branch specification questionnaire size differs")
    if review_document.get("classification_orientation_field") != "po_intro":
        errors.append("branch specification orientation field differs")
    if review_document.get("classification_orientation_paragraphs") != list(
        builder.CLASSIFICATION_INTRO_PARAGRAPHS
    ):
        errors.append("branch specification orientation wording differs")
    if review_document.get("classification_orientation_order") != (
        "project information -> po_intro -> po_classification_overview -> detailed judgements"
    ):
        errors.append("branch specification participant-visible order differs")
    if review_document.get("substantive_focus_rule") != {
        "plain_text": builder.SUBSTANTIVE_FOCUS_PARAGRAPH,
        "bold_phrase": builder.SUBSTANTIVE_FOCUS_PHRASE,
        "redcap_markup": f"<strong>{builder.SUBSTANTIVE_FOCUS_PHRASE}</strong>",
        "position": "inside po_intro before po_classification_overview",
    }:
        errors.append("branch specification substantive-focus rule differs")
    expected_reminders = {
        "po_miss_domain_reminder": {
            "plain_text": builder.MISSING_DOMAIN_REMINDER,
            "bold_phrase": builder.MISSING_DOMAIN_REMINDER_PHRASE,
            "branching": "[po_miss_domain] = '1'",
            "immediately_before": "po_miss_domains",
        },
        "po_miss_purpose_reminder": {
            "plain_text": builder.MISSING_PURPOSE_REMINDER,
            "bold_phrase": builder.MISSING_PURPOSE_REMINDER_PHRASE,
            "branching": "[po_miss_purpose] = '1'",
            "immediately_before": "po_miss_purposes",
        },
    }
    if review_document.get("missing_classification_reminders") != expected_reminders:
        errors.append("branch specification missing-classification reminders differ")
    if not str(review_document.get("taxonomy_reference", "")).startswith("absent;"):
        errors.append("branch specification does not make taxonomy-reference absence explicit")
    if "po_quote_permission" in builder.BRANCH_SPEC.read_text(encoding="utf-8"):
        errors.append("quotation field retained in branch specification")
    tag_spec = branch.get("tag_reviews", {})
    if tag_spec.get("operational_set") != list(builder.OPERATIONAL_TAGS):
        errors.append("branch specification operational tag set differs")
    if tag_spec.get("operational_inclusion_rule") != builder.OPERATIONAL_INCLUSION_RULE:
        errors.append("branch specification operational inclusion rule differs")
    if tag_spec.get("definitions") != builder.TAG_DEFINITIONS:
        errors.append("branch specification full tag definitions differ")
    if not tag_spec.get("lifecycle_status_is_not_operational_inclusion"):
        errors.append("branch specification conflates lifecycle and operational status")
    fixture, header = read_csv(builder.IMPORT_FIXTURE)
    if len(fixture) != 22:
        errors.append("fixture does not contain 22 rows")
    owners = [row for row in fixture if not row["redcap_repeat_instrument"]]
    repeats = [row for row in fixture if row["redcap_repeat_instrument"] == "project_review"]
    if len(owners) != 3 or len(repeats) != 19:
        errors.append("fixture owner/review structure differs")
    blank_fields = [
        *builder.CONSENT_NAMES,
        "consent_items_complete",
        "intended_recipient",
        "owner_consent",
        "ack_pref",
    ]
    for name in blank_fields:
        if name not in header or any(row[name] for row in fixture):
            errors.append(f"fixture does not keep {name} blank")
    if "po_quote_permission" in header:
        errors.append("fixture retains quotation-permission field")
    if "po_taxonomy_ref" in header:
        errors.append("fixture retains taxonomy-reference field")
    if any(row["owner_instr_ver"] != builder.VERSION for row in owners):
        errors.append("owner fixture version differs")
    if any(row["review_instr_ver"] != builder.VERSION for row in repeats):
        errors.append("review fixture version differs")
    if any(row["owner_consent_complete"] != "0" for row in owners):
        errors.append("owner fixture is imported complete/consented")
    for row in repeats:
        if any(row[name] for name in blank_fields):
            errors.append("owner-level consent value appears on repeat row")
            break
    for index, label in enumerate(builder.OPERATIONAL_TAGS, 1):
        label_field = f"prop_t{index:02d}_label"
        definition_field = f"prop_t{index:02d}_def"
        status_field = f"prop_t{index:02d}_status"
        if any(row[label_field] != label for row in repeats):
            errors.append(f"fixture {label_field} does not contain the canonical value")
        if any(row[definition_field] != builder.TAG_DEFINITIONS[label] for row in repeats):
            errors.append(f"fixture {definition_field} full definition differs")
        if any(row[status_field] not in {"0", "1"} for row in repeats):
            errors.append(f"fixture {status_field} is not populated on every review")
    for row in repeats:
        for index in range(1, builder.base.DOMAIN_SLOTS + 1):
            label = row[f"prop_d{index:02d}_label"]
            definition = row[f"prop_d{index:02d}_def"]
            if label:
                entry = builder.OWNER_DOMAIN_DISPLAY.get(label)
                if entry is None or definition != entry["full_definition"]:
                    errors.append(f"fixture proposed-Domain full definition differs: {label}")
    raw = builder.IMPORT_FIXTURE.read_text(encoding="utf-8")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(fixture)
    if buffer.getvalue() != raw:
        errors.append("fixture CSV round trip differs")
    dictionary_fields = {
        row["Variable / Field Name"] for row in load_dictionary()
    }
    if set(header) - dictionary_fields - REDCAP_STRUCTURAL_FIELDS:
        errors.append("fixture contains unknown structural/dictionary columns")
    for path in (builder.FIELD_SPEC, builder.EXPORT_SPEC, builder.FORMATTING_AUDIT):
        text = path.read_text(encoding="utf-8-sig")
        if "po_quote_permission" in text:
            errors.append(f"quotation field retained in {path.name}")
        if "po_taxonomy_ref" in text:
            errors.append(f"taxonomy-reference field retained in {path.name}")
    current_missing = next(
        row for row in load_dictionary() if row["Variable / Field Name"] == "po_miss_domains"
    )
    display = builder.OWNER_DOMAIN_DISPLAY
    if tuple(display) != builder.DOMAIN_ORDER or len(display) != 11:
        errors.append("owner-domain display mapping label set/order differs")
    taxonomy_labels = tuple(
        str(item["label"])
        for item in builder.base.taxonomy_groups()[0]["domain"]
    )
    if tuple(display) != taxonomy_labels:
        errors.append("owner-domain mapping keys differ from eligible frozen Domains")
    if builder.base.UNCLEAR_LABEL in display:
        errors.append("Unclear from Register Entry is present in owner-domain mapping")
    expected_choices = {
        str(index): str(entry["missing_choice_microdefinition"])
        for index, entry in enumerate(display.values(), 1)
    }
    if parse_choices(current_missing["Choices, Calculations, OR Slider Labels"]) != expected_choices:
        errors.append("Q6b is not generated exactly from OWNER_DOMAIN_DISPLAY")
    display_source = {
        str(item["canonical_label"]): str(item["owner_microdefinition"])
        for item in builder.base.display_source()["labels"]
        if item["owner_layer"] == "domain"
    }
    taxonomy_source = {
        str(item["label"]): item
        for item in builder.base.taxonomy_groups()[0]["domain"]
    }
    required_mapping_fields = {
        "canonical_label",
        "full_definition",
        "missing_choice_microdefinition",
        "taxonomy_source_fields",
        "boundary_summary",
        "author_approval",
    }
    for label, entry in display.items():
        if not required_mapping_fields <= set(entry):
            errors.append(f"owner-domain mapping fields incomplete: {label}")
            continue
        if entry["canonical_label"] != label:
            errors.append(f"owner-domain canonical label differs: {label}")
        if entry["full_definition"] != display_source.get(label):
            errors.append(f"owner-domain full definition differs from frozen-derived display: {label}")
        if tuple(entry["taxonomy_source_fields"]) != builder.DOMAIN_TAXONOMY_SOURCE_FIELDS:
            errors.append(f"owner-domain frozen source-field record differs: {label}")
        if any(not taxonomy_source[label].get(name) for name in entry["taxonomy_source_fields"]):
            errors.append(f"owner-domain frozen source field is empty: {label}")
        if not str(entry["missing_choice_microdefinition"]).startswith(f"{label} — "):
            errors.append(f"Q6b choice does not retain canonical label: {label}")
        if not entry["boundary_summary"] or entry["author_approval"] != "Approved, 2026-07-28":
            errors.append(f"owner-domain approval/boundary metadata differs: {label}")

    dictionary_text = builder.DICTIONARY.read_text(encoding="utf-8-sig")
    for choice in expected_choices.values():
        if dictionary_text.count(choice) != 1:
            errors.append(f"Q6b microdefinition is absent or duplicated in dictionary: {choice.split(' — ', 1)[0]}")
    updater_source = (builder.ROOT / "scripts/update_project_owner_participant_documents_candidate_0_4.py").read_text(encoding="utf-8")
    if "candidate.owner_domain_questionnaire_choices()" not in updater_source or "DOMAIN_CHOICES = (" in updater_source:
        errors.append("questionnaire updater independently maintains Q6b strings")

    field_rows, _ = read_csv(builder.FIELD_SPEC)
    field_missing = next(row for row in field_rows if row["variable"] == "po_miss_domains")
    if field_missing["notes"] != builder.owner_domain_redcap_choices():
        errors.append("field specification Q6b wording differs")
    formatting_rows, _ = read_csv(builder.FORMATTING_AUDIT)
    formatting_missing = [row for row in formatting_rows if row["variable_name"] == "po_miss_domains"]
    if len(formatting_missing) != 1 or formatting_missing[0]["body_text"] != builder.owner_domain_redcap_choices():
        errors.append("formatting audit Q6b wording differs")

    review_text = MISSING_DOMAIN_REVIEW.read_text(encoding="utf-8")
    if "approved instrument wording; implemented in candidate 0.4" not in review_text:
        errors.append("missing-domain review artefact does not record approved implementation")
    review_rows = missing_domain_review_rows()
    if len(review_rows) != 11 or tuple(row["Canonical Domain"] for row in review_rows) != builder.DOMAIN_ORDER:
        errors.append("missing-domain review does not contain the ordered 11 eligible Domains")
    for row in review_rows:
        label = row["Canonical Domain"]
        if label not in display:
            continue
        choice = str(display[label]["missing_choice_microdefinition"])
        if row["Final approved Q6b wording"] != choice:
            errors.append(f"missing-domain review approved wording differs: {label}")
        if row["Word count"] != str(len(choice.split())):
            errors.append(f"missing-domain review word count differs: {label}")
        if row["Author approval"] != "Approved, 2026-07-28":
            errors.append(f"missing-domain review approval differs: {label}")
        if row["Implementation"] != "Implemented in candidate 0.4":
            errors.append(f"missing-domain review implementation status differs: {label}")
        if not row["Boundary addressed"] or not row["Change from initial draft"]:
            errors.append(f"missing-domain review trace fields incomplete: {label}")
    if "| Unclear from Register Entry |" in review_text:
        errors.append("missing-domain review incorrectly adds Unclear from Register Entry as a choice")

    concordance = domain_concordance_rows()
    if len(concordance) != 11 or tuple(row["Canonical Domain"] for row in concordance) != builder.DOMAIN_ORDER:
        errors.append("Domain concordance does not contain the ordered 11 eligible Domains")
    for row in concordance:
        label = row["Canonical Domain"]
        if label not in display:
            continue
        entry = display[label]
        if row["Full proposed-label definition"] != entry["full_definition"]:
            errors.append(f"concordance full definition differs: {label}")
        if row["Approved Q6b wording"] != entry["missing_choice_microdefinition"]:
            errors.append(f"concordance Q6b wording differs: {label}")
        if row["Author approval"] != "Approved, 2026-07-28":
            errors.append(f"concordance author approval differs: {label}")
        if not row["Inclusion direction aligned"].startswith("Yes") or not row["Boundary direction aligned"].startswith("Yes"):
            errors.append(f"concordance human alignment decision differs: {label}")
        if not row["Live-QA result"].startswith("Pending"):
            errors.append(f"concordance live-QA result is not pending: {label}")
    live_text = builder.LIVE_CONFIG.read_text(encoding="utf-8")
    semantic_assertion = (
        "Research Domain wording concordance: For every Research Domain, compare the full "
        "definition displayed when the Domain is proposed with the compressed wording displayed "
        "in the missing-Domain checklist. Confirm that both identify the same substantive research "
        "object and apply compatible inclusion and exclusion boundaries. Neither wording may "
        "direct participants toward assigning the Domain in circumstances that the other wording excludes."
    )
    if semantic_assertion not in live_text:
        errors.append("live configuration omits exact semantic-concordance assertion")
    docs = builder.SPEC.read_text(encoding="utf-8") + builder.LIVE_CONFIG.read_text(encoding="utf-8")
    if builder.QUOTATION_POLICY not in docs:
        errors.append("point-of-use quotation policy absent")
    if builder.QUEUE_CONDITION not in docs:
        errors.append("queue condition absent from documentation")
    if errors:
        raise ValidationError("\n".join(errors))
    return {"fixture_rows": len(fixture), "owners": len(owners), "reviews": len(repeats)}


def validate_operational_tags() -> dict[str, object]:
    errors: list[str] = []
    rows = builder.operational_tag_audit()
    labels = tuple(str(row["label"]) for row in rows)
    if labels != builder.OPERATIONAL_TAGS:
        errors.append(f"owner operational tags differ: {labels!r}")
    active_only = tuple(
        str(row["label"])
        for row in rows
        if str(row.get("status", "")).lower() == "active"
    )
    if active_only == builder.OPERATIONAL_TAGS or len(active_only) != 1:
        errors.append("lifecycle active subset does not demonstrate the distinct inclusion rule")

    from analysis import llm_theme_analysis_v3 as classifier
    from dashboard import taxonomy as dashboard_taxonomy

    if tuple(classifier.CROSS_CUTTING_TAGS) != builder.OPERATIONAL_TAGS:
        errors.append("production-classifier tag set differs")
    if tuple(dashboard_taxonomy.TAG_LABELS) != builder.OPERATIONAL_TAGS:
        errors.append("dashboard tag set differs")

    dictionary = load_dictionary()
    by = {row["Variable / Field Name"]: row for row in dictionary}
    names = [row["Variable / Field Name"] for row in dictionary]
    for index, label in enumerate(builder.OPERATIONAL_TAGS, 1):
        status = f"prop_t{index:02d}_status"
        display = f"po_t{index:02d}_display"
        correct = f"po_t{index:02d}_correct"
        visibility = f"po_t{index:02d}_vis"
        if builder.TAG_FIELD_MAPPING.get(status) != label:
            errors.append(f"{status} canonical mapping differs")
        if parse_choices(by[status]["Choices, Calculations, OR Slider Labels"]) != {
            "1": "Applied",
            "0": "Not applied",
        }:
            errors.append(f"{status} choices differ")
        if by[status]["Required Field?"] != "y":
            errors.append(f"{status} is not required")
        if not (names.index(display) < names.index(status) < names.index(correct)):
            errors.append(f"{label} full definition is not immediately before its questions")
        for judgement in (correct, visibility):
            if by[judgement]["Required Field?"] != "y":
                errors.append(f"{judgement} is not required")
            if by[judgement]["Branching Logic (Show field only if...)"]:
                errors.append(f"{judgement} is not independent")
    missing = set(analytical_completion_missing({}, {
        **{name: "1" for name in builder.CONSENT_NAMES},
        "intended_recipient": "1",
        "owner_consent": "1",
        "owner_consent_complete": "2",
    }))
    for required in (
        "po_t01_correct", "po_t01_vis", "po_t02_correct", "po_t02_vis"
    ):
        if required not in missing:
            errors.append(f"analytical completion does not require {required}")
    if errors:
        raise ValidationError("\n".join(errors))
    return {
        "operational_set": list(labels),
        "inclusion_rule": builder.OPERATIONAL_INCLUSION_RULE,
        "lifecycle_active_only_subset": list(active_only),
    }


def validate_consent_logic() -> dict[str, object]:
    complete = {name: "1" for name in builder.CONSENT_NAMES}
    complete.update(
        {
            "intended_recipient": "1",
            "owner_consent": "1",
            "owner_consent_complete": "2",
        }
    )
    if not valid_owner_consent(complete):
        raise ValidationError("complete affirmative consent is not valid")
    for name in builder.CONSENT_NAMES:
        omitted = dict(complete)
        omitted[name] = ""
        if consent_items_complete(omitted) or valid_owner_consent(omitted):
            raise ValidationError(f"all-confirmed logic does not require {name}")
        cleared = dict(complete)
        cleared[name] = "0"
        if valid_owner_consent(cleared):
            raise ValidationError(f"cleared item does not invalidate consent: {name}")
    decline = {"intended_recipient": "1", "owner_consent": "0"}
    if valid_owner_consent(decline):
        raise ValidationError("active decline treated as valid affirmative consent")
    return {"affirmative": "passed", "ten_omissions": "passed", "decline": "passed"}


def check() -> dict[str, object]:
    builder.check_sources()
    return {
        "version": builder.VERSION,
        "dictionary": validate_dictionary(),
        "fixture_and_specs": validate_specs_and_fixture(),
        "operational_tags": validate_operational_tags(),
        "consent_logic": validate_consent_logic(),
        "status": "passed",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args(argv)
    try:
        print(json.dumps(check(), indent=2, sort_keys=True))
    except (ValidationError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
