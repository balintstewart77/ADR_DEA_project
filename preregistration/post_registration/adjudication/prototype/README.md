# Offline synthetic adjudication prototype

Status: candidate, offline-checked, **not REDCap-import-tested**. This package
contains invented `SYN_ADJ_*` material only. It has no network/API client,
credentials, production classification path, or fallback to a formal input.

Run from the repository root with Python 3:

```powershell
python preregistration/post_registration/adjudication/prototype/scripts/build_assets.py
python -m unittest discover -s preregistration/post_registration/adjudication/prototype/tests -v
python preregistration/post_registration/adjudication/prototype/scripts/run_workflow_demo.py
Start-Process preregistration/post_registration/adjudication/prototype/preview/index.html
```

`instruments/adjudication_stage1_candidate.csv` uses the repository REDCap CSV
header convention, but is only a candidate dictionary. Neutral interpretation
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
exist. It carries the generator's read-only evidence: neutral slot maps, label
and tag-status membership, and observed differences derived from displayed
candidates alone. It contains no source identity, route, count or reveal
material, and generation fails rather than truncating if a package needs a
fifth slot or carries an input QA flag.

The intended configuration is one case–reviewer assignment per record, with
Stage 1 and Stage 2 as distinct instruments and a repeating linked finding
structure outside this minimum dictionary. REDCap cannot encode all dynamic
membership/slot choices in a static CSV; the generator supplies read-only maps
and the local validator enforces cross-field compatibility. Non-production
REDCap import, branching, requiredness, locking, DAG isolation, export/import
logging and accounts remain untested operational dependencies.

The preview is a review surface, not a security boundary. It is generated from
masked synthetic packages and contains no reveal mapping. Reveal payloads are
separate local files and are only returned by the simulation after preservation.
