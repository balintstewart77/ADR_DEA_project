# Live REDCap runtime QA record — blank template

Tester:  Not stored in Git
Test date:  16/07/2026
REDCap instance:  
REDCap version:  17.0.3
Test project identifier (store only where approved):  
Dictionary version and SHA-256:  c905e60f5908da48451c1135e7def57e9f0d9dc855f2553f61993f5282b160ac
Import warnings:  
Action-tag compatibility:  
Checkbox exclusivity result:  
Analytical Purposes maximum-selection test: PASS after correction.
    Initial annotation: @MAXCHOICE=2
    Corrected annotation: @MAXCHECKED=2
    Observed behaviour: third purpose could not remain selected.
    Repository candidate still requires the same correction before pilot use.
Unclear from register entry exclusivity:  PASS
    Research Domains: Unclear cannot coexist with substantive domains.
    Analytical Purposes: Unclear cannot coexist with substantive purposes.
    Tested in both selection orders.
Branching result:  PASS
Conditional-required-field result:  PASS
Hidden-field result:  
Coder user-rights result:  
Project-owner survey result:  
Mobile result:  
Desktop result:  
Synthetic assignment import result:  
Export test:  PASS
    Records exported: 5
    Unique assignment IDs: 5
    Rows per assignment: 1
    scratch_coder_complete present: Yes / No
    Hidden administrative fields retained in administrator export: Yes / No
    Unexpected duplicate rows: Yes / No
One-row-per-assignment result:  PASS
Multiple-owner-response result:  
Synthetic-data deletion confirmation:  
Defects found:  

Post-fix retests: PASS

Accidental exposure:
Record F4K8M2Q6
Dedicated exposure description populated.
Generic explanatory note blank.
Survey completed successfully.

Maximum two purposes:
Record G7N3R9T5
Exactly two purpose checkbox fields exported as selected.
No third purpose persisted.
Survey completed successfully.

Export architecture:
Seven records exported.
Seven unique assignment IDs.
One row per assignment.

Pilot readiness decision:
