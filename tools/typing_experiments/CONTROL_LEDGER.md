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

The protected component import adds all 5,400 authored matrix rows: nine
language/component entries, 600 rows each. Across v2-v4 these repeat 1,800 unique
protected identities. Every original row is compared with the exact archived
`protected_rows(language)` output, including categories, flags and candidates;
only then are its identity hashes registered. All punctuation entries/bindings
remain unchanged. The isolated snapshot test regenerates the entire protected
key set using only committed archived sources. This records historical control
exposure; it does not add a personal dictionary or change runtime protection.

Punctuation source articles are now stored as optional `articleKeys` on all nine
punctuation entries. Their identity includes language and canonical decimal
Wikipedia ID; foreign IDs are never mixed with the RU lexical namespace.
Recovery retains all matching eligible articles, using the exact archived
punctuation selector and original article hash/modulus filter. The 3,600 rows
map to 3,617 occurrences and 3,476 language-qualified articles (1,150 RU).
777 RU articles supplement the lexical article exclusions; 373 were already
covered. The lexical registry and its own overlap report are unchanged.

```sh
python3 tools/typing_experiments/recover_punctuation_articles.py scan \
  --corpus qualification-v2 --language ru --controls CONTROL_LEDGER \
  --output build/recovery/qualification-v2-ru
# Repeat for each of three corpus names and en/ru/es.
python3 tools/typing_experiments/recover_punctuation_articles.py merge \
  --base CONTROL_LEDGER --recovery-root build/recovery --output build/enriched-controls.json
```

Each scan saves an immutable copy of its input control registry. The merge
verifies all original inputs, identity hashes, row IDs/selections and complete
nine-group coverage before adding keys. Scanning requires PyArrow; reading keys,
namespace validation and tests do not. No source windows are guessed.

New versioned spelling/control finalizers now enforce both registries, including
the recovered article keys. See [PUBLIC_CORPUS_PREPARATION_V1.md](PUBLIC_CORPUS_PREPARATION_V1.md).
Current coverage blocks final output; no historical generator is rewritten.
