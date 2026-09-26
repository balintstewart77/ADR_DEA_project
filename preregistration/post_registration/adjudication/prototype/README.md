# Adjudication instrument and generators

The frozen adjudication instrument, as imported into REDCap for formal use:
`instruments/adjudication_stage1_candidate.csv` (SHA-256 `860d56bb…97ac`)
and `instruments/adjudication_data_quality_rules.csv` (`4c4f9f9f…2ede1`). The
dictionary carries two amendments made during the primary pass, neither
touching Stage 1: ADJ-078 added an optional notes box to each Stage 2 finding
(from ADJ_0011; before it, `52b63541…adc15305`), and ADJ-082 added mechanism
vocabulary mechvocab-0.2 to the mechanism dropdowns (from ADJ_0036; before it,
`66d9f3a4…8677706`). ADJ-084 then reworded only the release-implication note
(from ADJ_0051; before it, `5e9476fd…9d37`), and ADJ-086 added mechanism
vocabulary mechvocab-0.3 (from ADJ_0076; before it, `fbff7ef7…5189`).
"candidate" in the dictionary's name is historical. The fixtures are invented
`SYN_ADJ_*` material only, and nothing here has a network or API client or
credentials.

The scripts that read formal inputs (`build_route1_component.py`,
`build_formal_import.py`, `preserve_block.py`, `draw_secondary_audit.py`)
check pinned hashes, write only to the git-ignored `preregistration_restricted/`
folder, and print aggregates only.

Run from the repository root with Python 3:

```powershell
python preregistration/post_registration/adjudication/prototype/scripts/build_assets.py
python -m unittest discover -s preregistration/post_registration/adjudication/prototype/tests -v
python preregistration/post_registration/adjudication/prototype/scripts/run_workflow_demo.py
Start-Process preregistration/post_registration/adjudication/prototype/preview/index.html
```

The dictionary uses the repository REDCap CSV header convention. Neutral interpretation
slots 1–4 cover the maximum Fable-plus-three-coder complete sets before
duplicate collapse. The generator maps package-specific stable interpretation
IDs to those slots and must suppress unused slots; overflow is a QA failure, not
truncation. Static Domain/Purpose rows cover every frozen canonical label.

`adj_assignment_id` is deliberately the first field, because REDCap takes the
first field as the record identifier and that identifier appears in record
lists, URLs, logs and exports. The stable source Record ID stays a hidden field
for restricted joins.

`instruments/adjudication_record_import_synthetic.csv` is the matching
record-import file: one row per synthetic case–reviewer assignment, six rows in
all, split between the `primary` and `secondary` reviewer groups. Import it
**after** the dictionary, and only once data access groups with those two names
exist. It carries the generator's read-only evidence: the frozen title and
datasets-used entry, neutral slot maps, label and tag-status membership, and
observed differences derived from displayed candidates alone. It also carries
the hidden flags that gate the lean Stage 1 form, so a comparative record is
asked §9.2's judgements once, plus a blind best-supported choice for each
component that differs, and an owner-only single set gets its
per-label checks instead. It contains no source identity, route, count or reveal
material, and generation fails rather than truncating if a package needs a
fifth slot or carries an input QA flag.

The intended configuration is one case–reviewer assignment per record, with
Stage 1 and Stage 2 as distinct instruments and a repeating linked finding
structure outside this minimum dictionary. REDCap cannot encode all dynamic
membership/slot choices in a static CSV; the generator supplies read-only maps
and the local validator enforces cross-field compatibility, including at
preservation, before each block's reveal.

The preview is a review surface, not a security boundary. It is generated from
masked synthetic packages and contains no reveal mapping. Reveal payloads are
separate local files and are only returned by the simulation after preservation.
