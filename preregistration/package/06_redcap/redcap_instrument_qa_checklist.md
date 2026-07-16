# REDCap instrument QA checklist

- [ ] Dictionary imports without unresolved warnings; form and field order are correct.
- [ ] Administrative, source, sampling, and model fields are absent from coder and owner displays.
- [ ] Coder sees only opaque assignment ID, title, datasets, and coding questions.
- [ ] Owner sees only permitted project information, proposed labels, and review questions.
- [ ] `@NONEOFTHEABOVE`, `@MAXCHECKED=2`, hidden, and read-only tags behave as intended.
- [ ] Branching and conditional-required fields behave correctly for every trigger.
- [ ] Desktop and mobile display, save-and-return (if enabled), and completion status work.
- [ ] Export matches `redcap_expected_export_schema.csv` with one row per assignment.
- [ ] Multiple owner responses remain separate but share the hidden project identifier.
- [ ] Prohibited-material declaration and accidental-exposure branch work.
- [ ] Capture dated import log and screenshots or PDF evidence in approved restricted storage.
- [ ] Delete synthetic data and confirm deletion before the excluded pilot.
