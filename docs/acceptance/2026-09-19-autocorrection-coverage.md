# Autocorrection coverage and product-admission replay — 2026-09-19

> Historical material from 2026-09-19. The original body is retained.
> Its source, model and device claims are not fresh acceptance. Current scope
> and outstanding evidence are in the [review completion map](../plans/2026-10-27-review-completion.md).

This change fixes two independent causes of missed Russian corrections: cold
packaged-lexicon validation exceeded the Space grace period, and the morphology
admission guard revoked winners that had already passed the separately qualified
general-local policy. The guard still vetoes a source form present in the public
morphology dictionary. Reviewed finite confusions retain exact source, target,
case, and packaged-membership checks.

The packaged fast path validates the frozen manifest identity, exact asset
regions, read-only mappings, headers, counts, and root bounds. Exhaustive hashing
and structural traversal remain in the build/qualification validator. On the
physical Fold, the Russian packed lexicon loaded in 2.65 ms and canonical-case
data in 3.49 ms; the previous exhaustive runtime path took about 4.7 s for the
Russian lexicon alone. These are individual observed runs, not latency percentiles.

## Product-policy replay

The distance-one replay now compiles every current controller dependency, binds
all 12 trie/length/rank/case assets plus `ru.morph`, installs the real
`AutoCorrectionAdmissionGuard`, and records whether every local winner was
applied or rejected for a specific admission reason. An unexplained admission
veto or change fails the gate.

Reproduction:

```sh
python3 tools/eval/smart-typing-0.3/pipeline/evaluate_distance_one_policy.py \
  --output build/smart-typing-0.3/local-distance-one-current-20260919-goal7
```

The frozen 12,000-row corpus produced `releaseApproved=true`:

| Split / language | Automatic | Correct | Precision | Admission vetoes | Unexpected vetoes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Calibration RU | 356 | 354 | 99.438% | 5 | 0 |
| Holdout RU | 360 | 360 | 100% | 4 | 0 |
| Calibration ES | 330 | 328 | 99.394% | 0 | 0 |
| Holdout ES | 342 | 341 | 99.708% | 0 | 0 |

Every RU admission veto was `ORIGINAL_VALID`. Original availability, exact Undo,
and protected-token checks had zero failures. English general-local replacement
remains unqualified and disabled.

Report SHA-256:
`4068c0607e8fd5e8af583adbfb2d08abe5bd356aa2faffe676dcd3dc825aa45a`.
Evidence SHA-256:
`d079c6925640529a401924009656ccda01615726c59bd1de69c516a8985122e7`.
The bound report and evidence are ignored build artifacts, not repository inputs.

## Device verification

The debug app and test APK were installed on the connected Fold. A real keyboard
tap/Space scenario corrected `смотруть`, `ощющениям`, `заберай`, `пвременить`,
`ерминатор`, and `спаателей` in one editor session, retained `ность`, and produced
no editor readback. Packaged asset validation, canonical-case correction/Undo,
JVM tests, runtime tests, lint, release assembly, dependency boundaries, and the
98-test Python pipeline passed.

The current APK was subsequently replayed on the same Fold and an API 37 emulator
after enabling sentence punctuation correction for pure Cyrillic words. The live
IME changed `смотруть.` to `смотреть.` and the first Backspace restored exactly
`смотруть`; six live candidate/Undo tests passed on both devices. ASCII tokens
before `.` or `:` remain protected so a future hostname or URI scheme is not
silently changed.

No historical dogfood totals were available on the connected Fold: the transient
test APK had been removed, and quality collection correctly remains opt-in and off
by default. The next build now records a separate numeric `MANUAL_RETYPE` event only
when a user changes an owned word and the changed word is successfully committed.
It stores no text, does not treat the edit as proof of a missed correction, and is
shown beside automatic applications and explicit Undo counts. The quality file was
bumped to schema 2; schema-1 files retain all seven prior counters and initialize
the appended retype counter to zero.

## Limits

The original corpus is public, frozen, and previously revealed. It is useful
regression evidence but not a blind estimate of natural-message accuracy. The
device run is a bounded scenario on one phone, not long-term dogfood evidence.
On-device training is limited to the compact personal typo-pattern policy; the
full LLM remains inference-only.

## Compact-ranker promotion experiment

The shipped compact Russian ranker and compact context model were replayed as an
additive policy only after the current product policy abstained. Calibration and
holdout are separate commands: calibration freezes the evaluator, model hashes,
admission rule, score threshold, and margin threshold before a holdout can be
opened. The evaluator rejects a candidate if it adds one incorrect replacement,
changes one correct/protected control, reduces precision, or does not add enough
correct replacements.

The first candidate was correctly rejected on the original holdout after adding
137 correct replacements and one incorrect control replacement. A generic
structural guard removed that failure and produced 134/134 correct additions on
the already revealed holdout; that is regression evidence, not independent
validation. The revised frozen policy was then evaluated unchanged on the
source-disjoint qualification-v4 Russian holdout:

| Policy | Automatic | Correct | Incorrect | Control changes | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current active | 327 | 325 | 2 | 1 | 99.388% |
| Candidate additions | 114 | 112 | 2 | 1 | 98.246% |
| Proposed total | 441 | 437 | 4 | 2 | 99.093% |

The candidate increased useful coverage but also introduced two errors, so the
promotion decision is `promotionApproved=false`, `rollbackRequired=true`. The
evaluation command exits with status 1. The active product policy is unchanged.
The frozen policy SHA-256 is
`5da5ff920414de7852b904073772650d89200db9eddfce0ca6611c91e2152f2d`;
the bound v4 decision report SHA-256 is
`80a530798a53e68c7255f1c1d5d04822b8a2dad81c6a1b87e39de65650788939`.
Both are ignored build evidence rather than product inputs.

A second, more conservative candidate additionally required the existing strict
automatic-admission check. It passed calibration and the qualification-v4
regression replay, but failed the other frozen holdout with 22 correct additions
and one incorrect addition. It was also rejected, and the remaining external
corpus was deliberately left unopened for a future retrained model. Threshold
tuning of the current compact ranker is therefore not a shippable path.

The next ranker was trained with the original word as an explicit abstention
candidate. Its model and thresholds were frozen before qualification-v3 was
opened. On that external holdout the current policy remained 347/347, while the
candidate added 159 correct and two incorrect replacements (`кармн` was changed
to `карман` instead of `кармен`; `миеля` to `мишеля` instead of `мигеля`). The
gate again returned `promotionApproved=false` and `rollbackRequired=true`, so the
candidate was not activated. These failures show that retrieval for rare
names/forms, rather than threshold tuning alone, is now the limiting step. The
frozen policy SHA-256 is
`0533d443bdb8da61e715a217c54839d3c26b1d57bb408a32edc13cad0f3beea1`;
the rejected decision report SHA-256 is
`d80e15fb2d3a7e79e1e03bfad114709bd56691682a5b0db3e63d101b8ef1206a`.

The next candidate added exact unit-edit retrieval over the public morphology
dictionary and a public rare-name supplement extracted from Wikipedia shards
`ru-0007` through `ru-0009`. Its frozen policy SHA-256 is
`d6fb70d119dc68381dd8fd9140f7a761b88bac76b7a2bd08aeee1834e6ebe467`.
It replayed 630/630 correct on qualification-v3 after that corpus had already
influenced the retrieval design, so that result was recorded only as regression
evidence.

A new independent holdout was then frozen from public shard `ru-0011` before
any replay. It contains 1,000 typo rows and 700 correct-word controls from
92,622 articles. The generator excluded 18,669 word families found in the
training data and all prior spelling corpora. Labels stayed in Python; the
Kotlin controller received only row identity, split, language, prefix, and typed
text. The replay completed all 1,700 rows with the model explicitly unavailable
and zero LLM calls.

| Policy | Automatic | Correct | Incorrect | Control changes | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current active | 385 | 381 | 4 | 3 | 98.961% |
| Candidate additions | 254 | 253 | 1 | 0 | 99.606% |
| Proposed total | 639 | 634 | 5 | 3 | 99.218% |

The sole new error was `стапом -> старом`, while the observed target was
`старпом`. Because incorrect changes increased from four to five, the gate
returned `promotionApproved=false` and `rollbackRequired=true`. The candidate
remains inactive even though aggregate precision increased. This is the exact
test-and-rollback behavior required for both global and personal candidates.
The frozen holdout manifest SHA-256 is
`cde8f78c6ada31a25bdc835295014232d64df6de61c199d4e9467cb9a58d4d4d`;
the bound decision report SHA-256 is
`63252eefaab4e6fa1a5b2b785dcb97dcefa9c48d64942c99f0705fcdcfc77a26`.
This holdout is now disclosed calibration evidence and cannot qualify a future
candidate.

## Qualified public additive policy

The rejected candidate was recalibrated only on the now-disclosed v3 and v6
evidence. Its model stayed unchanged; the frozen abstention margin increased
from `0.31024187176059387` to `0.42795266413380256`. The resulting policy was
frozen before opening a new source- and family-disjoint holdout from public
Wikipedia shard `ru-0012`. That v7 holdout contains 1,000 typo rows and 700
correct-word controls from 92,622 articles and excludes all earlier evidence.

The unchanged frozen policy passed the independent replay:

| Policy | Automatic | Correct | Incorrect | Control changes | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current active | 339 | 338 | 1 | 1 | 99.705% |
| Qualified additions | 244 | 244 | 0 | 0 | 100% |
| Proposed total | 583 | 582 | 1 | 1 | 99.828% |

The policy is integrated as a separate additive candidate pool, so it cannot
change a decision already made by the existing local policy. A replay compiled
from the current Kotlin product sources reproduced the same 244 additions
exactly and preserved every baseline decision. The product gate returned
`promotionApproved=true`, `rollbackRequired=false`.

On the host JVM, full token generation over all 1,700 rows measured p50
0.200 ms, p95 2.448 ms, and max 11.708 ms. For the 731 rows that exercised the
expanded candidate pool it measured p50 1.519 ms, p95 2.806 ms, and max
11.708 ms. A separate warmed product-path benchmark on the physical Fold measured
the complete packaged generation plus public morphology/rare augmentation and
frozen compact decision over 100 runs of five qualified probes: p50 32.607 ms,
p95 57.637 ms, and max 60.807 ms. Generation alone was p50 29.915 ms and p95
56.725 ms; the compact decision was p50 1.081 ms and p95 2.714 ms. The probe set
is bounded synthetic regression evidence, not a population latency estimate.

The frozen policy SHA-256 is
`826b7954e838479b94ef5f8fcc3194f4794d40d34bb0bc41ec435a3efdab76c0`;
the v7 holdout manifest SHA-256 is
`dec91ada74a0da141d988837a09cf7b4c58249fdf4d2903c3c270b497da147d8`;
the current product decision report SHA-256 is
`bb3fa97ca53604aa7ff12cd3559ef8a6e37500e4b33cd289660d69002a6afa21`.
The holdout and reports are ignored build evidence, not repository inputs.

## Retrained additive policy v2

The ranker was subsequently retrained on the disclosed public v2-v7 evidence;
the original candidate, context model, retrieval dictionaries, and zero-new-error
promotion rule remained unchanged. The first new source- and family-disjoint
holdout from `ru-0013` rejected that candidate: it added 287 correct changes but
also changed `лнчем` to `линчем` where the observed target was `ланчем`. The
candidate was not packaged. Its margin was raised strictly above that disclosed
error and the recalibrated policy retained 240/240, 240/240, and 270/270
zero-error additions on the disclosed v6, v7, and v8 evidence respectively.

The next `ru-0014` replay initially appeared to reject the policy for changing
`колько` to `сколько`. Source inspection showed that the Wikipedia text actually
contained the mixed-script token `Cколько`: the corpus generator had split the
Latin `C` from the Cyrillic suffix and incorrectly labelled the suffix as a
standalone correct-word control. The qualification generator now rejects
language-specific matches adjacent to another alphabetic code point. The v9
result was not reclassified as an approval and was not used to promote the
candidate.

With the model and thresholds still frozen, a final independent holdout was
created from `ru-0015` using the corrected generator. It contains 1,000 synthetic
typos and 700 correct-word controls from 92,622 articles and excludes every
previous spelling family. The current Kotlin product path produced:

| Policy | Automatic | Correct | Incorrect | Control changes | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Existing local policy | 352 | 351 | 1 | 1 | 99.716% |
| Legacy-first compact cascade | 249 | 249 | 0 | 0 | 100% |
| Proposed total | 601 | 600 | 1 | 1 | 99.834% |

The retrained model by itself selected 246 correct rows, but abstained on three
correct rows selected by the already-qualified model. It was therefore not
shipped as a direct replacement. The product instead runs the qualified v1
stage first and consults v2 only when v1 abstains. The source-bound cascade
gate verified all 245 v1 selections byte-for-byte, then accepted four additional
v2 selections, all correct. It returned `promotionApproved=true` and
`rollbackRequired=false`; the negative regression test returns rollback if even
one prior selection disappears or changes. Host generation over all 1,700 rows
measured p50 0.275 ms and p95 2.385 ms; rows selected by the cascade measured
p50 1.225 ms and p95 2.202 ms. These host timings are regression measurements,
not device-population latency.

The retrained RET2 ranker SHA-256 is
`f4b0737515abc6855b7354ddaf0d1b349be98b5d7b80587cc94f1c0c1bc576ec`;
the retained v1 RET2 ranker SHA-256 is
`eb466bcabc4ea1cfac493422fa814386bdff02dc9c04c48bd66a9d8a25a11bcd`;
the frozen cascade policy SHA-256 is
`17679935c58c939dd864367a81c9144058f658c5c465eb57d64867c31f43e979`;
the v10 holdout manifest SHA-256 is
`da4de280ef2f469565551ba83e8f158d05a6ba2b2e825a45637cdf0d0ef084c6`;
and the source-bound product decision report SHA-256 is
`7b20c2a9aa5b5df3cc4268112afe00c4f9d431cd58e584a024814718570377f6`.

## Minimal-pair rollback and independent v12 qualification

The next independent source- and family-disjoint holdout, from `ru-0016`,
demonstrated the rollback path instead of approving the cascade. The existing
local policy changed 350 rows with 349 correct and one incorrect; the compact
cascade added 256 changes with 255 correct and one incorrect. The new compact
error was `грйсон -> грейсон`, while the observed target was `грэйсон`. Both
ranker stages preferred the wrong `е` candidate with a large margin. The gate
returned `promotionApproved=false` and `rollbackRequired=true`, and the phone
build was returned to manual-only compact suggestions before the policy was
revised.

Policy v4 adds a narrow stage-winner guard: it abstains only when the winner has
an unresolved one-character Russian `е`/`э` minimal-pair rival. It does not
abstain merely because an unrelated pair exists elsewhere in the candidate
list. Replaying the disclosed v11 evidence after this change preserved the
baseline and produced 255/255 correct compact additions with no control changes.

The guard and all thresholds were then frozen before preparing v12 from the
next shard, `20231101.ru/train/0017.parquet`. That holdout contains 1,000
synthetic typos and 700 correct-word controls from 92,622 articles, excludes all
previous spelling families, and was not used to tune the policy. Both the
proposal-only shadow replay and the actual qualified Kotlin product path
returned the same result:

| Policy | Automatic | Correct | Incorrect | Control changes | Precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| Existing local policy | 343 | 343 | 0 | 0 | 100% |
| Guarded compact additions | 262 | 262 | 0 | 0 | 100% |
| Qualified product total | 605 | 605 | 0 | 0 | 100% |

The actual mutation replay returned `promotionApproved=true` and
`rollbackRequired=false`. On the host, all decisions measured p50 0.237 ms and
p95 2.314 ms; compact-selected rows measured p50 1.114 ms and p95 2.054 ms.
These are bounded regression timings, not a device-population latency claim.

The frozen v4 policy SHA-256 is
`5057e9e955fafdc507e06b4b1e88307b4dd2201d6864a9620b39e23358a33acd`;
the v12 holdout manifest SHA-256 is
`b755fb65c73cf764782759cc7eea62bdaafe8882c7156af52aee990bc2b3fce2`;
the holdout rows SHA-256 is
`95c0f40915241ef72e5bc7bcc1dd484e5aafcee691b32cb31d1e983b012d8fa2`;
the product observations SHA-256 is
`1b3252eec2de950888bbad8ed5f633ee9995c902506d9017c77763d40ac5e204`;
and the product decision report SHA-256 is
`9356ad00f231176aad1ff8097c18177a7d73923b30ba0b99fe57398e2fcf5de2`.

## On-device learning safety contract

On-device work is limited to a small personal residual ranker. The 396 MB GGUF
remains inference-only: fine-tuning it on the phone would exceed the measured
memory, CPU, heat, and validation budget of an input method.

Each training run must follow this state machine:

1. Snapshot only explicit, learning-eligible feedback and make a deterministic
   train/holdout split. Held-out examples never enter training.
2. Train into a new `candidate` slot while the current `active` slot continues
   serving. Freeze hashes for the evidence snapshot, trainer, evaluator, base
   model, and candidate before validation.
3. Replay `active` and `candidate` over the same holdout. Promotion requires
   more correct decisions, no additional incorrect decisions, no additional
   correct/protected-token changes, no precision decrease, and a minimum sample
   count. Missing, cancelled, corrupt, or thermally interrupted evaluation is a
   refusal, never a pass.
4. Atomically rotate `candidate -> active` and `active -> rollback` only after
   the decision is durably committed. Keep exactly one last-known-good rollback
   slot. A crash must resolve to either the old or the new complete pointer,
   never a partially written model.
5. Run the promoted model in shadow/canary mode against subsequent explicit
   feedback. A statistically qualified increase in undo/rejection or a
   correctness/control regression atomically restores `rollback`; the failed
   candidate is quarantined and cannot be reactivated under the same identity.

The Android job may start only while charging, device-idle, battery-not-low,
storage-not-low, inside the fixed 01:00–05:00 local night window, and below the thermal
limit. Every condition is rechecked during training and validation. Losing a
condition cancels the candidate and leaves `active` untouched. Private training
state belongs under `noBackupFilesDir`; raw examples remain opt-in and never
leave the device.

## Implemented personal-learning promotion gate

The local typo-pattern learner now follows the staged rule instead of applying
a pattern as soon as three examples accumulate. New explicit feedback updates
only a candidate policy. The active policy is compared against that candidate
on the deterministic one-fifth holdout, row by row. Promotion requires at least
20 evaluated rows, including ten correction rows and five identity controls,
at least one improvement, zero newly wrong rows, zero identity regressions, a
strict net improvement, and a complete uncancelled evaluation. Insufficient
data is a refusal, not a pass.

After a pass, the exact evaluated snapshot is written atomically before it can
become active. The prior active policy is retained as the single rollback slot.
A stale snapshot or failed/partial commit cannot activate the candidate. The
binary store remains backward compatible: legacy data is imported as the
already-active baseline, while all subsequent evidence is staged.

The non-persisted `JobScheduler` wrapper is now enabled only when both explicit
example collection and typo-pattern learning are enabled. Android additionally
requires charging, device idle, battery not low, and storage not low. The worker
rechecks local time, charging state, battery level, idle state, allocatable
storage, and thermal state before evaluation, during replay, and immediately
before a commit. Losing a condition cancels or reschedules the run without
publishing the candidate.

Before evaluating a new candidate, the nightly worker also replays the current
active policy against its retained rollback policy. A complete sufficiently
large canary result containing a new regression atomically restores the exact
evaluated rollback slot. New evidence arriving during either evaluation makes
the snapshot stale and prevents both promotion and rollback. The one-shot job
schedules the next local-night window after a completed run and is restored by
the keyboard or settings after a reboot, without adding a boot permission.
Manual evaluation in Learning Lab uses the same candidate gate.
Full GGUF/LLM fine-tuning remains out of scope for the phone.

API 26 and API 37 emulator instrumentation tests verified that the framework registers
exactly one non-persisted learning job with charging, device-idle,
battery-not-low, and storage-not-low constraints, and that disabling learning
removes it. The runtime night and thermal checks remain enforced inside the
worker because `JobScheduler` has no corresponding constraint for them.
