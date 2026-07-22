# Taxonomy, prompt, and production model

This folder is for taxonomy dictionary 1.0-rc2 / ontology v3.4-rc2, the exact
rendered `dict-1.0-rc2` production prompt, Fable 5 configuration metadata, and
the 1,308-record production classification output. It must not contain API keys,
caches with sensitive metadata, exploratory model outputs, or prospective human
labels. These pre-existing artefacts are expected to be frozen. The taxonomy,
configuration metadata, and classification CSV exist. A standalone byte-exact
rendering of the frozen static prompt is stored at
`production_prompt_dict-1.0-rc2.txt`; its SHA-256 is
`8fd34b5e80a748dce114ebe636d9861662c4cd8d3f0ce053ef458b95d9593861`.

`production_release_manifest.yaml` is the machine-readable Phase 3 release
record. It ties the source, cleaning code and rulings, cleaned population,
taxonomy, classifier/prompt implementation, production output, run metadata,
pre-existing evidence and exact exclusions to repository-relative paths and
SHA-256 hashes. The source repository convention is reference-based until final
package assembly, so these authoritative files have not been duplicated here.
The production release is frozen for Phase 3; protocol, REDCap and teaching
materials remain outside this freeze.
