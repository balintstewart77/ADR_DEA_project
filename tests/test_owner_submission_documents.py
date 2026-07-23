from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
MATERIALS = ROOT / "preregistration/package/06_redcap/participant_materials"
PROTOCOL_DIR = ROOT / "preregistration/package/00_protocol"
PIS = MATERIALS / "Project_Owner_Participant_Information_and_Consent_v2.docx"
QUESTIONNAIRE = MATERIALS / "Project_Owner_Review_Questionnaire_v3.docx"
ARCHIVED_QUESTIONNAIRE = MATERIALS / "Project_Owner_Review_Questionnaire_v2.docx"
PROTOCOL = PROTOCOL_DIR / "Validation_Protocol_PreReg_v0.17.docx"
ARCHIVED_PROTOCOL = PROTOCOL_DIR / "Validation_Protocol_PreReg_v0.16.docx"
INVITATION = MATERIALS / "project_owner_invitation_email_draft.docx"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

OBSOLETE = (
    "after expressing interest",
    "separate short review links",
    "separate review links",
    "project-specific review links",
    "links will be released",
    "before links are released",
    "receive links",
    "one link per project",
    "separate link provided for that project",
    "each owner-project assignment is a separate redcap record",
    "one record per owner-project assignment",
    "consent repeated for each project",
)


def docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    return "\n".join(
        "".join(node.text or "" for node in paragraph.iter(W + "t"))
        for paragraph in root.iter(W + "p")
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()



def test_archived_predecessor_hashes_are_preserved() -> None:
    assert sha256(ARCHIVED_QUESTIONNAIRE) == "cad14d0d355d6487c93a86cfb4cc9642d4e46bf16bdf66c5d07c5cd89b698f80"
    assert sha256(ARCHIVED_PROTOCOL) == "616591553a571f9e084f42a21cc701a30b57966c904759ed9c633a057ef7c9a5"

def test_participant_information_v2_matches_owner_queue_workflow() -> None:
    text = docx_text(PIS)
    assert "Version 2 | 23 July 2026" in text
    assert "UCL ethics application: Project ID 5004" in text
    assert "Dr Balint Stewart and Dr Joseph Lam" in text
    assert "You will receive one personalised link" in text
    assert "Participant Information and Consent survey" in text
    assert "all, some or none of the projects, in any order" in text
    assert "Save & Return Later" in text
    assert "return through the same personalised link" in text
    assert "Please do not forward the link" in text
    assert "requested separately for each project response" in text
    assert "requested once per researcher" in text
    assert "separate restricted recruitment/contact table" in text
    assert "neutral Review reference" in text
    assert (
        "I confirm that I am the researcher to whom this personalised link was sent."
        in text
    )
    assert (
        "I confirm that I have read and understood the Participant Information "
        "Sheet provided with this survey, have had the opportunity to ask questions, "
        "and agree to take part in the Project Owner Review."
        in text
    )
    assert "Yes, I agree to take part" in text
    assert "No, I do not wish to take part" in text
    assert "before analysis begins" in text
    assert "[withdrawal date TBC]" not in text


def test_questionnaire_v3_matches_candidate_0_3_content_and_logic() -> None:
    text = docx_text(QUESTIONNAIRE)
    assert "Project Owner Review Questionnaire v3" in text
    assert "23 July 2026" in text
    assert "one personalised Survey Queue link" in text
    assert "Participant Information and Consent are completed once" in text
    assert "all, some or none, in any order" in text
    assert "Save & Return Later" in text
    assert "Read-only classification overview" in text
    assert "Several Domains may apply and they are not ranked" in text
    assert "More than one may apply, with a maximum of two" in text
    assert "Either, both or neither may apply" in text
    assert "Clearly visible / Partly visible / Not visible / Unsure" in text
    assert (
        "Please briefly explain why this proposed Research Domain does not fit the "
        "actual project."
        in text
    )
    assert (
        "Optional: Please briefly explain what is only partly visible, not visible or unclear"
        in text
    )
    assert (
        "Please briefly explain why this proposed Analytical Purpose does not fit the "
        "actual project."
        in text
    )
    assert (
        "An Unsure response shows no explanation field."
        in text
    )
    assert text.count("Q4d. Optional:") == 1
    assert text.count("Q5d. Optional:") == 1
    assert text.count("Optional: Please briefly explain the taxonomy-fit problem") == 1
    assert "If you selected 'Other taxonomy problem', describe it here" in text
    assert "Would you like to be acknowledged by name" not in text
    assert "Preferred name for acknowledgement" not in text
    assert "Preferred affiliation for acknowledgement" not in text
    assert "Please return to your personalised project list to review another project or to finish." in text
    assert (
        "You may request withdrawal of this submitted review before the deadline stated in the "
        "Participant Information Sheet by contacting the study team and quoting the Review reference "
        "shown above."
        in text
    )
    assert "[withdrawal date TBC]" not in text
    assert "[study email]" not in text
    assert "balint.stewart@ucl.ac.uk" in text
    assert "Unclear from Register Entry" not in text.split("Q6b.", 1)[1].split("Q6c.", 1)[0]
    assert "Unclear from Register Entry" not in text.split("Q7b.", 1)[1].split("Q7c.", 1)[0]
    assert "Appendix B. REDCap analytical-completion rule" in text
    assert "Do not provide confidential or non-public information." not in text
    assert text.count("Is the basis for this tag status visible in the public project title and datasets listed above?") == 2
    assert "Could the correct status for this tag reasonably be determined" not in text
    assert "No suitable category exists in the framework" in text
    assert "Visibility explanations, missing-label explanations" in text



def test_protocol_v0_17_aligns_owner_architecture_and_requiredness() -> None:
    text = docx_text(PROTOCOL)
    paragraphs = [" ".join(paragraph.split()) for paragraph in text.splitlines()]

    def scoped_paragraph(*anchors: str) -> str:
        matches = [
            paragraph.casefold()
            for paragraph in paragraphs
            if all(anchor.casefold() in paragraph.casefold() for anchor in anchors)
        ]
        assert len(matches) == 1, (anchors, matches)
        return matches[0]

    # Controlled version/status header: exact wording is intentional.
    assert (
        "Review candidate v0.17 | prepared 23 July 2026 | not frozen, registered "
        "or authorised for formal sampling, assignment import or coding"
        in text
    )

    access = scoped_paragraph("pseudonymous owner record", "Survey Queue")
    assert "non-repeating participant information and consent" in access
    assert "pre-created repeating project review instances" in access
    assert "private personalised survey queue link" in access
    assert all(option in access for option in ("all", "some", "none"))
    # REDCap feature name is controlled wording.
    assert "save & return later" in access
    assert "same personalised link" in access
    assert "cannot create additional review instances" in access

    data_model = scoped_paragraph("pseudonymous owner_id", "long format")
    assert "assignment_id" in data_model and "neutral" in data_model
    assert "owner-level row" in data_model and "repeating review rows" in data_model
    assert "owner-level consent" in data_model
    assert "joined" in data_model and "owner_id" in data_model

    instrument = scoped_paragraph("owners separately judge", "taxonomy gap")
    assert all(layer in instrument for layer in ("domain", "purpose", "tag statuses"))
    assert "unranked" in instrument
    assert "multi-label" in instrument or "multiple labels" in instrument
    assert ("at most two" in instrument or "no more than two" in instrument)
    assert "purpose" in instrument
    assert "not a register-wide accuracy estimate" in instrument
    assert "gold standard" in instrument
    assert "unsure" in instrument and "no explanation" in instrument
    assert "optional" in instrument and "do not determine analytical completeness" in instrument
    # Controlled participant-facing taxonomy label: exact wording is intentional.
    assert "no suitable category exists in the framework" in instrument

    withdrawal = scoped_paragraph("deadline for withdrawal", "restricted recruitment/contact table")
    # Participant withdrawal commitment: exact timing phrase is intentional.
    assert "before analysis begins" in withdrawal
    assert "deadline for withdrawal before analysis lock" not in withdrawal


def test_protocol_v0_17_preserves_sampling_exclusions_seeds_and_decision_rules() -> None:
    old = docx_text(PROTOCOL_DIR / "Validation_Protocol_PreReg_v0.15.docx")
    new = docx_text(PROTOCOL)
    unchanged_passages = (
        "1,308 retained register record-units representing 1,304 unique official Project IDs",
        "The frozen exclusion set contains 22 unique Record IDs",
        "Target size: 150 records",
        "Target size: 75 records",
        "25 Research Domain-only, 25 Analytical Purpose-only, and 25 both-dimension disagreements",
        "Target size: 100 random-baseline reserve records and 50 hard-case reserve records",
        "SEED_DRAW = 20260713",
        "SEED_SHUFFLE_C01 = 101",
        "SEED_SHUFFLE_C02 = 102",
        "SEED_SHUFFLE_C03 = 103",
        "SEED_BOOTSTRAP = 20260714",
        "SEED_ADJUDICATION_AUDIT = 20260715",
        "2,000 nonparametric record-level bootstrap resamples",
        "Hyndman–Fan Type 7 interpolation",
        "will be blind to the production-model and comparison-model outputs",
        "unused reserve identities remain embargoed while eligible for a clean retest",
    )
    for passage in unchanged_passages:
        assert passage in old
        assert passage in new


def test_submission_copies_have_no_obsolete_link_wording_or_word_review_markup() -> None:
    for path in (PIS, QUESTIONNAIRE, PROTOCOL):
        text = docx_text(path).lower()
        assert not [phrase for phrase in OBSOLETE if phrase in text], path.name
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            document_xml = archive.read("word/document.xml")
        assert "word/comments.xml" not in names
        root = ET.fromstring(document_xml)
        assert not list(root.iter(W + "ins"))
        assert not list(root.iter(W + "del"))


def test_invitation_email_is_preserved_byte_for_byte() -> None:
    assert sha256(INVITATION) == (
        "971f71246c3483476306fc2b535fea0e43c31a1a5a922b63b1bb6b99d2e5527b"
    )
    invitation_text = docx_text(INVITATION).lower()
    assert not [phrase for phrase in OBSOLETE if phrase in invitation_text]