#!/usr/bin/env python3
"""Validate owner-redcap-candidate-0.4 entirely offline."""

from __future__ import annotations

import argparse
import csv
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


def participant_doc_paragraphs() -> list[str]:
    return docx_paragraphs(builder.PARTICIPANT_SOURCE, strip_checkbox=True)


def questionnaire_doc_paragraphs() -> list[str]:
    return docx_paragraphs(builder.QUESTIONNAIRE_SOURCE)


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
    if counts != Counter({"owner_consent": 22, "project_review": 96}):
        errors.append(f"field counts differ: {dict(counts)}")
    if len(rows) != 118 or len(names) != len(set(names)):
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
        if row["Form Name"] == "project_review" and row["Variable / Field Name"] != "po_quote_permission"
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
    if "po_quote_permission" in builder.BRANCH_SPEC.read_text(encoding="utf-8"):
        errors.append("quotation field retained in branch specification")
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
    docs = builder.SPEC.read_text(encoding="utf-8") + builder.LIVE_CONFIG.read_text(encoding="utf-8")
    if "exact proposed wording and context" not in docs:
        errors.append("point-of-use quotation policy absent")
    if builder.QUEUE_CONDITION not in docs:
        errors.append("queue condition absent from documentation")
    if errors:
        raise ValidationError("\n".join(errors))
    return {"fixture_rows": len(fixture), "owners": len(owners), "reviews": len(repeats)}


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
