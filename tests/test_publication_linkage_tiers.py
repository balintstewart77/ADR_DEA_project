"""De-duplication, output typing and tier assignment."""

from datetime import date

import pandas as pd

from analysis.publication_linkage.adjudication import apply_decisions, quote_verified, write_queue
from analysis.publication_linkage.outputs import CandidateOutput, classify_output_type, dedupe_outputs
from analysis.publication_linkage.pipeline import link_outputs, links_table
from analysis.publication_linkage.register_records import ProjectRecord, Researcher, sector_group
from analysis.publication_linkage.tiers import Evidence, add_months, assign_tier, collect_evidence, in_window

SNAPSHOT = date(2026, 10, 21)


def project(**overrides) -> ProjectRecord:
    values = dict(
        record_id="2021/050",
        project_id="2021/050",
        title="Earnings returns to degrees by subject",
        accreditation_date=date(2021, 6, 1),
        environment="ONS Secure Research Service (SRS)",
        environment_code="SRS",
        researchers=[Researcher("Jack Britton", "Institute for Fiscal Studies"), Researcher("Ann Lee", "UCL")],
        datasets=["Longitudinal Education Outcomes (LEO)"],
        providers=["DfE, DWP and HMRC"],
        linked_products=["Longitudinal Education Outcomes (LEO)"],
        record_linkage="Cross-domain record linkage",
        component_domains="Education & Skills; Labour Market & Employment",
        researcher_sectors="academic",
        dataset_spellings={"Longitudinal Education Outcomes (LEO)": ["LEO", "Longitudinal Education Outcomes (LEO)"]},
    )
    values.update(overrides)
    return ProjectRecord(**values)


def output(**overrides) -> CandidateOutput:
    values = dict(
        source="core",
        source_id="1",
        title="Graduate earnings by subject",
        publication_date="2022-05-01",
        authors=["Britton, Jack", "Someone Else"],
        abstract="We use Longitudinal Education Outcomes data.",
        full_text="Body. This work was produced in the ONS Secure Research Service under the Digital Economy Act.",
    )
    values.update(overrides)
    return CandidateOutput(**values)


def decide(proj, out):
    group = dedupe_outputs([out])[0]
    return assign_tier(collect_evidence(proj, group, SNAPSHOT))


# --- de-duplication --------------------------------------------------------------

def test_dedupe_by_doi_then_title_and_year():
    a = output(source="openalex", source_id="W1", doi="10.1/abc", title="Graduate earnings by subject", publication_date="2022")
    b = output(source="core", source_id="9", doi="https://doi.org/10.1/ABC", title="Different title", publication_date="2022")
    c = output(source="europepmc", source_id="MED:1", doi=None, title="Graduate Earnings by Subject!", publication_date="2022-01-02")
    d = output(source="core", source_id="10", doi=None, title="Graduate earnings by subject", publication_date="2019")
    groups = dedupe_outputs([a, b, c, d])
    sizes = sorted(len(g.members) for g in groups)
    assert sizes == [1, 3]
    merged = next(g for g in groups if len(g.members) == 3)
    assert merged.output_key == "doi:10.1/abc"
    assert merged.sources == ["core", "europepmc", "openalex"]


def test_short_titles_without_doi_do_not_merge():
    a = output(source_id="1", title="Introduction", doi=None)
    b = output(source_id="2", title="Introduction", doi=None)
    assert len(dedupe_outputs([a, b])) == 2


def test_output_types():
    assert classify_output_type("openalex", "article", "Journal of Labour Economics") == "journal article"
    assert classify_output_type("openalex", "preprint", None) == "preprint"
    assert classify_output_type("core", "research article", "SSRN Electronic Journal") == "preprint"
    assert classify_output_type("core", None, "IFS Working Papers") == "working paper"
    assert classify_output_type("core", "thesis", None) == "thesis"
    assert classify_output_type("govuk", "research", None) == "report"
    assert classify_output_type("europepmc", "preprint", None, doi="10.1101/2021.01.01") == "preprint"


def test_group_type_prefers_journal_version():
    wp = output(source="core", source_id="1", doi="10.1/x", venue="IFS Working Papers", type_raw=None)
    art = output(source="openalex", source_id="W", doi="10.1/x", venue="Labour Economics", type_raw="article")
    assert dedupe_outputs([wp, art])[0].output_type == "journal article"


# --- windows -----------------------------------------------------------------------

def test_window_runs_from_six_months_before_accreditation_to_snapshot():
    proj = project()
    assert add_months(date(2021, 6, 1), -6) == date(2020, 12, 1)
    assert in_window("2020-12-01", proj, SNAPSHOT) is True
    assert in_window("2020-11-30", proj, SNAPSHOT) is False
    assert in_window("2020", proj, SNAPSHOT) is True  # year overlaps the window
    assert in_window("2027-01-01", proj, SNAPSHOT) is False
    assert in_window(None, proj, SNAPSHOT) is None


# --- tiers -------------------------------------------------------------------------

def test_tier1_needs_quoted_id_plus_author_or_dataset():
    quoted = "Accessed under DEA project 2021/050 in the SRS."
    assert decide(project(), output(full_text=quoted)).tier == 1
    stranger = output(full_text=quoted, authors=["Nobody Here"], abstract="Unrelated topic.", title="Unrelated")
    decision = decide(project(), stranger)
    assert decision.tier is None and decision.needs_adjudication


def test_tier1_ignores_a_different_projects_id():
    assert decide(project(), output(full_text="DEA project 2021/051 in the SRS.")).tier == 3


def test_tier2_statement_author_dataset_date():
    decision = decide(project(), output())
    assert decision.tier == 2 and not decision.needs_adjudication


def test_tier2_requires_date_in_window():
    assert decide(project(), output(publication_date="2019-01-01")).tier is None


def test_environment_must_match_the_projects_environment():
    sail_text = "Body. Data were held in the SAIL Databank."
    decision = decide(project(), output(full_text=sail_text))
    assert decision.tier == 3 and "other_environment_named" in decision.reasons
    sail_project = project(environment="SAIL Databank", environment_code="SAIL")
    assert decide(sail_project, output(full_text=sail_text)).tier == 2


def test_tier3_without_statement_and_settled_when_unambiguous():
    decision = decide(project(), output(full_text="Body without any statement."))
    assert decision.tier == 3 and not decision.needs_adjudication


def test_initial_only_author_and_acronym_only_dataset_go_to_adjudication():
    weak = output(authors=["J. Britton"], abstract="We use LEO.", title="Graduate pay")
    decision = decide(project(), weak)
    assert decision.tier == 2 and decision.needs_adjudication
    assert {"author_initial_only", "dataset_acronym_only"} <= set(decision.reasons)


def test_strong_statement_without_dataset_is_a_near_miss():
    no_dataset = output(abstract="We study graduates.", full_text="Analysed in the ONS Secure Research Service.")
    decision = decide(project(), no_dataset)
    assert decision.tier is None and decision.needs_adjudication
    sail_only = output(abstract="We study graduates.", full_text="Analysed in the SAIL Databank.")
    sail_project = project(environment="SAIL Databank", environment_code="SAIL")
    assert decide(sail_project, sail_only) == assign_tier(Evidence())


def test_no_author_no_link():
    stranger = output(authors=["Nobody Here"])
    assert decide(project(), stranger).tier is None


def test_report_without_author_metadata_uses_names_in_body():
    report = output(source="govuk", authors=[], full_text="Authors: Ann Lee. Secure Research Service analysis of LEO data.")
    assert decide(project(), report).tier == 2


def test_one_output_links_to_several_projects():
    first = project()
    second = project(record_id="2022/010", project_id="2022/010", accreditation_date=date(2022, 1, 5))
    rows = link_outputs(dedupe_outputs([output()]), [first, second], SNAPSHOT)
    assert sorted(row.project.record_id for row in rows) == ["2021/050", "2022/010"]


def test_sector_groups():
    assert sector_group("academic") == "academic"
    assert sector_group("academic; government") == "government"
    assert sector_group("academic; third-sector") == "third-sector"
    assert sector_group("") == "unclassified"


# --- adjudication --------------------------------------------------------------

def test_quote_verification_is_verbatim_modulo_whitespace():
    source = "Graduate pay\nWe use the LEO   data in the ONS Secure Research Service."
    assert quote_verified("use the LEO data in the ONS", source)
    assert not quote_verified("uses the LEO data", source)
    assert not quote_verified("LEO", source)  # too short to be evidence


def test_apply_decisions_verifies_quotes_and_caps_tiers(tmp_path):
    weak = output(authors=["J. Britton"], abstract="We use LEO.", title="Graduate pay")
    rows = link_outputs(dedupe_outputs([weak]), [project()], SNAPSHOT)
    write_queue(rows, tmp_path)
    links = links_table(rows)
    item_id = f"2021/050|{rows[0].group.output_key}"
    decision_path = tmp_path / "adjudication" / "batch_001.decisions.jsonl"

    decision_path.write_text(
        '{"item_id": "%s", "match": true, "tier": 2, "reason": "ok", "evidence_quote": "We use LEO."}\n' % item_id
    )
    adjudicated, counts = apply_decisions(links, tmp_path)
    assert counts["verified"] == 1 and adjudicated.loc[0, "final_tier"] == 2

    decision_path.write_text(
        '{"item_id": "%s", "match": true, "tier": 2, "reason": "ok", "evidence_quote": "a sentence not shown"}\n' % item_id
    )
    adjudicated, counts = apply_decisions(links, tmp_path)
    assert counts["unverified"] == 1
    assert adjudicated.loc[0, "adjudication_status"] == "quote_not_verified"
    assert adjudicated.loc[0, "final_tier"] == 2  # rule tier stands

    decision_path.write_text(
        '{"item_id": "%s", "match": false, "tier": null, "reason": "different topic", "evidence_quote": "We use LEO."}\n' % item_id
    )
    adjudicated, _ = apply_decisions(links, tmp_path)
    assert adjudicated.loc[0, "final_tier"] == ""


def test_adjudicated_tier2_capped_without_statement(tmp_path):
    near = output(authors=["J. Britton"], abstract="We use LEO.", title="Graduate pay", full_text="No statement.")
    rows = link_outputs(dedupe_outputs([near]), [project()], SNAPSHOT)
    write_queue(rows, tmp_path)
    links = links_table(rows)
    item_id = f"2021/050|{rows[0].group.output_key}"
    (tmp_path / "adjudication" / "batch_001.decisions.jsonl").write_text(
        '{"item_id": "%s", "match": true, "tier": 2, "reason": "x", "evidence_quote": "We use LEO."}\n' % item_id
    )
    adjudicated, counts = apply_decisions(links, tmp_path)
    assert adjudicated.loc[0, "final_tier"] == 3 and counts["capped_to_tier3"] == 1
    assert isinstance(adjudicated, pd.DataFrame)
