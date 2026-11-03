"""Link DEA-accredited register projects to their public outputs.

The package searches free bibliographic sources (OpenAlex, CORE, Europe PMC,
UKRI Gateway to Research, GOV.UK and Semantic Scholar for enrichment), caches
every raw response under ``data/publication_linkage_cache/``, and assigns each
project--output pair an evidence tier:

* Tier 1 (explicit): the output quotes the register Project ID, confirmed by an
  author or dataset match.
* Tier 2 (strong): accreditation route or secure-environment statement, a
  register researcher among the authors, a register dataset named, and a
  publication date inside the window.
* Tier 3 (probable): author, dataset and date match without a statement.

Absence of a findable output is not evidence that a project produced none.
"""
