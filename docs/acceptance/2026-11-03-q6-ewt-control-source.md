# Q6: EWT source identities in the control registry

The disclosed English Web Treebank (EWT) source was already represented in the
lexical ledger, but the control registry could not represent a source-only
entry or parse an EWT document ID. The control registry now accepts a strictly
validated `source` entry: it must have no control-context or surface keys and
must contain document keys. EWT document keys use exactly the existing lexical
namespace. Tatoeba and Wikipedia identity calculations are unchanged.

A new control entry mirrors the 1,174 document keys in the existing pinned EWT
lexical entry, which covers 16,622 disclosed source rows. All prior 54 control
entries and the incomplete-coverage declaration are preserved; the lexical
ledger is unchanged. The entry carries hashes only, not source text or raw
document IDs. The registration pins the exact original lexical entry and its
source lock, importer and source-identity bindings. The historical lexical
helper was recovered byte-for-byte from Git revision `a5dd9d3c` and retained
alongside the registration-time control helper.

The pinned train/dev/test EWT files were independently re-read locally. Across
all 16,622 rows, the current control and lexical document-key sets matched the
1,174 keys in the retained lexical entry exactly. A real EWT source row was
rejected by the control article gate; preflight reported both control and lexical
article overlap and lexical sentence overlap. English lexical-family
qualification remains explicitly unsupported and both ledgers remain incomplete;
this does not approve a holdout or change a model.

The archived historical control validator rejects the newer source-only entry.
For old checks only, the historical runner first verifies the complete live EWT
registration, then removes exactly that entry from a temporary ledger copy;
all other entries and the live ledger are retained. It uses the archived helper
versions and rejects malformed or unverified source entries. A first registration
attempt identified a historical lexical-helper hash mismatch; recovering the
original helper resolved it without changing the parent entry. Two final
registrations matched byte for byte. No raw EWT text or document IDs were added.

Final validation: the standard-library profile passed 828 tests in 169 modules
with zero failures, errors or skips; receipt SHA-256
`133c3177eb8b518f25f7cc3cfbd539a9552432d88d1fb482565dae72e5e01e54`.
Four EWT registration tests and four historical-runner tests passed; these
include parent and registered-key mutation, archived-helper mutation, source
projection and verification ordering. The control, preflight and EWT importer
modules passed 10, 24 and two tests. The original EWT registration and old
historical checks also passed from a staged source archive without `build/`.
The unchanged three recent historical source-token registrations passed. The
first source-only test failed on the old EWT parser as expected; the old schema
also refused the new entry before the temporary projection was introduced.
Hosted CI and the scientific profile were not rerun for this source-gate slice.
