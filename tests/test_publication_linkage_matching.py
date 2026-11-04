"""Rules for project-ID detection, accreditation phrases, datasets and names."""

from analysis.publication_linkage.matching import (
    build_dataset_terms,
    dataset_name_variants,
    extract_statement_snippets,
    find_dataset_mentions,
    find_names_in_text,
    find_phrases,
    find_project_id_mentions,
    name_match_level,
    normalise_doi,
    normalise_title,
    official_project_id,
    parse_person_name,
    strip_references,
)


# --- project IDs -------------------------------------------------------------

def test_project_id_with_context_word_is_detected():
    text = "Approved by the Research Accreditation Panel (DEA project number 2022/139)."
    assert [m.project_id for m in find_project_id_mentions(text)] == ["2022/139"]


def test_project_id_context_after_the_id_counts():
    text = "This work (2019/003, accredited under the DEA) used ONS data."
    assert [m.project_id for m in find_project_id_mentions(text)] == ["2019/003"]


def test_bare_year_number_pattern_is_never_a_match():
    assert find_project_id_mentions("Table 4 compares 2019/003 with earlier waves of the survey.") == []


def test_fiscal_years_paths_and_longer_numbers_are_not_ids():
    text = (
        "In project year 2019/20 and 2020/2021 the accredited project used "
        "https://example.org/2019/003/x and ref 12019/0034 under the DEA."
    )
    assert find_project_id_mentions(text) == []


def test_srs_project_wording_and_spaces_around_slash():
    text = "SRS project 2021 / 045 provided access."
    assert [m.project_id for m in find_project_id_mentions(text)] == ["2021/045"]


def test_official_project_id_drops_synthetic_record_suffix():
    assert official_project_id("2020/030/a") == "2020/030"
    assert official_project_id("2023/211") == "2023/211"


# --- accreditation phrases ------------------------------------------------------

def test_route_and_environment_phrases_are_categorised():
    text = (
        "Data were accessed in the ONS Secure Research Service under the Digital Economy Act 2017 "
        "by accredited researchers."
    )
    hits = find_phrases(text)
    keys = {h.key for h in hits}
    assert {"ons_secure_research_service", "digital_economy_act", "accredited_researcher"} <= keys
    assert {h.environment for h in hits if h.category == "environment"} == {"SRS"}


def test_phrases_are_case_and_hyphen_insensitive():
    keys = {h.key for h in find_phrases("DEA-accredited project in the secure-research-service; digital  economy act")}
    assert {"dea_accredited", "secure_research_service", "digital_economy_act"} <= keys


def test_environment_variants_map_to_codes():
    text = (
        "SAIL Databank; Secure Anonymised Information Linkage; UK Data Service SecureLab; "
        "Integrated Data Service; Scottish National Safe Haven; NISRA Research Support Unit"
    )
    codes = {h.environment for h in find_phrases(text) if h.category == "environment"}
    assert codes == {"SAIL", "UKDS", "IDS", "RDS", "NISRA"}


def test_uksa_cited_as_author_is_not_a_statement():
    assert not [h for h in find_phrases("as noted previously (UK Statistics Authority, 2019).") if h.key == "uk_statistics_authority"]
    assert [h for h in find_phrases("accredited by the UK Statistics Authority under the DEA") if h.key == "uk_statistics_authority"]


def test_references_section_is_stripped_before_matching():
    body = "Introduction\nWe study wages.\n" * 20
    text = body + "References\nDigital Economy Act 2017. legislation.gov.uk\n"
    assert "Digital Economy Act" not in strip_references(text)
    early = "References\nsee below\n" + body
    assert strip_references(early) == early  # heading in the first half is kept


def test_statement_snippets_prioritise_project_ids_and_dedupe():
    text = (
        "We thank colleagues. This work was carried out in the ONS Secure Research Service. "
        "This work was carried out in the ONS Secure Research Service. "
        "The DEA project number is 2020/123. Results follow."
    )
    snippets = extract_statement_snippets(text, max_snippets=2)
    assert snippets == [
        "This work was carried out in the ONS Secure Research Service.",
        "The DEA project number is 2020/123.",
    ]


# --- datasets ----------------------------------------------------------------------

def test_dataset_variants_split_acronyms_and_qualifiers():
    variants = dict(dataset_name_variants("Annual Survey of Hours and Earnings Longitudinal (ASHE)"))
    assert variants["ASHE"] == "acronym"
    assert variants["Annual Survey of Hours and Earnings"] == "name"


def test_census_keeps_its_year_and_generic_names_are_dropped():
    labels = {label for label, _ in dataset_name_variants("Census Wales 2011")}
    assert "Census Wales 2011" in labels and "2011 Census" in labels
    assert "Census Wales" not in labels and "Census" not in labels


def test_ambiguous_acronyms_are_not_terms():
    assert ("ABS", "acronym") not in dataset_name_variants("Annual Business Survey (ABS)")


def test_acronym_match_is_case_sensitive_and_bounded():
    terms = build_dataset_terms({"Longitudinal Education Outcomes (LEO)": ["LEO"]})
    assert find_dataset_mentions("We use LEO data.", terms)
    assert not find_dataset_mentions("Leo and leonine LEOPARD", terms)
    names = find_dataset_mentions("the longitudinal-education outcomes dataset", terms)
    assert [hit.kind for hit in names] == ["name"]


# --- names --------------------------------------------------------------------------

def test_name_formats_parse_to_the_same_person():
    for raw in ("Jack Britton", "Britton, Jack", "Britton J", "Dr Jack Britton"):
        parsed = parse_person_name(raw)
        assert parsed.family_key == "britton" and parsed.first_given.startswith("j")


def test_name_match_levels():
    assert name_match_level("Jack Britton", "Britton, Jack") == "full"
    assert name_match_level("Jack Britton", "J. Britton") == "initial"
    assert name_match_level("Jack Britton", "James Britton") is None
    assert name_match_level("Mónica Costa Dias", "Costa Dias, Monica") == "full"
    assert name_match_level("Laura van der Erve", "Erve, Laura van der") == "full"
    assert name_match_level("Ashley Akbari", "Ash Akbari") == "full"


def test_names_found_verbatim_in_body_text():
    assert find_names_in_text(["Jane Doe", "Ann Lee"], "Prepared by Jane  Doe (DfE analyst).") == ["Jane Doe"]


# --- identifiers -------------------------------------------------------------------

def test_doi_and_title_normalisation():
    assert normalise_doi("https://doi.org/10.1093/IJE/dyab149.") == "10.1093/ije/dyab149"
    assert normalise_doi("not a doi") is None
    assert normalise_title("The Returns to <i>Undergraduate</i> Degrees: Evidence!") == "the returns to undergraduate degrees evidence"


# --- register researchers ---------------------------------------------------------

def test_register_researcher_field_pairs_names_with_institutions():
    from analysis.publication_linkage.register_records import parse_researchers

    raw = (
        "Alisha Davies , Public Health Wales\nLaura Bentley,\nPublic Health Wales\n"
        "Ashley Akbari, Swansea University,\nWalid Chehtane, Social Care Wales"
    )
    pairs = [(r.name, r.institution) for r in parse_researchers(raw)]
    # Institutions come back canonicalised, with the approved acronym.
    assert ("Alisha Davies", "Public Health Wales (PHW)") in pairs
    assert ("Laura Bentley", "Public Health Wales (PHW)") in pairs
    assert ("Ashley Akbari", "Swansea University") in pairs
    assert len(pairs) == 4
    assert parse_researchers(None) == []


def test_environment_accreditation_boilerplate_is_not_a_route_statement():
    from analysis.publication_linkage.matching import statement_hits

    boilerplate = (
        "The de-identified data used in this study were made available to accredited researchers only. "
        "Applications to use data held within the SAIL Databank, an ISO 27001 and UK Statistics Authority (UKSA) "
        "Digital Economy Act (DEA) accredited Trusted Research Environment, must first be approved. "
        "We used SAIL, a Trusted Research Environment (TRE), accredited under the Digital Economy Act."
    )
    kept, dropped = statement_hits(boilerplate)
    assert not [h for h in kept if h.category == "route"]
    assert {h.key for h in dropped} >= {"accredited_researcher", "digital_economy_act"}
    assert {h.environment for h in kept} == {"SAIL"}
    real = "Use of the 2011 Census was approved by the Research Accreditation Panel under the Digital Economy Act."
    kept, dropped = statement_hits(real)
    assert {h.key for h in kept} == {"research_accreditation_panel", "digital_economy_act"} and not dropped


def test_everyday_word_product_names_are_case_sensitive():
    terms = build_dataset_terms({"MoJ Data First Family Court Data Extract": ["Data First", "Family Court (FACO)"]})
    assert find_dataset_mentions("linked through Data First", terms)
    assert not find_dataset_mentions("when the data first became available", terms)
    assert not find_dataset_mentions("the family court process", terms)
    assert find_dataset_mentions("the FACO extract", terms)


def test_en_dash_ranges_are_not_project_ids():
    assert find_project_id_mentions("a project from the University (Code number UCV/2019–2020/001).") == []
