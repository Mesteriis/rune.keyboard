# Q6: rejected unmanifested conversation preparation

Audited all 29,162 observed JSONL rows in the original rejected conversation
preparation: train 22,558, calibration 3,308, holdout 3,296. The directory has no
manifest, and the retained failure log records CONTEXT_SPLIT_OVERLAP. Neither
absence nor that log proves historical timing or actual model consumption.
No manifest is manufactured and this artifact is not qualified retrospectively.

The audit verifies each source ID and normalized full-sentence hash against the
frozen CC0 Tatoeba split and compressed public source. It then verifies the
actual source word/prefix capture, original selection hash and derivation of the
typo or correct/protected control. Strict row fields reject additional text or
non-numeric historical family metadata. The archived bounded-prefix generator
is loaded by its pinned hash; the rejected producer is not executed. Native
family IDs are not canonical lemmas. Dictionary-only analyses recover all
source-word families, with zero unresolved rows in this artifact.

Source article and sentence keys were already excluded. Two lexical gaps
remained: 25 prepared-train families and 740 unique contexts (missing per split:
460/154/164, with overlap). Added a family-only prepared-training-quarantine
usage, distinct from proven supervision, and a context-only historical usage.
The default new-sentences preparation profile blocks quarantined families;
all profiles block historical contexts. Existing 80 entries, bindings and
global incomplete coverage are preserved. Re-audit reports no missing lexical
article/sentence/context/family exclusions for these three files. This status
does not certify control-ledger completeness or global Q6 completion.

The aborted follow-on directory currently has zero JSONL files; its receipt
states an intentional stop before data freeze/scoring. This is an observation
of available artifacts, not proof that no earlier material ever existed.
Owner-authored metadata declares 120 rows, but public-source origin remains
unestablished. Those rows and their private corpus fingerprints are not imported.

All 145 tests pass in a fresh isolated source-only directory, without original
build corpora, models or morphology packages. Both ledger schemas validate and
remain incomplete. Tests cover source capture and tampering, derived controls
and typos, preservation of prior entries, scoped quarantine, cross-source
context reuse, durable registry snapshots, and a real preparation CLI rejection
of a quarantined family without creating output. CI now includes the audit
tests; no remote CI run is claimed. The full source audit separately used the
pinned dictionary and frozen public source, with exit code 0 and no model calls.

Evidence and exact commands are in the adjacent evidence JSON. Remaining Q6
work includes owner-authored provenance, remaining historical inventory and
generator/source chains, and canonical families for the previously quarantined
unsupported public targets. No model fitting, APK update or Fold operation was
performed.

## Exact replay and control exclusions for the rejected corpus

The original v1 [preparer](../../tools/typing_experiments/historical_provenance_sources/conversation_supervised_v1_preparer.py)
was recovered from the literal creation command. The replay used the
verified CC0 Tatoeba split, historical vocabulary and packed morphology,
and the same 33 prior bindings as the later v2 run. Six unavailable raw
prior files used their existing hash-verified registry projections. The
selection and serialization stages wrote all three original v1 row files.
The original guard again threw `CONTEXT_SPLIT_OVERLAP` before writing a
manifest. All three files matched the original SHA-256 values in the
adjacent audit evidence, covering 29,162 rows. The replay made zero model calls.

The [registration command](../../tools/typing_experiments/register_rejected_conversation_controls.py)
verifies the recovered source and all three row-file digests before
projecting the control ledger. It added three entries while preserving every
previous entry.

| Entry | Exact contexts | Surface keys | Tatoeba sentence keys |
| --- | ---: | ---: | ---: |
| Protected controls | 5,359 | 3,261 | 0 |
| Regressions | 23,657 | 19,008 | 0 |
| Source | 0 | 0 | 5,414 |

Rerunning the command without `--output` compared the three registered
entries for exact equality. The tests cover conflicting contexts, cross-context
surface reuse, source-sentence reuse, changed row bytes and unexpected
manifests. The new entries contain hashes. The recovered row files were
temporary, and the historical dataset remains rejected. Both registries
still report incomplete global coverage.

The canonical digest of the three ordered entries is
`3f8e7d260e8a00644e28c7a16e56480faf816adb78e1f1c374a1ab75c2d5f983`.
The source-only test checks it after the recovered row files are removed.
