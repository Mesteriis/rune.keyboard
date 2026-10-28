# Q2: truthful local-learning consent and storage disclosure

The English/Russian summaries for personal learning, example collection and typo
patterns now disclose the stored words, phrase fragments, hashes, counts and
flags. Personal phrases are learned from committed ordinary words as well as
corrections. Typo-pattern learning can retain hash-only records while raw-example
collection is off; both switches must be disabled to stop new evidence. Existing
raw words remain until reset. Hashes are deterministic deduplication keys, not
encryption or anonymization.

The privacy policy and guide list the two private no-backup files, fields, bounds
and separate reset controls. Personal reset clears its profile and tap data;
Learning lab reset clears its evidence and active/rollback pattern policies.
Neither disabling a switch nor removing one confirmed word erases the other
records. Password/incognito exclusions are described using the already verified
U3 policy. Storage, default switches, qualification and ranking are unchanged.
The architecture also corrects its obsolete model-call and scheduler claims;
CHANGELOG records this under Unreleased without changing release metadata.

## Source-bound checks

`python3 tools/check_learning_disclosures.py` checks seven source data structures
and their field-specific guide rows, eight codec/model limits, both locale copies
for all three switches and the lab description, file paths and separate reset
instructions. Reviewed encoder/writePolicy bodies are bound too: a newly written
computed value must not bypass the constructor-field inventory. Writer changes,
including formatting-only edits, require renewed review of that bound schema.
This checker is intentionally scoped to these two stores, not every persistent
file in the app.

Twelve mutation/regression tests pass on Python 3.12 and 3.14. They reject a new
field, an unmentioned row field, extra computed serialization, changed storage
limits (including a misleading underscored numeric prefix), a missing locale
phrase disclosure, omitted ordinary-typing/hash-only collection disclosures,
missing reset separation and invalid source. Both checker and tests are wired
into the stdlib CI job; the workflow parses. Hosted CI was not run.

All 1,355 app JVM tests pass with zero failures/errors/skips. Debug/test APK
compilation, lint and the IME architecture boundary pass. Two actual API 26 native
tests pass with zero skips. They exercise 12 attached consent rows: three switches
× EN/RU × 1.0/1.3 font scale at 320 dp. Every summary wraps without clipping or
ellipsis, and its complete text reaches the native checkable Switch label.
This is component/node evidence, not a full TalkBack navigation claim.

The two initial native attempts failed because an unattached View did not provide
a populated accessibility node. The corrected fixture uses a real attached dialog
in the settings activity, with attachment/traversal completed before the node is
read. These failures are retained and are not counted as product passes. The
owned emulator is stopped/deleted; the Fold was not used.

The guide had pre-existing owner edits. Only this task's new privacy section and
intro correction are staged; the older owner hunks remain pending. Removing the
task section reconstructs their exact original bytes. The other four pending
payload hashes and all 98 original paths are preserved.

## Integration and remaining Q2 scope

Source commit `fca5874` passes the architecture, release/profile privacy and APK
footprint gates in a separate tracked-clean checkout, offline. Source cleanliness
passes before and after. The release APK is 180,104,897 bytes compressed and
182,211,461 bytes unpacked, within the reviewed budgets. No signing material was
copied. The source disclosure command and all 12 Python tests also pass in that
clean checkout without the pending owner guide hunks. Exact integration and
artifact/log identities are in the adjacent receipt. Q2 stays in progress: complete source-cascade
ordering, remaining feature-count/schema/experiment documentation, asset NOTICE
coverage, provenance/README path closure and current
F-Droid scanner-policy acceptance remain. This privacy slice does not establish
whole-review, source-export or distribution acceptance.
