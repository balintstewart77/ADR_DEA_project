# Training and pilot

This folder contains the current coder and trainer training handouts and the
pilot/debrief reference used to define the final training/pilot exclusions. It
must not contain personal contact information, reserve IDs, or blinded
assignments. The training documents remain working candidates pending the
post-pilot freeze; the public exclusion list is v8.

Exact membership is checked offline with
`scripts/verify_training_exclusion_membership.py`. It parses the designated
worked-example, discussion, pilot, and trainer exclusion-summary sections of
the DOCX files and requires exact equality with v8: 11 keyed worked examples,
one unkeyed discussion case, and ten pilot records (22 unique clean Record
IDs). The current verified P4, P7, and T1 IDs are respectively `2025/039`,
`2025/251`, and `2021/113`.
