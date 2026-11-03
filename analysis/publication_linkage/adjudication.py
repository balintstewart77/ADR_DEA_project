"""AI adjudication for Tier 2/3 candidates the rules cannot settle.

Workflow:

1. :func:`write_queue` writes ``adjudication/round_NNN/batch_NNN.jsonl`` files
   (only for items without a decision made on identical text). Each item
   carries the register record and the output's title, abstract and
   acknowledgement/data-statement snippets -- nothing else -- plus the rule
   evidence, and a ``source_text`` string that is the exact text shown.
2. Helper agents (a cheaper model) read one batch each, following
   ``adjudication/INSTRUCTIONS.md``, and write ``batch_NNN.decisions.jsonl``
   with one JSON object per item:
   ``{"item_id", "match", "tier", "reason", "evidence_quote"}``.
3. :func:`apply_decisions` checks that every ``evidence_quote`` occurs
   verbatim in the item's ``source_text`` (after whitespace/dash/quote
   normalisation only) and folds verified decisions into the links table.

Reviewer decisions in ``adjudication/reviewer_decisions.jsonl`` are applied
last and are final.

Guards: an adjudicator can confirm, downgrade or reject a rule tier and can
raise a near miss to Tier 2/3; it can never assign Tier 1, and it can give
Tier 2 only when the rules found an accreditation/environment statement.
Unverified quotes are discarded and the rule tier stands.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from analysis.publication_linkage.matching import clean_text

BATCH_SIZE = 15
MAX_ABSTRACT_CHARS = 2500

INSTRUCTIONS = """# Adjudication instructions

You are checking whether a public output (paper, report, thesis) came from a
specific DEA-accredited research project on the UK Statistics Authority
register. Each line of the batch file is one JSON item with:

* `record`: the register entry (project title, accreditation date,
  processing environment, researchers with institutions, datasets);
* `output`: the output's title, year, venue, authors, abstract and
  `snippets` (acknowledgement / data-statement sentences);
* `rule_evidence`: what string-matching rules found (author matches,
  datasets named, statement type) and why the item needs a decision.

Decide, using only the text given:

* `match`: true if the output plausibly reports work from THIS register
  project (same researchers, same data, consistent topic and timing), false
  otherwise. Shared authors alone are not enough; the data and topic must fit.
* `tier`: 2 if the output also names the accreditation route (Digital
  Economy Act, Research Accreditation Panel, accredited researcher, UK
  Statistics Authority) or the project's secure environment; 3 if the match
  is probable but no such statement is present; null when `match` is false.
  Never give tier 1.
* `reason`: one or two sentences.
* `evidence_quote`: a verbatim quote (copied exactly, 5-60 words) from the
  `source_text` field that best supports your decision. Do not paraphrase.

Write one JSON object per line to the decisions file, in the same order:
{"item_id": "...", "match": true, "tier": 2, "reason": "...", "evidence_quote": "..."}
Output nothing else in that file.
"""


def _norm(text: object) -> str:
    return " ".join(clean_text(text).split())


def queue_items(rows) -> list[dict]:
    """Adjudication items for LinkRows flagged ``needs_adjudication``."""
    items = []
    for row in rows:
        if not row.needs_adjudication:
            continue
        group = row.group
        primary = group.primary
        abstract = next((clean_text(m.abstract) for m in group.members if m.abstract), "")[:MAX_ABSTRACT_CHARS]
        snippets = group.snippets()[:4]
        source_text = "\n".join(part for part in [primary.title, abstract, *snippets] if part)
        items.append({
            "item_id": f"{row.project.record_id}|{group.output_key}",
            "record": row.project.summary(),
            "output": {
                "output_key": group.output_key,
                "title": primary.title,
                "year": group.year,
                "venue": primary.venue,
                "authors": group.authors()[:30],
                "abstract": abstract,
                "snippets": snippets,
            },
            "rule_evidence": {
                "rule_tier": row.tier,
                "reasons": list(row.reasons),
                "author_matches": [f"{a} = {b} ({lvl})" for a, b, lvl in row.evidence.author_matches],
                "datasets_named": sorted({label for _, label, _ in row.evidence.dataset_hits}),
                "statement_type": row.evidence.statement_type,
            },
            "source_text": source_text,
        })
    return items


def source_sha(item: dict) -> str:
    return hashlib.sha256(item["source_text"].encode("utf-8")).hexdigest()


def round_dirs(folder: Path) -> list[Path]:
    return sorted(path for path in folder.glob("round_*") if path.is_dir())


def load_rounds(folder: Path) -> dict[str, dict]:
    """item_id -> {"sha", "decision", "round"} for every decided item.

    Each round's ``manifest.json`` (tracked) records the SHA-256 of the text
    each item was shown, so a decision is reused only on identical text even
    where the batch inputs themselves are not kept.
    """
    decided: dict[str, dict] = {}
    for round_dir in round_dirs(folder):
        manifest_path = round_dir / "manifest.json"
        shas = json.loads(manifest_path.read_text(encoding="utf-8")).get("items", {}) if manifest_path.exists() else {}
        for decision_path in sorted(round_dir.glob("batch_*.decisions.jsonl")):
            for decision in read_jsonl(decision_path):
                item_id = str(decision.get("item_id"))
                if item_id in shas:
                    decided[item_id] = {"sha": shas[item_id], "decision": decision, "round": round_dir.name}
    return decided


def write_queue(rows, out_dir: Path, batch_size: int = BATCH_SIZE) -> dict:
    """Queue items without a reusable decision into a new adjudication round.

    Returns {"items": all current items by id, "pending": ids needing a
    decision, "round": the round directory written (or None)}.
    """
    folder = out_dir / "adjudication"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "INSTRUCTIONS.md").write_text(INSTRUCTIONS, encoding="utf-8")
    items = {item["item_id"]: item for item in queue_items(rows)}
    decided = load_rounds(folder)
    pending = [item_id for item_id, item in items.items() if decided.get(item_id, {}).get("sha") != source_sha(item)]
    round_dir = None
    if pending:
        rounds = round_dirs(folder)
        latest = rounds[-1] if rounds else None
        if latest is not None and not list(latest.glob("batch_*.decisions.jsonl")):
            round_dir = latest  # undecided round: rewrite it
            for old in latest.glob("batch_*.jsonl"):
                old.unlink()
        else:
            round_dir = folder / f"round_{len(rounds) + 1:03d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        for index in range(0, len(pending), batch_size):
            path = round_dir / f"batch_{index // batch_size + 1:03d}.jsonl"
            with path.open("w", encoding="utf-8") as handle:
                for item_id in pending[index: index + batch_size]:
                    handle.write(json.dumps(items[item_id], ensure_ascii=False) + "\n")
        manifest = {"items": {item_id: source_sha(items[item_id]) for item_id in pending}}
        (round_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"items": items, "pending": pending, "round": round_dir}


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def quote_verified(quote: object, source_text: object) -> bool:
    quote_norm = _norm(quote).strip(" .\"'")
    return len(quote_norm.split()) >= 3 and quote_norm in _norm(source_text)


def apply_decisions(links: pd.DataFrame, out_dir: Path, items: dict[str, dict] | None = None) -> tuple[pd.DataFrame, dict]:
    """Fold verified agent decisions, then reviewer decisions, into the links.

    ``items`` are the current queue items (from :func:`write_queue`); an agent
    decision applies only when it was made on the same text. Reviewer
    decisions (``adjudication/reviewer_decisions.jsonl``) are final and apply
    to any linked pair, queued or not.
    """
    folder = out_dir / "adjudication"
    items = items if items is not None else {}
    decided = load_rounds(folder)

    links = links.copy()
    for column in (
        "adjudication_status", "adjudication_match", "adjudication_tier", "adjudication_reason",
        "adjudication_quote", "adjudication_quote_verified", "final_tier",
    ):
        links[column] = links[column].astype(object)
    if "reviewer_decision" not in links.columns:
        links["reviewer_decision"] = ""
    links["reviewer_decision"] = links["reviewer_decision"].astype(object)
    counts = {
        "queued": len(items), "decided": 0, "reused_from_earlier_round": 0, "verified": 0, "unverified": 0,
        "confirmed": 0, "rejected": 0, "capped_to_tier3": 0, "pending": 0,
        "reviewer_decisions": 0, "reviewer_decisions_not_linked": 0,
    }
    latest_round = round_dirs(folder)[-1].name if round_dirs(folder) else None
    for index, link in links.iterrows():
        item_id = f"{link['Record ID']}|{link['output_key']}"
        if item_id not in items:
            continue
        record = decided.get(item_id)
        if not record or record["sha"] != source_sha(items[item_id]):
            counts["pending"] += 1
            continue
        decision = record["decision"]
        counts["decided"] += 1
        if record["round"] != latest_round:
            counts["reused_from_earlier_round"] += 1
        verified = quote_verified(decision.get("evidence_quote"), items[item_id]["source_text"])
        links.at[index, "adjudication_match"] = bool(decision.get("match"))
        links.at[index, "adjudication_tier"] = decision.get("tier") if decision.get("tier") is not None else ""
        links.at[index, "adjudication_reason"] = str(decision.get("reason") or "")
        links.at[index, "adjudication_quote"] = str(decision.get("evidence_quote") or "")
        links.at[index, "adjudication_quote_verified"] = verified
        if not verified:
            counts["unverified"] += 1
            links.at[index, "adjudication_status"] = "quote_not_verified"
            continue
        counts["verified"] += 1
        links.at[index, "adjudication_status"] = "adjudicated"
        if not decision.get("match"):
            counts["rejected"] += 1
            links.at[index, "final_tier"] = ""
            continue
        tier = decision.get("tier")
        tier = 3 if tier not in (2, 3) else int(tier)
        if tier == 2 and str(link.get("statement_type", "none")) == "none":
            tier = 3
            counts["capped_to_tier3"] += 1
        counts["confirmed"] += 1
        links.at[index, "final_tier"] = tier

    reviewer_path = folder / "reviewer_decisions.jsonl"
    reviewer = {str(d["item_id"]): d for d in read_jsonl(reviewer_path)} if reviewer_path.exists() else {}
    linked_ids = set(links["Record ID"].astype(str) + "|" + links["output_key"].astype(str)) if len(links) else set()
    for item_id, decision in reviewer.items():
        if item_id not in linked_ids:
            counts["reviewer_decisions_not_linked"] += 1
            continue
        record_id, output_key = item_id.split("|", 1)
        mask = (links["Record ID"].astype(str) == record_id) & (links["output_key"] == output_key)
        final = decision.get("final_tier")
        links.loc[mask, "final_tier"] = int(final) if final in (1, 2, 3) else ""
        links.loc[mask, "adjudication_status"] = "reviewer_decision"
        links.loc[mask, "reviewer_decision"] = (
            f"{decision.get('decision', '')} by {decision.get('reviewer', '')} on {decision.get('date', '')}: "
            f"{decision.get('note', '')}"
        )
        counts["reviewer_decisions"] += 1
    return links, counts
