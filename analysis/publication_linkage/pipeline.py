"""Run sources over a set of projects and build the linkage tables."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from analysis.publication_linkage import config
from analysis.publication_linkage.http_client import BudgetExhausted, QueryRejected, SourceBlocked  # noqa: F401
from analysis.publication_linkage.matching import find_project_id_mentions, parse_person_name
from analysis.publication_linkage.outputs import CandidateOutput, OutputGroup, dedupe_outputs
from analysis.publication_linkage.register_records import ProjectRecord, sector_group
from analysis.publication_linkage.tiers import Evidence, assign_tier, best_evidence_quote, collect_evidence

ALL_SOURCES = ("openalex", "core", "europepmc", "gtr", "govuk")
ENRICHERS = ("semanticscholar",)


def make_source(name: str, *, offline: bool = False, cache_dir: Path = config.CACHE_DIR):
    if name == "openalex":
        from analysis.publication_linkage.sources.openalex import OpenAlexSource
        return OpenAlexSource(offline=offline, cache_dir=cache_dir)
    if name == "core":
        from analysis.publication_linkage.sources.core import CoreSource
        return CoreSource(offline=offline, cache_dir=cache_dir)
    if name == "europepmc":
        from analysis.publication_linkage.sources.europepmc import EuropePmcSource
        return EuropePmcSource(offline=offline, cache_dir=cache_dir)
    if name == "gtr":
        from analysis.publication_linkage.sources.gtr import GtrSource
        return GtrSource(offline=offline, cache_dir=cache_dir)
    if name == "govuk":
        from analysis.publication_linkage.sources.govuk import GovUkSource
        return GovUkSource(offline=offline, cache_dir=cache_dir)
    if name == "semanticscholar":
        from analysis.publication_linkage.sources.semanticscholar import SemanticScholarEnricher
        return SemanticScholarEnricher(offline=offline, cache_dir=cache_dir)
    raise ValueError(f"unknown source {name}")


@dataclass
class SourceRun:
    name: str
    status: str = "not_run"  # ok | blocked | budget_stopped | failed | partial
    candidates: int = 0
    stats: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    seconds: float = 0.0


@dataclass
class LinkRow:
    project: ProjectRecord
    group: OutputGroup
    evidence: Evidence
    tier: int | None
    needs_adjudication: bool
    reasons: tuple[str, ...]


def run_sources(
    projects: list[ProjectRecord],
    snapshot_date: date,
    sources: tuple[str, ...],
    *,
    offline: bool = False,
    cache_dir: Path = config.CACHE_DIR,
    log=print,
) -> tuple[list[CandidateOutput], dict[str, SourceRun], dict]:
    candidates: list[CandidateOutput] = []
    runs: dict[str, SourceRun] = {}
    extras: dict = {}
    for name in sources:
        run = SourceRun(name)
        started = time.monotonic()
        source = make_source(name, offline=offline, cache_dir=cache_dir)
        try:
            found = source.collect(projects, snapshot_date)
            run.status = "budget_stopped" if any("stopped for the day" in n for n in source.notes) else "ok"
        except SourceBlocked as error:
            found, run.status = [], "blocked"
            run.notes.append(str(error))
        except BudgetExhausted as error:
            found, run.status = [], "budget_stopped"
            run.notes.append(str(error))
        except Exception as error:  # noqa: BLE001 - a failing source is logged, the others continue
            found, run.status = [], "failed"
            run.notes.append(f"{type(error).__name__}: {config.redact(str(error))[:300]}")
        run.candidates = len(found)
        run.stats = source.client.stats.as_dict()
        run.notes.extend(source.notes)
        run.seconds = round(time.monotonic() - started, 1)
        runs[name] = run
        candidates.extend(found)
        for attribute in ("author_resolution", "grant_links"):
            if getattr(source, attribute, None):
                extras.setdefault(attribute, []).extend(getattr(source, attribute))
        log(f"[{name}] {run.status}: {run.candidates} candidates, {run.stats.get('live_calls')} live / "
            f"{run.stats.get('cached_calls')} cached calls, {run.seconds}s")
    return candidates, runs, extras


def complete_full_texts(
    groups: list[OutputGroup],
    projects: list[ProjectRecord],
    snapshot_date: date,
    *,
    offline: bool,
    cache_dir: Path,
    log=print,
) -> tuple[list[CandidateOutput], dict]:
    """Fetch full text for outputs whose evidence a search index reported but
    we cannot quote: OpenAlex/Europe PMC said a project ID matched, or
    OpenAlex said an accreditation phrase matched an author-matched output.
    CORE is asked by DOI first, then Europe PMC open-access full text.
    OpenAlex PDFs are never downloaded."""
    from analysis.publication_linkage.sources.core import CoreSource
    from analysis.publication_linkage.sources.europepmc import EuropePmcSource

    family_index = build_family_index(projects)
    by_project_id: dict[str, list[ProjectRecord]] = {}
    for project in projects:
        by_project_id.setdefault(project.project_id, []).append(project)
    wanted = []
    for group in groups:
        if not group.doi or any(m.full_text for m in group.members):
            continue
        want = False
        # Index-reported project ID: worth text only if the rules already see
        # an author or dataset of that project (Tier 1 needs one of them).
        for project_id in group.index_project_id_hits():
            for project in by_project_id.get(project_id, []):
                evidence = collect_evidence(project, group, snapshot_date)
                want = want or evidence.has_author or evidence.has_dataset
        # Index-reported phrase: worth text if a register researcher on a
        # candidate project is an author and the date is in that window.
        if not want and group.index_phrase_hits():
            for project in candidate_projects(group, family_index, {}):
                evidence = collect_evidence(project, group, snapshot_date)
                if evidence.has_author and evidence.date_in_window is not False:
                    want = True
                    break
        if want:
            wanted.append(group.doi)
    added: list[CandidateOutput] = []
    stats = {"wanted": len(wanted), "core": 0, "europepmc": 0, "not_found": 0, "blocked": []}
    if not wanted:
        return added, stats
    core = CoreSource(offline=offline, cache_dir=cache_dir)
    epmc = EuropePmcSource(offline=offline, cache_dir=cache_dir)
    for doi in wanted:
        found = None
        for name, source in (("core", core), ("europepmc", epmc)):
            if name in stats["blocked"]:
                continue
            try:
                candidate = source.fetch_by_doi(doi)
            except SourceBlocked:
                stats["blocked"].append(name)
                continue
            if candidate and candidate.full_text:
                found = candidate
                stats[name] += 1
                break
        if found:
            added.append(found)
        else:
            stats["not_found"] += 1
    stats["core_calls"] = core.client.stats.live_calls
    stats["europepmc_calls"] = epmc.client.stats.live_calls
    log(f"[full-text completion] {len(added)} of {len(wanted)} DOIs found with full text "
        f"(CORE {stats['core']}, Europe PMC {stats['europepmc']})")
    return added, stats


def enrich(groups: list[OutputGroup], *, offline: bool, cache_dir: Path, log=print) -> tuple[list[CandidateOutput], SourceRun]:
    run = SourceRun("semanticscholar")
    enricher = make_source("semanticscholar", offline=offline, cache_dir=cache_dir)
    added: list[CandidateOutput] = []
    try:
        added = enricher.enrich(groups)
        run.status = "ok"
    except SourceBlocked as error:
        run.status = "blocked"
        run.notes.append(str(error))
    except (QueryRejected, RuntimeError, OSError) as error:
        run.status = "failed"
        run.notes.append(f"{type(error).__name__}: {config.redact(str(error))[:300]}")
    run.candidates = len(added)
    run.stats = enricher.client.stats.as_dict()
    log(f"[semanticscholar] {run.status}: {len(added)} enrichment records")
    return added, run


def build_family_index(projects: list[ProjectRecord]) -> dict[str, list[ProjectRecord]]:
    index: dict[str, list[ProjectRecord]] = {}
    for project in projects:
        for researcher in project.researchers:
            parsed = parse_person_name(researcher.name)
            if parsed:
                index.setdefault(parsed.family_key, []).append(project)
    return index


def candidate_projects(
    group: OutputGroup,
    family_index: dict[str, list[ProjectRecord]],
    by_project_id: dict[str, list[ProjectRecord]],
) -> list[ProjectRecord]:
    """Projects that could link: a shared author family name, a quoted
    project ID, or (for author-less reports) every project, filtered later."""
    found: dict[str, ProjectRecord] = {}
    authors = group.authors()
    for author in authors:
        parsed = parse_person_name(author)
        if parsed:
            for project in family_index.get(parsed.family_key, []):
                found[project.record_id] = project
    if by_project_id:
        quoted = [mention.project_id for mention in find_project_id_mentions(group.statement_text())]
        for project_id in [*quoted, *group.index_project_id_hits()]:
            for project in by_project_id.get(project_id, []):
                found[project.record_id] = project
    if not authors:
        text = group.matching_text().casefold()
        for family, projects in family_index.items():
            if len(family) > 3 and family in text:
                for project in projects:
                    found[project.record_id] = project
    return list(found.values())


def link_outputs(groups: list[OutputGroup], projects: list[ProjectRecord], snapshot_date: date) -> list[LinkRow]:
    family_index = build_family_index(projects)
    by_project_id: dict[str, list[ProjectRecord]] = {}
    for project in projects:
        by_project_id.setdefault(project.project_id, []).append(project)
    rows: list[LinkRow] = []
    for group in groups:
        for project in candidate_projects(group, family_index, by_project_id):
            evidence = collect_evidence(project, group, snapshot_date)
            decision = assign_tier(evidence)
            if decision.tier is not None or decision.needs_adjudication or decision.reasons:
                rows.append(LinkRow(project, group, evidence, decision.tier, decision.needs_adjudication, decision.reasons))
    return rows


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def evidence_quote(row: LinkRow) -> str:
    return best_evidence_quote(row.project, row.group, row.evidence)


def outputs_table(groups: list[OutputGroup]) -> pd.DataFrame:
    records = []
    for group in groups:
        primary = group.primary
        by_source = {}
        for member in group.members:
            by_source.setdefault(member.source, []).append(member.source_id)
        records.append({
            "output_key": group.output_key,
            "doi": group.doi or "",
            "title": primary.title,
            "year": group.year,
            "publication_date": group.publication_date or "",
            "output_type": group.output_type,
            "authors": "; ".join(group.authors()),
            "venue": primary.venue or "",
            "url": primary.url or "",
            "sources": "; ".join(group.sources),
            "openalex_ids": "; ".join(by_source.get("openalex", [])),
            "core_ids": "; ".join(by_source.get("core", [])),
            "europepmc_ids": "; ".join(by_source.get("europepmc", [])),
            "gtr_ids": "; ".join(by_source.get("gtr", [])),
            "govuk_paths": "; ".join(by_source.get("govuk", [])),
            "semanticscholar_ids": "; ".join(by_source.get("semanticscholar", [])),
            "has_full_text": any(bool(m.full_text) for m in group.members),
            "evidence_snippet": " | ".join(group.snippets()[:3]),
        })
    return pd.DataFrame(records)


def links_table(rows: list[LinkRow]) -> pd.DataFrame:
    records = []
    for row in rows:
        ev = row.evidence
        records.append({
            "Record ID": row.project.record_id,
            "Project ID": row.project.project_id,
            "output_key": row.group.output_key,
            "rule_tier": row.tier if row.tier is not None else "",
            "needs_adjudication": row.needs_adjudication,
            "rule_reasons": "; ".join(row.reasons),
            "evidence_quote": evidence_quote(row),
            "sources": "; ".join(row.group.sources),
            "project_id_quoted": bool(ev.project_id_mentions),
            "author_matches": "; ".join(f"{a} = {b} ({lvl})" for a, b, lvl in ev.author_matches),
            "authors_named_in_text": "; ".join(ev.authors_named_in_text),
            "datasets_named": "; ".join(sorted({f"{d} [{label}]" for d, label, _ in ev.dataset_hits})),
            "statement_type": ev.statement_type,
            "route_phrases": "; ".join(ev.route_phrases),
            "environment_phrases": "; ".join(ev.environment_phrases),
            "environment_consistent": ev.environment_consistent,
            "supporting_phrases": "; ".join(ev.supporting_phrases),
            "boilerplate_phrases": "; ".join(ev.boilerplate_phrases),
            "index_phrase_hits": "; ".join(ev.index_phrase_hits),
            "publication_date": ev.publication_date or "",
            "date_in_window": ev.date_in_window,
            "adjudication_status": "pending" if row.needs_adjudication else "not_needed",
            "adjudication_match": "",
            "adjudication_tier": "",
            "adjudication_reason": "",
            "adjudication_quote": "",
            "adjudication_quote_verified": "",
            "final_tier": row.tier if (row.tier is not None) else "",
            "reviewer_decision": "",
        })
    columns = [
        "Record ID", "Project ID", "output_key", "rule_tier", "needs_adjudication", "rule_reasons", "evidence_quote",
        "sources", "project_id_quoted", "author_matches", "authors_named_in_text", "datasets_named", "statement_type", "route_phrases",
        "environment_phrases", "environment_consistent", "supporting_phrases", "boilerplate_phrases", "index_phrase_hits",
        "publication_date", "date_in_window", "adjudication_status", "adjudication_match", "adjudication_tier",
        "adjudication_reason", "adjudication_quote", "adjudication_quote_verified", "final_tier", "reviewer_decision",
    ]
    return pd.DataFrame(records, columns=columns)


def _months_between(start: date, end: date) -> float:
    return round((end - start).days / 30.4375, 1)


def project_summary_table(
    projects: list[ProjectRecord],
    links: pd.DataFrame,
    outputs: pd.DataFrame,
    snapshot_date: date,
    mature_cutoff: date,
) -> pd.DataFrame:
    dates = dict(zip(outputs["output_key"], outputs["publication_date"])) if len(outputs) else {}
    records = []
    for project in projects:
        project_links = links[links["Record ID"] == project.record_id] if len(links) else links
        tiers = pd.to_numeric(project_links["final_tier"], errors="coerce") if len(project_links) else pd.Series(dtype=float)
        headline = project_links[tiers.isin([1, 2])] if len(project_links) else project_links
        route = (
            (tiers == 1) | ((tiers == 2) & project_links["statement_type"].astype(str).str.contains("route"))
            if len(project_links) else pd.Series(dtype=bool)
        )
        index_id_only = (
            project_links["rule_reasons"].astype(str).str.contains("project_id_reported_by_index_without_text")
            & tiers.isna()
            if len(project_links) else pd.Series(dtype=bool)
        )
        first_date = ""
        lag = None
        if len(headline):
            output_dates = sorted(str(dates.get(key, "")) for key in headline["output_key"] if dates.get(key))
            if output_dates:
                first_date = output_dates[0]
                first = date.fromisoformat(first_date[:10]) if len(first_date) >= 10 else date(int(first_date[:4]), 7, 1)
                lag = _months_between(project.accreditation_date, first)
        records.append({
            "Record ID": project.record_id,
            "Project ID": project.project_id,
            "accreditation_date": project.accreditation_date.isoformat(),
            "accreditation_year": project.accreditation_date.year,
            "mature_cohort": project.accreditation_date <= mature_cutoff,
            "environment": project.environment,
            "record_linkage": project.record_linkage,
            "researcher_sectors": project.researcher_sectors,
            "sector_group": sector_group(project.researcher_sectors),
            "has_tier1": bool((tiers == 1).any()),
            "has_tier2": bool((tiers == 2).any()),
            "has_tier3": bool((tiers == 3).any()),
            "has_output_t1_t2": bool(tiers.isin([1, 2]).any()),
            # Sensitivity: explicit accreditation-route evidence only (Tier 1,
            # or Tier 2 whose statement names the route, not just an environment).
            "has_output_route_only": bool(route.any()),
            "has_output_any_tier": bool(tiers.isin([1, 2, 3]).any()),
            "n_outputs_t1_t2": int(headline["output_key"].nunique()) if len(headline) else 0,
            "n_outputs_any_tier": int(project_links.loc[tiers.isin([1, 2, 3]), "output_key"].nunique()) if len(project_links) else 0,
            "n_pending_adjudication": int((project_links["adjudication_status"] == "pending").sum()) if len(project_links) else 0,
            "n_index_reported_id_unconfirmed": int(index_id_only.sum()) if len(project_links) else 0,
            "first_output_date_t1_t2": first_date,
            "lag_months_t1_t2": lag,
        })
    return pd.DataFrame(records)


def source_yield_table(links: pd.DataFrame) -> pd.DataFrame:
    """Matches per source and tier, and outputs found by that source alone."""
    rows = []
    if not len(links):
        return pd.DataFrame(columns=["source", "tier", "project_output_pairs", "unique_pairs_this_source_only", "projects", "projects_this_source_only"])
    links = links.copy()
    links["tier_label"] = links["final_tier"].apply(lambda v: f"tier_{int(v)}" if str(v).strip() not in {"", "nan"} else "unresolved")
    links["source_list"] = links["sources"].str.split("; ")
    all_sources = sorted({s for sources in links["source_list"] for s in sources})
    for tier, tier_links in links.groupby("tier_label"):
        for source in all_sources:
            has = tier_links[tier_links["source_list"].apply(lambda s, src=source: src in s)]
            only = has[has["source_list"].apply(lambda s, src=source: s == [src])]
            # Projects reached through this source vs through any other source.
            here = set(has["Record ID"])
            elsewhere = set(
                tier_links.loc[tier_links["source_list"].apply(lambda s, src=source: any(x != src for x in s)), "Record ID"]
            )
            rows.append({
                "source": source,
                "tier": tier,
                "project_output_pairs": len(has),
                "unique_pairs_this_source_only": len(only),
                "projects": len(here),
                "projects_this_source_only": len(here - elsewhere),
            })
    return pd.DataFrame(rows)


def write_tables(out_dir: Path, tables: dict[str, pd.DataFrame]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(out_dir / name, index=False, encoding="utf-8")


def write_manifest(out_dir: Path, payload: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "run_manifest.json").write_text(
        config.redact(json.dumps(payload, indent=2, ensure_ascii=False, default=str)) + "\n", encoding="utf-8"
    )
