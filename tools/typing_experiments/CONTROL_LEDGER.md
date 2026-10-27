# Historical punctuation and protected controls

`control-ledger.json` preserves public control exposure separately from lexical
article/family/window exclusions. Each SHA-256 key has a versioned control-kind
and language namespace. No foreign Wikipedia numeric IDs or protected-token
strings are inserted as Pymorph lemmas. This registry stores hashes and source
bindings, not source phrases, candidate strings or scores. Hashes are not a
privacy boundary; only pinned public corpus components are imported.

Punctuation identity uses language, NFC prefix and current word. Expected boundary
is validated but excluded from identity: relabeling a disclosed context cannot
make it fresh. Protected identity uses language, NFC prefix and exact typed token.
Case, punctuation, whitespace, identifiers and command syntax are preserved;
only canonically equivalent Unicode representations share an identity.

```sh
python3 tools/typing_experiments/control_ledger.py --validate-only
python3 tools/typing_experiments/control_ledger.py --rows proposed.jsonl --kind punctuation
python3 tools/typing_experiments/import_control_components.py --kind punctuation --output build/new-controls
# Append protected components using --kind protected --base EXISTING_CONTROL_LEDGER.
```

The importer pins the three historical corpus manifests and each component file.
It checks public/frozen flags, exact archived generator/source-lock bytes,
punctuation selection hashes and original labels. Protected rows must additionally
match the archived generator's complete authored matrix for each language.
Repeated component imports and malformed control flags/IDs/labels fail explicitly.
Existing entries and bindings are copied without alteration.

A known intersection fails as `CONTROL_OVERLAP:<kind>`. Unseen rows fail as
`CONTROL_COVERAGE_INCOMPLETE`: this registry alone cannot certify overall corpus
freshness. Empty inputs cannot pass. Use this alongside the lexical ledger;
neither replaces source/label/cohort/quality qualification. Current preparation
builders are not silently rewritten to invoke this gate. Versioned preparation
integration and remaining historical coverage are still pending.

These three corpora contain 3,600 punctuation rows (nine language/component
entries). The separate source-recovery process is required for article/window
exclusions. Unit checks and reading persisted keys need only the standard library;
no models, morphology package, PyArrow or Android device is required.
