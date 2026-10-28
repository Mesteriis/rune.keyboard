# Historical model project-source identities

This archive preserves 29 exact historical project-source versions recovered
from the local Git object database. Their original relative paths, SHA-256
identities and Git blob IDs are recorded in manifest.json. Project source retains
the repository's existing license; this inventory introduces no new license.

The other 41 unchanged source/asset versions are referenced in the repository
and hash-checked rather than duplicated here. One original all-rows input is
reconstructed by concatenating the three byte-identical public refinement row
partitions from historical-data-v1. No archived code is imported or executed by
the auditor.

word-data-manifest.json is the original public Wikipedia-derived word-ranking
manifest. Its source revision, file hashes, original preparation-script hash and
license metadata are preserved. No article text or model weights are included
in this archive. Original Wikipedia source terms and dataset provenance are
in tools/model/rune-text-0.2/WIKIMEDIA_NOTICE.md and source-lock.json.

The direct project-source graph for two original candidate exports is covered.
External compiler/JDK/Android runtime references are inventoried by basename and
hash only; their historical availability/execution is not established. This is
not transitive source closure, candidate-generation reproduction, training,
quality qualification or completion of the remaining historical CI tests.

Commands from the repository root:

    python3 tools/ci/historical_model_sources.py
    python3 tools/ci/historical_model_sources.py --verify-git
    python3 tools/ci/historical_model_sources.py --historical-build PATH_TO_ORIGINAL_BUILD

The Git check needs the original blobs in local history and compares all 29
archived payloads byte for byte. Shallow CI checkouts use the archived bytes;
they do not need the historical object database. The optional build check binds
the original receipts and verifies all 12 advertised export files without
publishing their machine-local paths or logs.
