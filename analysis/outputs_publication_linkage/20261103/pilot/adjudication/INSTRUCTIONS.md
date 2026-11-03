# Adjudication instructions

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
