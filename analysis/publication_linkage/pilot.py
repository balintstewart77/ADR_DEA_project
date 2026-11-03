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
import json
import math
import re
import time
from collections import defaultdict
from datetime import date, datetime, timezone

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


def summarise_call_log(started_at: str, finished_at: str, call_log=None) -> dict:
    """Per-source live-call summary from ``call_log.jsonl`` in a UTC window."""
    path = call_log or (config.CACHE_DIR / "call_log.jsonl")
    summary: dict = defaultdict(lambda: {
        "live_calls": 0, "http_errors": 0, "blocked": False, "cost_usd": 0.0, "seconds_live": 0.0,
        "first_ts": None, "last_ts": None,
    })
    if not path.exists():
        return {}
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if not (started_at <= entry["ts"] <= finished_at):
            continue
        source = summary[entry["source"]]
        source["first_ts"] = source["first_ts"] or entry["ts"]
        source["last_ts"] = entry["ts"]
        if entry.get("outcome") == "blocked":
            source["blocked"] = True
            continue
        if "status" in entry:
            source["live_calls"] += 1
            source["http_errors"] += int(int(entry["status"]) >= 400)
            source["cost_usd"] = round(source["cost_usd"] + float(entry.get("cost_usd") or 0), 6)
            source["seconds_live"] = round(source["seconds_live"] + float(entry.get("seconds") or 0), 1)
    for source in summary.values():
        first, last = source.pop("first_ts"), source.pop("last_ts")
        source["elapsed_seconds"] = round(
            (datetime.fromisoformat(last) - datetime.fromisoformat(first)).total_seconds(), 1
        ) if first and last else 0.0
    return dict(summary)


def live_runs_record(runs: dict, enrichment_run, started_at: str, finished_at: str) -> dict:
    log = summarise_call_log(started_at, finished_at)
    sources = {}
    for name, run in [*runs.items(), ("semanticscholar", enrichment_run)]:
        sources[name] = {
            "status": run.status,
            "candidates": run.candidates,
            "live_calls": log.get(name, {}).get("live_calls", run.stats.get("live_calls", 0)),
            "cached_calls": run.stats.get("cached_calls", 0),
            "http_errors": log.get(name, {}).get("http_errors", 0),
            "cost_usd": log.get(name, {}).get("cost_usd", run.stats.get("cost_usd", 0.0)),
            "seconds": run.seconds,
            "notes": sorted(set(run.notes)),
        }
    return {"started_at": started_at, "finished_at": finished_at, "sources": sources}


def openalex_spend_line() -> str:
    from analysis.publication_linkage.http_client import OpenAlexBudget

    budget = OpenAlexBudget(config.CACHE_DIR)
    ledger = budget._load()
    days = ", ".join(
        f"{day}: ${record.get('cost_usd', 0):.4f}"
        + (f" (server credits left {record['server_remaining_credits']:,} of {record['server_limit_credits']:,})"
           if record.get("server_remaining_credits") is not None else "")
        for day, record in sorted(ledger.items())
    )
    return (f"- OpenAlex spend by UTC day (ledger of reported meta.cost_usd; stop at ${config.OPENALEX_STOP_AT_USD:.2f}"
            f" of the free $1): {days or 'none'}.")


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


_ID_IN_URL = re.compile(r"%22(?:[A-Za-z+]+\+)?20\d\d%2F\d{3}%22")


def call_scale(source: str, url: str) -> str:
    """What a logged call scales with: researcher, project, dataset or fixed."""
    if source == "openalex":
        if "/authors" in url or "authorships.author.id" in url:
            return "researcher"
        return "project" if _ID_IN_URL.search(url) else "fixed"
    if source == "core":
        if "authors%3A" in url:
            return "researcher"
        return "project" if _ID_IN_URL.search(url) or "doi%3A" in url else "fixed"
    if source == "europepmc":
        return "project" if _ID_IN_URL.search(url) or "DOI%3A" in url else "fixed"
    if source == "gtr":
        return "researcher"
    if source == "govuk":
        return "dataset"
    return "project"


def full_run_estimates(all_records, projects, snapshot_date: date, live: dict | None) -> pd.DataFrame:
    """Scale the live pilot's logged calls and costs to the whole register."""
    units_pilot = {
        "researcher": len(researcher_queries(projects, snapshot_date)),
        "project": len(projects),
        "dataset": len({d for p in projects for d in p.datasets}),
        "fixed": 1,
    }
    units_all = {
        "researcher": len(researcher_queries(all_records, snapshot_date)),
        "project": len(all_records),
        "dataset": len({d for r in all_records for d in r.datasets}),
        "fixed": 1,
    }
    rows = []
    if not live:
        return pd.DataFrame(rows)
    path = config.CACHE_DIR / "call_log.jsonl"
    tallies: dict = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))
    for line in path.read_text(encoding="utf-8").splitlines() if path.exists() else []:
        entry = json.loads(line)
        if not (live["started_at"] <= entry["ts"] <= live["finished_at"]) or "status" not in entry:
            continue
        scale = call_scale(entry["source"], entry.get("url", ""))
        tallies[entry["source"]][scale][0] += 1
        tallies[entry["source"]][scale][1] += float(entry.get("cost_usd") or 0)
    for source, by_scale in sorted(tallies.items()):
        calls = cost = 0.0
        pilot_calls = pilot_cost = 0.0
        for scale, (n, usd) in by_scale.items():
            factor = 0.0 if scale == "fixed" else units_all[scale] / max(units_pilot[scale], 1)
            # Fixed (register-wide phrase) calls are already cached: no repeat.
            calls += n * factor
            cost += usd * factor
            pilot_calls += n
            pilot_cost += usd
        rows.append({
            "source": source,
            "pilot_live_calls": int(pilot_calls),
            "pilot_cost_usd": round(pilot_cost, 4),
            "est_further_calls_full_run": int(round(calls)),
            "est_further_cost_usd": round(cost, 2),
            "est_days": (
                math.ceil(calls / 1000) if source == "core"
                else math.ceil(cost / config.OPENALEX_STOP_AT_USD) if source == "openalex" and cost
                else ""
            ),
            "limit_basis": {
                "core": "1,000 tokens/day (personal tier)",
                "openalex": f"${config.OPENALEX_STOP_AT_USD:.2f}/day stop within the free $1",
            }.get(source, "rate limit only"),
        })
    return pd.DataFrame(rows)


def write_report(out_dir, meta, sample, runs, enrichment_run, summary, links, yield_table, adjudication_counts, estimates, timings, live=None, completion=None) -> None:
    n = len(summary)
    t12 = int(summary["has_output_t1_t2"].sum())
    route_only = int(summary["has_output_route_only"].sum())
    index_id_unconfirmed = int((summary["n_index_reported_id_unconfirmed"] > 0).sum())
    any_tier = int(summary["has_output_any_tier"].sum())
    t1 = int(summary["has_tier1"].sum())
    t3_only = int((summary["has_tier3"] & ~summary["has_output_t1_t2"]).sum())
    tier_values = pd.to_numeric(links["final_tier"], errors="coerce") if len(links) else pd.Series(dtype=float)
    status_rows = []
    notes = []
    if live:
        for name, record in live["sources"].items():
            status_rows.append({
                "source": name, "status": record["status"], "candidates": record["candidates"],
                "live_calls": record["live_calls"], "http_errors": record["http_errors"],
                "cost_usd": record["cost_usd"], "seconds": record["seconds"],
            })
            notes.extend(f"- **{name}**: {note}" for note in record["notes"])
    else:
        for name, run in [*runs.items(), ("semanticscholar", enrichment_run)]:
            status_rows.append({
                "source": name, "status": run.status, "candidates": run.candidates,
                "live_calls": run.stats.get("live_calls", 0), "http_errors": run.stats.get("errors", 0),
                "cost_usd": run.stats.get("cost_usd", 0.0), "seconds": run.seconds,
            })
            notes.extend(f"- **{name}**: {note}" for note in sorted(set(run.notes)))
    live_sources = live["sources"] if live else {n: {"status": r.status} for n, r in [*runs.items(), ("semanticscholar", enrichment_run)]}
    aggregations = dict(
        projects=("Record ID", "count"), with_t1_t2=("has_output_t1_t2", "sum"),
        with_route_only=("has_output_route_only", "sum"), with_any_tier=("has_output_any_tier", "sum"),
    )
    by_year = summary.groupby("accreditation_year").agg(**aggregations).reset_index()
    by_sector = summary.groupby("sector_group").agg(**aggregations).reset_index()
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
    blocked = [name for name, record in live_sources.items() if record["status"] == "blocked"]
    ran = [name for name, record in live_sources.items() if record["status"] in {"ok", "budget_stopped"}]

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
        *([
            "- Because sources were blocked, **this is a partial pilot**: rates, overlaps and source recommendations"
            " below cover only the sources that ran. Re-running the same command once access is open adds the"
            " missing sources (cached calls are reused).",
        ] if blocked else []),
        *([openalex_spend_line()] if "openalex" in live_sources else []),
        "",
        "## Sample",
        "",
        f"{len(sample)} projects drawn with seed {PILOT_SEED}, proportional to accreditation year x sector group"
        " (largest-remainder allocation).",
        "",
        markdown_table(sample.groupby(["accreditation_year", "sector_group"]).size().unstack(fill_value=0).reset_index()),
        "## Source runs",
        "",
        (f"Live run {live['started_at']} to {live['finished_at']} (UTC); calls and errors from the call log."
         f" Tables were rebuilt from the cache on {timings['run_date']} without further calls." if live else ""),
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
        "Overlap between sources, Tier 1-2 outputs (each output counted once, by the set of sources that found it):",
        "",
        markdown_table(source_overlap(links, (1, 2)) if len(links) else pd.DataFrame()),
        "Overlap between sources, Tier 1-3 outputs:",
        "",
        markdown_table(source_overlap(links, (1, 2, 3)) if len(links) else pd.DataFrame()),
        (f"Full-text completion for index-reported evidence: {completion.get('wanted', 0)} DOIs wanted;"
         f" text found via CORE {completion.get('core', 0)}, Europe PMC {completion.get('europepmc', 0)};"
         f" not found {completion.get('not_found', 0)}." if completion else ""),
        "",
        "## Share of pilot projects with a findable output",
        "",
        f"- Tier 1 or 2 (headline definition): {wilson_text(t12, n)}",
        f"- Sensitivity, explicit accreditation-route statements only (Tier 1, or Tier 2 naming the DEA route,"
        f" Research Accreditation Panel, accredited researcher or UKSA; environment-only Tier 2 excluded):"
        f" {wilson_text(route_only, n)}",
        f"- Tier 1 (project ID quoted): {wilson_text(t1, n)}",
        f"- Any tier including Tier 3 (probable): {wilson_text(any_tier, n)}; Tier 3 only: {t3_only}",
        f"- Projects with an index-reported Project ID that no available full text confirms: {index_id_unconfirmed}",
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
        "- CORE's index rejects every documented full-text lookup (including the docs' own examples), so CORE phrase"
        " and project-ID searches reach titles and abstracts only; CORE full text is scanned locally on"
        " author-centred results.",
        "- OpenAlex matches phrases and project IDs in full text it does not return; such hits count only once CORE"
        " or Europe PMC text lets the rules quote them.",
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
    parser.add_argument("--name", default="pilot", help="output folder under the run date")
    parser.add_argument(
        "--record-live-window", nargs=2, metavar=("START", "END"),
        help="with --offline: record the live-run window (UTC ISO timestamps) from the call log",
    )
    args = parser.parse_args(argv)

    started = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out_dir = config.OUTPUT_ROOT / args.run_date / args.name
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
    completed, completion_stats = complete_full_texts(groups, projects, snapshot, offline=args.offline, cache_dir=config.CACHE_DIR)
    candidates += completed
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
    queue = write_queue(rows, out_dir)
    links, adjudication_counts = apply_decisions(links, out_dir, queue["items"])
    adjudication_counts["round_written"] = queue["round"].name if queue["round"] else ""
    summary = project_summary_table(projects, links, outputs, snapshot, cutoff)
    yield_table = source_yield_table(links)

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
    }
    for name, frame_extra in (("author_resolution", "openalex_author_resolution.csv"), ("grant_links", "gtr_grant_links.csv")):
        if extras.get(name):
            tables[frame_extra] = pd.DataFrame(extras[name])
    write_tables(out_dir, tables)
    live_path = out_dir / "live_source_runs.json"
    if not args.offline:
        live = live_runs_record(runs, enrichment_run, started_at, datetime.now(timezone.utc).isoformat(timespec="seconds"))
        live_path.write_text(json.dumps(live, indent=2) + "\n", encoding="utf-8")
    elif args.record_live_window:
        # Reconstruct the record of an earlier live run from the call log.
        live = live_runs_record(runs, enrichment_run, *args.record_live_window)
        log = summarise_call_log(*args.record_live_window)
        for name, record in live["sources"].items():
            record["notes"] = [n for n in record["notes"] if "offline mode" not in n]
            record["seconds"] = log.get(name, {}).get("elapsed_seconds", record["seconds"])
            if log.get(name, {}).get("blocked"):
                record["status"] = "blocked"
                record["notes"].append("network policy refused host (proxy 403)")
        live["reconstructed_from_call_log"] = True
        live_path.write_text(json.dumps(live, indent=2) + "\n", encoding="utf-8")
    else:
        live = json.loads(live_path.read_text(encoding="utf-8")) if live_path.exists() else None
    estimates = full_run_estimates(records, projects, snapshot, live)
    write_tables(out_dir, {"full_run_estimates.csv": estimates})
    timings = {"run_date": args.run_date, "mature_cutoff": cutoff.isoformat(), "seconds": round(time.monotonic() - started, 1)}
    write_report(out_dir, meta, sample, runs, enrichment_run, summary, links, yield_table, adjudication_counts, estimates, timings, live, completion_stats)
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
        "full_text_completion": completion_stats,
        "seconds": timings["seconds"],
        "offline": args.offline,
        "live_run": {k: live[k] for k in ("started_at", "finished_at")} if live else None,
    })
    print(f"[pilot] wrote {out_dir} in {timings['seconds']}s")


if __name__ == "__main__":
    main()

