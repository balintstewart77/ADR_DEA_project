# Training and pilot

This folder contains the preserved training-session materials, the formal-
coding revisions, and the pilot/debrief references used to define the final
training/pilot exclusions. It must not contain personal contact information,
reserve IDs, or blinded assignments. The public exclusion list is v8.

Materials delivered for the 17 July 2026 shared training session are preserved
without alteration:

- `DEA_coder_training_handout_v2.docx`;
- `DEA_trainer_handout_v1.docx`; and
- `DEA_pilot_projects_trainer_debrief_reference.docx`.

The corresponding post-training formal-coding candidates are:

- `DEA_coder_training_handout_v3.docx`;
- `DEA_trainer_handout_v2.docx`; and
- `DEA_pilot_projects_trainer_debrief_reference_v2.docx`.

The formal-coding versions add Scratch Coder choice 4, `Cannot assess from
register entry`, and consolidate taxonomy-issue codes to 1, 2, and 5. They do
not alter domain, purpose, COVID, equity, sample, or exclusion rules. The two
decisions and their pilot/formal-coding impacts are recorded in
`pilot_feedback_log_20260717.md`. The pilot was launched under
`redcap-candidate-0.3`; candidate 0.4 applies only after pilot export/archive,
repository validation, and live runtime QA.

Exact membership is checked offline with
`scripts/verify_training_exclusion_membership.py`. It parses the designated
worked-example, discussion, pilot, and trainer exclusion-summary sections of
the DOCX files and requires exact equality with v8: 11 keyed worked examples,
one unkeyed discussion case, and ten pilot records (22 unique clean Record
IDs). The current verified P4, P7, and T1 IDs are respectively `2025/039`,
`2025/251`, and `2021/113`.

`training_material_record_manifest.csv` provides one row per unique exclusion,
including semicolon-delimited repeated card appearances, material role, keyed
status, document sections and exclusion status. It has exactly 22 rows and is a
verified working candidate pending the post-pilot freeze; creating it does not
freeze or alter the coder, trainer or pilot documents.

The exact-membership checker also enforces the protocol-authoritative REDCap
blinding description: the visible assignment code is neutral and opaque,
whereas reviewer/source IDs and sampling metadata remain hidden. Repository
audit on 17 July found that this wording was not embedded in the preserved v2
coder handout despite an earlier README claim. The as-delivered file is not
silently overwritten; the wording is included and machine-checked in v3. The
protocol, teaching examples, answer content, taxonomy rules, and exact
22-record membership remain unchanged. The historical handouts remain the
as-delivered record, and the revised handouts remain working candidates pending
the formal-coding freeze.
