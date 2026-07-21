# Frozen GPT-5.5 cross-model classification release

This directory contains the canonical stored GPT-5.5 classification output used
for formal cross-model evidence and validation inputs.

`gpt55_classifications.csv` is the frozen canonical GPT-5.5 classification
artefact for the retained 1,308-record population. It was recovered from the
original run output and preserved byte-for-byte; it was not reconstructed,
regenerated or edited.

The original recovered run output remains at
`analysis/outputs/gpt55_classifications.csv`. The release copy is the formal
canonical source; the two files have the same 920,480 bytes and SHA-256
`5bb4379174e1c9b9cf7faf611712c53648bc57eea7ba1d28127ecedab16b5ded`.
The path-specific `.gitattributes` rule disables text and EOL conversion for the
release CSV so its UTF-8 BOM, CRLF record terminators, and embedded LF bytes are
preserved exactly.

The absent 1,309-row restricted intermediate used temporarily during excluded-
pilot review is not a formal study artefact, is not reconstructed here, and is
not used by formal sampling, coding, validation or analysis. No direct
provisional-versus-canonical equivalence claim is made.

Machine-readable provenance and validation details are in
`release_receipt.json`; the checksum sidecar supports direct byte verification.

