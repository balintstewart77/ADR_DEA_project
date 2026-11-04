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
            ok = int(entry["status"]) == 200
            source["live_calls"] += 1
            source["http_errors"] += int(int(entry["status"]) >= 400)
            source["rate_limited"] = source.get("rate_limited", 0) + int(int(entry["status"]) == 429)
            # Only successful calls are charged (see http_client).
            source["cost_usd"] = round(source["cost_usd"] + (float(entry.get("cost_usd") or 0) if ok else 0.0), 6)
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
            "rate_limited": log.get(name, {}).get("rate_limited", 0),
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
        if "fullTextXML" in url:
            return "researcher"  # fetched only for hits sharing a register family name
        return "project" if _ID_IN_URL.search(url) or "DOI%3A" in url else "fixed"
    if source == "gtr":
        return "researcher"
    if source == "govuk":
        return "dataset"
    return "project"


def openalex_list_price(url: str) -> float:
    """List price of an OpenAlex call (matches meta.cost_usd, verified live)."""
    if "search=" in url:
        return config.OPENALEX_PRICE_USD["search"]
    if "/works?" in url or "/authors?" in url:
        return config.OPENALEX_PRICE_USD["list"]
    return config.OPENALEX_PRICE_USD["singleton"]


def full_run_estimates(all_records, projects, snapshot_date: date, request_log: list[dict]) -> pd.DataFrame:
    """Scale every request this pilot needed (cached or live) to the register.

    Calls are classed by what they scale with (researcher, project, dataset);
    register-wide phrase searches are "fixed": already cached and reused.
    """
    units_pilot = {
        "researcher": len(researcher_queries(projects, snapshot_date)),
        "project": len(projects),
        "dataset": len({d for p in projects for d in p.datasets}),
    }
    units_all = {
        "researcher": len(researcher_queries(all_records, snapshot_date)),
        "project": len(all_records),
        "dataset": len({d for r in all_records for d in r.datasets}),
    }
    tallies: dict = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))
    for entry in request_log:
        if entry.get("status") not in (200, 404):
            continue
        scale = call_scale(entry["source"], entry["url"])
        price = openalex_list_price(entry["url"]) if entry["source"] == "openalex" else 0.0
        tallies[entry["source"]][scale][0] += 1
        tallies[entry["source"]][scale][1] += price
    rows = []
    for source, by_scale in sorted(tallies.items()):
        needed = sum(n for n, _ in by_scale.values())
        fixed = by_scale.get("fixed", [0, 0.0])[0]
        calls = sum(n * units_all[s] / max(units_pilot[s], 1) for s, (n, _) in by_scale.items() if s != "fixed")
        cost = sum(usd * units_all[s] / max(units_pilot[s], 1) for s, (_, usd) in by_scale.items() if s != "fixed")
        rows.append({
            "source": source,
            "pilot_calls_needed": needed,
            "of_which_register_wide": fixed,
            "est_calls_full_run": int(round(calls)),
            "est_cost_usd": round(cost, 2),
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
                "of_which_429": record.get("rate_limited", 0),
                "cost_usd": record["cost_usd"], "seconds_in_responses": record["seconds"],
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
    failed = [name for name, record in live_sources.items() if record["status"] == "failed"]
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
        f"- Sources that ran: {', '.join(ran) or 'none'}. Blocked by the network policy: "
        f"{', '.join(blocked) or 'none'}. Failed: {', '.join(failed) or 'none'} (see source notes).",
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
        "Per source and tier. Pairs and projects count discovery (unique = found by that source alone);"
        " statement_text_supplied counts pairs where that source's own abstract or full text carries the"
        " qualifying statement (the text that makes Tier 2 checkable), and _only_ where no other source did:",
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
        *(["- Blocked sources mean recall here is lower than the full design would give."] if blocked else []),
        *([f"- Failed this run: {', '.join(failed)}; Semantic Scholar is enrichment only, so abstracts came from"
           " OpenAlex, Europe PMC and CORE."] if failed else []),
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


def report_only(out_dir, args) -> None:
    """Regenerate estimates and the report from a finished run's saved files."""
    from analysis.publication_linkage.pipeline import SourceRun

    df, meta = load_register()
    records = build_project_records(df)
    snapshot = date.fromisoformat(meta["snapshot_date"])
    cutoff = mature_cutoff(snapshot)
    sample = draw_pilot_sample(records_frame(records), cutoff)
    by_id = {record.record_id: record for record in records}
    projects = [by_id[record_id] for record_id in sample["Record ID"]]
    manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
    links = pd.read_csv(out_dir / "project_output_links.csv", dtype={"final_tier": object})
    links["final_tier"] = links["final_tier"].fillna("")
    summary = pd.read_csv(out_dir / "project_summary.csv")
    live_path = out_dir / "live_source_runs.json"
    live = json.loads(live_path.read_text(encoding="utf-8")) if live_path.exists() else None
    request_log_path = config.CACHE_DIR / "request_logs" / f"{args.run_date}_{args.name}.jsonl"
    request_log = [json.loads(line) for line in request_log_path.read_text(encoding="utf-8").splitlines()]
    estimates = full_run_estimates(records, projects, snapshot, request_log)
    yield_table = source_yield_table(links)
    write_tables(out_dir, {"full_run_estimates.csv": estimates, "source_yield.csv": yield_table})
    timings = {"run_date": args.run_date, "mature_cutoff": cutoff.isoformat(), "seconds": manifest.get("seconds")}
    write_report(
        out_dir, meta, sample, {}, SourceRun("semanticscholar"), summary, links, yield_table,
        manifest["adjudication"], estimates, timings, live, manifest.get("full_text_completion"),
    )
    print(f"[pilot] report rewritten in {out_dir}")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-date", default=date.today().strftime("%Y%m%d"))
    parser.add_argument("--sources", default=",".join(ALL_SOURCES))
    parser.add_argument("--offline", action="store_true", help="use cached responses only")
    parser.add_argument("--no-enrich", action="store_true")
    parser.add_argument("--name", default="pilot", help="output folder under the run date")
    parser.add_argument("--report-only", action="store_true", help="rewrite the report from the saved tables")
    parser.add_argument(
        "--record-live-window", nargs=2, metavar=("START", "END"),
        help="with --offline: record the live-run window (UTC ISO timestamps) from the call log",
    )
    args = parser.parse_args(argv)

    started = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out_dir = config.OUTPUT_ROOT / args.run_date / args.name
    if args.report_only:
        report_only(out_dir, args)
        return
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
            record["seconds"] = log.get(name, {}).get("seconds_live", record["seconds"])
            if log.get(name, {}).get("blocked"):
                record["status"] = "blocked"
                record["notes"].append("network policy refused host (proxy 403)")
            elif record["status"] == "blocked" and log.get(name, {}).get("live_calls"):
                # Offline "blocked" only means nothing was cached: live calls
                # were made and failed.
                entry = log[name]
                record["status"] = "failed"
                record["notes"].append(
                    f"{entry['http_errors']} of {entry['live_calls']} live calls failed "
                    f"({entry.get('rate_limited', 0)} rate-limited, HTTP 429)"
                )
        live["reconstructed_from_call_log"] = True
        live_path.write_text(json.dumps(live, indent=2) + "\n", encoding="utf-8")
    else:
        live = json.loads(live_path.read_text(encoding="utf-8")) if live_path.exists() else None
    from analysis.publication_linkage.http_client import REQUEST_LOG

    request_log_path = config.CACHE_DIR / "request_logs" / f"{args.run_date}_{args.name}.jsonl"
    request_log_path.parent.mkdir(parents=True, exist_ok=True)
    request_log_path.write_text(
        "".join(config.redact(json.dumps(entry)) + "\n" for entry in REQUEST_LOG), encoding="utf-8"
    )
    estimates = full_run_estimates(records, projects, snapshot, REQUEST_LOG)
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

