"""Feasibility pilot: 50 mature-cohort projects, every source, stop and report.

Usage::

    python -m analysis.publication_linkage.pilot --run-date 20261103
    python -m analysis.publication_linkage.pilot --run-date 20261103 --offline   # rebuild from cache

The sample is stratified by accreditation year and researcher-sector group
with proportional (largest-remainder) allocation, drawn from projects
accredited at least two years before the register snapshot. The seed and
allocation are written next to the outputs so the draw can be reproduced and
later draws (validation recall sheet) can exclude it.
"""

from __future__ import annotations

import argparse
import math
import time
from datetime import date

import numpy as np
import pandas as pd

from analysis.publication_linkage import config
from analysis.publication_linkage.adjudication import apply_decisions, write_queue
from analysis.publication_linkage.outputs import dedupe_outputs
from analysis.publication_linkage.pipeline import (
    ALL_SOURCES,
    complete_full_texts,
    enrich,
    link_outputs,
    links_table,
    outputs_table,
    project_summary_table,
    run_sources,
    source_yield_table,
    write_manifest,
    write_tables,
)
from analysis.publication_linkage.register_records import (
    build_project_records,
    load_register,
    mature_cutoff,
    records_frame,
)
from analysis.publication_linkage.sources import researcher_queries
from analysis.validation.intervals import wilson_interval

PILOT_SIZE = 50
PILOT_SEED = 20261103


def allocate(counts: pd.Series, n: int) -> pd.Series:
    """Proportional allocation with largest remainders (Hamilton)."""
    total = counts.sum()
    quotas = counts / total * n
    base = np.floor(quotas).astype(int)
    remainder = n - int(base.sum())
    order = (quotas - base).sort_values(ascending=False, kind="mergesort").index[:remainder]
    base.loc[order] += 1
    return base.clip(upper=counts)


def allocate_two_stage(eligible: pd.DataFrame, n: int) -> pd.Series:
    """Years first (proportional, at least one per year), then sector groups
    within each year (proportional). Returns allocation per stratum label."""
    year_counts = eligible.groupby("accreditation_year").size()
    year_alloc = pd.Series(1, index=year_counts.index)
    year_alloc += allocate(year_counts, n - len(year_counts)).reindex(year_counts.index, fill_value=0)
    year_alloc = year_alloc.clip(upper=year_counts)
    allocation = {}
    for year, k in year_alloc.items():
        sector_counts = eligible[eligible["accreditation_year"] == year].groupby("sector_group").size()
        for sector, m in allocate(sector_counts, int(k)).items():
            allocation[f"{year} | {sector}"] = int(m)
    return pd.Series(allocation)


def draw_pilot_sample(frame: pd.DataFrame, cutoff: date, n: int = PILOT_SIZE, seed: int = PILOT_SEED) -> pd.DataFrame:
    eligible = frame[pd.to_datetime(frame["accreditation_date"]).dt.date <= cutoff].copy()
    eligible["stratum"] = eligible["accreditation_year"].astype(str) + " | " + eligible["sector_group"]
    counts = eligible.groupby("stratum").size()
    allocation = allocate_two_stage(eligible, n)
    rng = np.random.RandomState(seed)
    chosen = []
    for stratum in sorted(allocation.index):
        k = int(allocation[stratum])
        if k == 0:
            continue
        members = eligible[eligible["stratum"] == stratum].sort_values("Record ID")
        picks = rng.choice(len(members), size=k, replace=False)
        chosen.append(members.iloc[sorted(picks)])
    sample = pd.concat(chosen, ignore_index=True)
    sample["stratum_population"] = sample["stratum"].map(counts)
    sample["stratum_allocation"] = sample["stratum"].map(allocation)
    sample["design_weight"] = sample["stratum_population"] / sample["stratum_allocation"]
    sample["sampling_seed"] = seed
    return sample


def wilson_text(k: int, n: int) -> str:
    if n == 0:
        return "n/a"
    interval = wilson_interval(int(k), int(n))
    return f"{k}/{n} = {k / n:.0%} (95% Wilson CI {interval.lower:.0%} to {interval.upper:.0%})"


def source_overlap(links: pd.DataFrame, tiers: tuple[int, ...]) -> pd.DataFrame:
    tier_values = pd.to_numeric(links["final_tier"], errors="coerce")
    subset = links[tier_values.isin(tiers)]
    if not len(subset):
        return pd.DataFrame(columns=["sources", "outputs"])
    per_output = subset.groupby("output_key")["sources"].first()
    return per_output.value_counts().rename_axis("sources").reset_index(name="outputs")


def markdown_table(frame: pd.DataFrame) -> str:
    if not len(frame):
        return "_none_\n"
    columns = [str(c) for c in frame.columns]
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in frame.itertuples(index=False):
        lines.append("| " + " | ".join("" if (isinstance(v, float) and math.isnan(v)) else str(v) for v in row) + " |")
    return "\n".join(lines) + "\n"


def full_run_estimates(all_records, snapshot_date: date, pilot_runs: dict, pilot_researchers: int) -> pd.DataFrame:
    researchers_all = len(researcher_queries(all_records, snapshot_date))
    datasets_all = len({d for r in all_records for d in r.datasets})
    rows = []
    core = pilot_runs.get("core")
    if core and pilot_researchers:
        live = core.stats.get("live_calls", 0) + core.stats.get("cached_calls", 0)
        per_researcher = live / pilot_researchers
        calls = round(per_researcher * researchers_all)
        rows.append({
            "source": "core", "pilot_calls": live, "unit": "unique researcher",
            "units_full_register": researchers_all, "est_calls_full_run": calls,
            "est_days_at_1000_tokens_per_day": math.ceil(calls / 1000),
            "est_cost_usd": 0.0,
        })
    # OpenAlex: author search ($0.001) + one list page per researcher ($0.0001)
    # + phrase-search pages (counted once for the whole register).
    openalex = pilot_runs.get("openalex")
    phrase_pages = 13 * 5
    est_cost = researchers_all * (0.001 + 0.0001) + phrase_pages * 0.001
    rows.append({
        "source": "openalex", "pilot_calls": (openalex.stats.get("live_calls", 0) if openalex else 0),
        "unit": "unique researcher (+ phrase pages)", "units_full_register": researchers_all,
        "est_calls_full_run": researchers_all * 2 + phrase_pages,
        "est_days_at_1000_tokens_per_day": "",
        "est_cost_usd": round(est_cost, 2),
    })
    rows.append({
        "source": "govuk", "pilot_calls": (pilot_runs["govuk"].stats.get("live_calls", 0) if "govuk" in pilot_runs else 0),
        "unit": "register dataset x 3 route terms (+ page fetches)", "units_full_register": datasets_all,
        "est_calls_full_run": datasets_all * 3, "est_days_at_1000_tokens_per_day": "", "est_cost_usd": 0.0,
    })
    return pd.DataFrame(rows)


def write_report(out_dir, meta, sample, runs, enrichment_run, summary, links, yield_table, adjudication_counts, estimates, timings) -> None:
    n = len(summary)
    t12 = int(summary["has_output_t1_t2"].sum())
    any_tier = int(summary["has_output_any_tier"].sum())
    t1 = int(summary["has_tier1"].sum())
    t3_only = int((summary["has_tier3"] & ~summary["has_output_t1_t2"]).sum())
    tier_values = pd.to_numeric(links["final_tier"], errors="coerce") if len(links) else pd.Series(dtype=float)
    status_rows = []
    for name, run in [*runs.items(), ("semanticscholar", enrichment_run)]:
        status_rows.append({
            "source": name, "status": run.status, "candidates": run.candidates,
            "live_calls": run.stats.get("live_calls", 0), "cached_calls": run.stats.get("cached_calls", 0),
            "errors": run.stats.get("errors", 0), "cost_usd": run.stats.get("cost_usd", 0.0),
            "seconds": run.seconds or run.stats.get("seconds_live", 0),
        })
    notes = []
    for name, run in [*runs.items(), ("semanticscholar", enrichment_run)]:
        for note in sorted(set(run.notes)):
            notes.append(f"- **{name}**: {note}")
    by_year = summary.groupby("accreditation_year").agg(projects=("Record ID", "count"), with_t1_t2=("has_output_t1_t2", "sum"), with_any_tier=("has_output_any_tier", "sum")).reset_index()
    by_sector = summary.groupby("sector_group").agg(projects=("Record ID", "count"), with_t1_t2=("has_output_t1_t2", "sum"), with_any_tier=("has_output_any_tier", "sum")).reset_index()
    pairs_by_tier = pd.DataFrame({
        "tier": ["Tier 1", "Tier 2", "Tier 3", "unresolved (pending adjudication / rejected)"],
        "project_output_pairs": [
            int((tier_values == 1).sum()), int((tier_values == 2).sum()), int((tier_values == 3).sum()),
            int(tier_values.isna().sum()),
        ],
    })
    statement_split = (
        links[tier_values == 2].groupby("statement_type").size().rename("tier2_pairs").reset_index()
        if len(links) else pd.DataFrame()
    )
    lags = summary["lag_months_t1_t2"].dropna()
    blocked = [name for name, run in runs.items() if run.status == "blocked"]
    if enrichment_run.status == "blocked":
        blocked.append("semanticscholar")
    ran = [name for name, run in runs.items() if run.status in {"ok", "budget_stopped"}]

    lines = [
        f"# Publication linkage: feasibility pilot ({timings['run_date']})",
        "",
        "> **Absence of a findable output is not evidence of no output.** Government analysts' work is often",
        "> internal, and many papers do not acknowledge the accreditation. Every rate below is a lower bound on",
        "> public, findable, attributable outputs, not on research activity. Project-level files in this folder are",
        "> working data; anything published is aggregated.",
        "",
        "## Status",
        "",
        f"- Register snapshot {meta['snapshot_date']} (version {meta['register_version']}), {meta['records']:,} cleaned records.",
        f"- Mature cohort: accredited on or before {timings['mature_cutoff']} (two years before the snapshot).",
        f"- Sources that ran: {', '.join(ran) or 'none'}. Sources blocked by the session's network policy: "
        f"{', '.join(blocked) or 'none'}.",
        "- Because sources were blocked, **this is a partial pilot**: rates, overlaps and source recommendations below"
        " cover only the sources that ran. Re-running the same command once access is open adds the missing"
        " sources (cached calls are reused).",
        "",
        "## Sample",
        "",
        f"{len(sample)} projects drawn with seed {PILOT_SEED}, proportional to accreditation year x sector group"
        " (largest-remainder allocation).",
        "",
        markdown_table(sample.groupby(["accreditation_year", "sector_group"]).size().unstack(fill_value=0).reset_index()),
        "## Source runs",
        "",
        markdown_table(pd.DataFrame(status_rows)),
        *notes,
        "",
        "## Matches",
        "",
        markdown_table(pairs_by_tier),
        "Tier 2 pairs by statement type (route = DEA / Research Accreditation Panel / accredited researcher / UKSA;"
        " environment = the project's own secure environment named):",
        "",
        markdown_table(statement_split),
        "Per source and tier (pairs; unique = found by that source alone):",
        "",
        markdown_table(yield_table),
        "Overlap between sources, Tier 1-2 outputs:",
        "",
        markdown_table(source_overlap(links, (1, 2)) if len(links) else pd.DataFrame()),
        "## Share of pilot projects with a findable output",
        "",
        f"- Tier 1 or 2 (headline definition): {wilson_text(t12, n)}",
        f"- Tier 1 (project ID quoted): {wilson_text(t1, n)}",
        f"- Any tier including Tier 3 (probable): {wilson_text(any_tier, n)}; Tier 3 only: {t3_only}",
        f"- Median lag from accreditation to first Tier 1-2 output: "
        f"{(f'{lags.median():.0f} months (n={len(lags)})') if len(lags) else 'n/a'}",
        "",
        "Unweighted counts; the proportional design makes the sample roughly self-weighting by year x sector."
        " Pilot intervals are wide by design and are not the headline estimate.",
        "",
        markdown_table(by_year),
        markdown_table(by_sector),
        "## Adjudication",
        "",
        "Pairs the rules cannot settle (initial-only author, acronym-only dataset, another environment named,"
        " or a strong statement with no dataset string) are queued for helper-agent adjudication; each decision"
        " must quote the shown text verbatim, and the quote is checked by code.",
        "",
        markdown_table(pd.DataFrame([adjudication_counts])),
        "## Full-run estimates",
        "",
        markdown_table(estimates),
        "## Limitations",
        "",
        "- Blocked sources mean recall here is lower than the full design would give.",
        "- CORE's documented full-text and abstract search currently fails server-side, so CORE phrase searches"
        " fall back to titles and CORE contributes through author-centred retrieval with local full-text scanning.",
        "- Author matching is by family name plus a compatible first given name; common names can produce false"
        " candidates (mitigated by the dataset, statement and date conditions).",
        "- Environment statements for SAIL, UKDS SecureLab, NISRA and Scottish Safe Havens are weaker evidence of"
        " DEA use than DEA/RAP statements, because those environments host non-DEA work too; Tier 2 is split by"
        " statement type above for that reason.",
        "- Outputs shared by two projects with the same team count for both.",
        "",
    ]
    (out_dir / "pilot_report.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-date", default=date.today().strftime("%Y%m%d"))
    parser.add_argument("--sources", default=",".join(ALL_SOURCES))
    parser.add_argument("--offline", action="store_true", help="use cached responses only")
    parser.add_argument("--no-enrich", action="store_true")
    args = parser.parse_args(argv)

    started = time.monotonic()
    out_dir = config.OUTPUT_ROOT / args.run_date / "pilot"
    df, meta = load_register()
    records = build_project_records(df)
    snapshot = date.fromisoformat(meta["snapshot_date"])
    cutoff = mature_cutoff(snapshot)
    frame = records_frame(records)
    sample = draw_pilot_sample(frame, cutoff)
    by_id = {record.record_id: record for record in records}
    projects = [by_id[record_id] for record_id in sample["Record ID"]]
    print(f"[pilot] {len(projects)} projects; snapshot {snapshot}; mature cutoff {cutoff}")

    sources = tuple(s.strip() for s in args.sources.split(",") if s.strip())
    candidates, runs, extras = run_sources(projects, snapshot, sources, offline=args.offline)
    groups = dedupe_outputs(candidates)
    candidates += complete_full_texts(groups, projects, snapshot, offline=args.offline, cache_dir=config.CACHE_DIR)
    groups = dedupe_outputs(candidates)
    from analysis.publication_linkage.pipeline import SourceRun

    enrichment_run = SourceRun("semanticscholar", status="skipped")
    if not args.no_enrich:
        added, enrichment_run = enrich(groups, offline=args.offline, cache_dir=config.CACHE_DIR)
        if added:
            candidates += added
            groups = dedupe_outputs(candidates)

    rows = link_outputs(groups, projects, snapshot)
    linked_keys = {row.group.output_key for row in rows}
    outputs = outputs_table([g for g in groups if g.output_key in linked_keys])
    links = links_table(rows)
    write_queue(rows, out_dir)
    links, adjudication_counts = apply_decisions(links, out_dir)
    summary = project_summary_table(projects, links, outputs, snapshot, cutoff)
    yield_table = source_yield_table(links)
    estimates = full_run_estimates(records, snapshot, runs, len(researcher_queries(projects, snapshot)))

    sample_out = sample[[
        "Record ID", "Project ID", "accreditation_date", "accreditation_year", "sector_group", "environment",
        "record_linkage", "stratum", "stratum_population", "stratum_allocation", "design_weight", "sampling_seed",
    ]]
    tables = {
        "pilot_sample.csv": sample_out,
        "outputs.csv": outputs,
        "project_output_links.csv": links,
        "project_summary.csv": summary,
        "source_yield.csv": yield_table,
        "full_run_estimates.csv": estimates,
    }
    for name, frame_extra in (("author_resolution", "openalex_author_resolution.csv"), ("grant_links", "gtr_grant_links.csv")):
        if extras.get(name):
            tables[frame_extra] = pd.DataFrame(extras[name])
    write_tables(out_dir, tables)
    timings = {"run_date": args.run_date, "mature_cutoff": cutoff.isoformat(), "seconds": round(time.monotonic() - started, 1)}
    write_report(out_dir, meta, sample, runs, enrichment_run, summary, links, yield_table, adjudication_counts, estimates, timings)
    write_manifest(out_dir, {
        "kind": "publication_linkage_pilot",
        "run_date": args.run_date,
        "register": meta,
        "mature_cutoff": cutoff.isoformat(),
        "sample_seed": PILOT_SEED,
        "sources_requested": list(sources),
        "source_runs": {name: {"status": r.status, "candidates": r.candidates, "stats": r.stats, "notes": r.notes} for name, r in runs.items()},
        "enrichment": {"status": enrichment_run.status, "stats": enrichment_run.stats, "notes": enrichment_run.notes},
        "candidates_retrieved": len(candidates),
        "outputs_deduplicated": len(groups),
        "outputs_linked": len(outputs),
        "links": len(links),
        "adjudication": adjudication_counts,
        "seconds": timings["seconds"],
        "offline": args.offline,
    })
    print(f"[pilot] wrote {out_dir} in {timings['seconds']}s")


if __name__ == "__main__":
    main()

