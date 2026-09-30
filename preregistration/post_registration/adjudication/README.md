# DEA adjudication materials

Materials for the structured two-stage adjudication in protocol §9: the
REDCap instrument, the code that generates, masks, preserves and reveals it,
the rule reference adjudicators cite, and the primary adjudicator's
declaration. The adjudication diagnoses the sources of selected classification
disagreements and informs, but does not replace, the preregistered release and
revision process.

* [primary_adjudicator_declaration.md](primary_adjudicator_declaration.md) is
  the §9.1 record of the primary adjudicator's identity, development role and
  conflicts, committed before adjudication began.
* [reference/taxonomy_rule_reference.md](reference/taxonomy_rule_reference.md)
  sets out the frozen taxonomy's rules under the IDs the instrument cites.
* [precommitments.csv](precommitments.csv) holds SHA-256 hashes of internal
  analysis commitments and memos that are withheld for now, so that the date
  each was fixed can be checked once it is released.
* [prototype/](prototype/README.md) holds the REDCap data dictionary and
  data-quality rules, the generators for the masked record and reveal imports,
  the per-block preservation check, the secondary audit draw, and their tests.

No formal case content, source mapping, coder response or owner response is
kept here. Record-level inputs and outputs live in the git-ignored
`preregistration_restricted/` folder.
