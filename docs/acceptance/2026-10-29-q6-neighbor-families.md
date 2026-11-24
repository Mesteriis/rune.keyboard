# Q6 historical neighbor target families

The 15,000 retained neighbor rows contain 2,500 distinct intended Russian words.
The pinned dictionary-only analyzer recognizes all 2,500. Every dictionary
analysis is retained: 2,503 family keys, including 93 absent from the previous
lexical registry. Numeric native family IDs were not treated as lemma names, and
no lemma was inferred for typo or protected variants. This is a conservative
dictionary projection of disclosed target words, not a claim about all text in
the source articles or independent model qualification.

The entry binds the original corpus/attribution fixture, parent registry entry,
helper sources and dictionary receipt. Two independent generations produced
byte-identical ledger and receipt. The resulting ledger SHA-256 is
`c6f435896c55c1e87a60c56eb6a6c3e10befd5492a2da8e1136041dc174141ce`;
the receipt SHA-256 is
`f79c2bd2b2ebba2619ff2d37852765dc6506cf9a8456ca30e48c26b9b7bef784`.
An actual source-derived family absent from the prior registry is rejected by
the updated gate, with the completeness check explicitly disabled for that
comparison. Existing entries and the incomplete-coverage declaration remain.

Two focused tests cover ambiguous analyses, unknown forms and invalid parent or
surface. The `--check` command verifies the stored key digest, parent and source
bindings without requiring the dictionary or `build/`; it does not rederive the
morphological analyses. The previous 5b50eee5 registry also passed the complete
stdlib inventory: 802 tests across 163 modules, no failures/errors/skips; its
receipt SHA-256 is `b57192c8ce01b4b28e3fd1ef844a8adfb432e355cb168f28b5a577214187f98a`.
The new family entry is separately tested; Q6 and full independent qualification
remain open.

## Partition independence recheck

On 2026-11-10 the retained corpus was checked with the hash-locked
Pymorphy3 2.0.6 dictionary-only backend. Each input file matched the original
manifest. All 2,500 distinct target words have at least one dictionary
analysis; all analyses were included. Article IDs, native numeric family IDs
and exact target words are pairwise disjoint between train, calibration and
holdout. Dictionary lemmas are disjoint between calibration and both other
partitions, but train and holdout share **one** lemma: `чёртов`, from train
`чертовым` and holdout `чёртовой`. The train/holdout portions therefore are
not family-disjoint under this dictionary's complete analysis, even though
the original native IDs are disjoint. This is not evidence that the overlap
changed any model output or the historical count; it limits the independence
claim of that historical quality evaluation.

The normalized lemma is already in the permanent neighbor-family exclusion
entry, so no registry edit is needed for this overlap. The live Pymorphy CI
backend suite now checks the complete corpus, requires the observed overlap
and the zero-overlap axes, and binds the corpus files. The hash-locked Python
3.12 backend gate passed all six required cases; six gate self-tests also
passed (their simulated failures and skips are expected refusal probes).
The temporary environment was removed. No model was trained or scored.

## Current-controller replay of disclosed holdout

On 2026-11-10 the 6,000 retained historical holdout rows were replayed through
the current model-free controller at `d6658c35` using the existing
`replay_joint_correction.py --mode current-product` driver. The input rows were
bound to original SHA-256 `e0a97cd39220a3887dfe2129f45c07db512e83e72a8c6f4b74ca3657d5928437`;
all observations completed and were matched by row ID. The expected spelling
is a historical label, not independently proofread user intent.

| Group | Rows | Changed at boundary | Exact labelled target | Changed to another text |
| --- | ---: | ---: | ---: | ---: |
| adjacent2 | 1,000 | 934 | 929 | 5 |
| adjacent3 | 1,000 | 920 | 906 | 14 |
| mixed2 | 1,000 | 797 | 753 | 44 |
| mixed3 | 1,000 | 807 | 787 | 20 |
| correct | 1,000 | 14 | 986 | 14 |
| protected | 1,000 | 0 | 1,000 | 0 |

For unchanged correct/protected rows, exact target means preservation rather
than a correction. All 14 changed correct controls differed only in case
(for example `норвегии` → `Норвегии`); they are not automatically classified
as false corrections. All 83 other changed typo rows differed from the
historical label, but some may be plausible alternatives in an ambiguous
prefix; this disclosed synthetic corpus cannot establish a population error
rate. All 3,472 changed boundaries returned to the exact pre-boundary text on
Backspace. A second complete controller replay again reported the same 14
case-only changes and 83 other label mismatches.

The six holdout rows belonging to the cross-partition lemma above comprised
four typos and two controls: the current controller produced the labelled
target for all four typos, preserved both controls and restored each changed
input on Backspace. This does not show how those rows behaved in the original
historical controller, whether training overlap caused their results, or how
the historical aggregate changes without them. This corpus remains disclosed
and cannot independently qualify an autocorrection policy. Temporary inputs,
compiled replay and output were removed after the checks.

## Observed-output exclusions

Two additional current-controller runs of all 6,000 rows at source `4ab02eda`
produced identical public output-context projections for 3,472 changed
boundaries. The source-bound projection is retained at
`tools/typing_experiments/neighbor-history-v1/current-observed-v1.jsonl`
(SHA-256 `e86ca9e774008dd43f8238278db14b46f081d90f9ff558ba5d54aa3fb70a68e8`).
It contains public Wikipedia-derived text covered by the adjacent corpus
attribution; the hashes in the registries are unsalted and are not anonymous.
The historical source ID and article are checked for each output; the fixture
is evidence of the observed outputs, not an assertion that each is correct.

Before registration the projected outputs included 107 new regression-control
contexts, 90 new lexical contexts and 67 new control surfaces. Both permanent
registries now bind and exclude all 3,472 observed rows. Two independent
registrations produced byte-identical files, retained every previous entry and
kept the incomplete-coverage flags unchanged. The source-bound registration
check and its mutation tests are wired into CI. A live negative control for the
observed `дневной` context is rejected by both ledgers. The registries and
preparation tests passed locally; this does not qualify the historical dataset
or establish that the outputs are correct. Temporary replay and registration
artifacts were removed; hosted CI was not run.

## Diagnostic breakdown of the 83 label mismatches

The 83 disclosed changed typo rows were rerun through the current model-free
controller at source `33756df7`. The source-bound analyzer
`tools/ci/audit_neighbor_ranking.py` checks the original row identities,
replay receipt, observed output, exact Undo and score/pool shapes. The recorded
projection is already registered as an exclusion; this is not independent
qualification or a policy comparison.

| Diagnostic | Rows |
| --- | ---: |
| Historical target in expanded joint search | 81 of 83 |
| Target passes the per-candidate joint admission probe | 61 of 81 |
| Target refused by that probe as `RIVAL_UNKNOWN` | 20 of 81 |
| Target has highest raw joint score, including the original token | 20 of 81 |
| Target has highest raw score and passes the per-candidate probe | 18 of 81 |
| Target score exceeds the selected candidate's raw score | 24 of 81 |
| Target appears in the actual edit's correction-generation alternatives | 34 of 83 |

These counters overlap and do not attribute the actual final decision: the
admission probe independently evaluates each candidate and raw scores do not
include all thresholds, other stages or the final controller decision. For
`дщевной`, the historical target `душевной` scored above `дневной` but the
hypothetical target probe returned `RIVAL_UNKNOWN`. For `мглокьм`,
`молотком` was also refused by that probe and scored below `молоком`. For
`пончалв`, `поначалу` was admitted and scored above the final `пончиков`,
showing why raw ranking alone is insufficient to explain the selected stage.
The surrounding source contexts indicate useful cases to investigate, but
labels and intent were not independently qualified. No policy, model or
threshold changed. Two focused analyzer tests passed locally and are CI-wired;
temporary replay and audit outputs were removed.

## Actual source and contextual-score probe

The 83 disclosed mismatch rows were replayed twice in current-product mode
with the host-only boundary observer and an explicitly enabled raw contextual
score probe. Both runs produced identical projections; each row's output
matched its registered observation and every changed row restored its exact
input on Backspace. Boundary events attributed 68 changes to
`CONTEXTUAL_RANKER`, 14 to `LOCAL_POLICY` and one to `JOINT_RESCUE`. The five
examples in the prior section were all attributed to `CONTEXTUAL_RANKER`.

The historical target appeared in the joint candidate pool in 81 cases and
the selected output appeared in all 83. In all 81 comparisons, the frozen
contextual scorer gave the selected output a strictly higher raw score than
the historical target; 32 differences were below 0.1. For all 68 changes
attributed to `CONTEXTUAL_RANKER`, the selected output was its highest-scoring
raw candidate. These post-hoc examples do not qualify a new threshold,
demonstrate an independent error rate or establish user intent. Unlike the
previous joint-score probe, these are scores from the actual contextual model.

The opt-in probe only changes host diagnostic output. With the probe off, a
two-pass 2,160-row current-product run was deterministic and matched its
frozen baseline with zero different rows. The replay argument and projection
tests passed locally. All temporary replay outputs were removed; no Android
APK or product policy was changed and hosted CI was not run.

## Contextual-choice ablation on the disclosed holdout

On 2026-11-10 the host replay compared the existing controller path with a
counterfactual that bypasses `ContextualCorrectionPolicy` while retaining the
other replay stages. Each mode ran twice over the same 6,000 disclosed
holdout rows and produced deterministic projections. The host-only opt-in
`--disable-contextual-choice` does not change the Android implementation.

| Typo group | Existing exact historical targets | Without contextual choice | Lost exact targets | Existing other changes | Without contextual choice |
| --- | ---: | ---: | ---: | ---: | ---: |
| adjacent2 | 929 | 732 | 197 | 5 | 0 |
| adjacent3 | 906 | 784 | 122 | 14 | 0 |
| mixed2 | 753 | 579 | 174 | 44 | 10 |
| mixed3 | 787 | 575 | 212 | 20 | 5 |
| Total | 3,375 | 2,670 | 705 | 83 | 15 |

On these disclosed synthetic labels, the counterfactual removes 68 changed
outputs that differ from the historical target but also loses 705 matches;
no new exact target was gained. Every different output in the ablation was the pre-boundary input, not a
new automatic replacement. The replay nevertheless exposed additional
contexts and they are registered as described below. Every changed boundary in
both modes restored the exact pre-boundary text on Backspace. A separate
1,000-row mixed2 repeat confirmed its row. This rejects a blanket contextual
bypass as a useful fix on this set; it does not estimate natural-language
accuracy or prove that an individual alternate was wrong.

With the option off, a two-pass 2,160-row product replay still matched the
frozen baseline with zero different rows. The replay argument/projection tests
passed; temporary replay artifacts were removed. No Android model, policy,
threshold or APK changed and hosted CI was not run.

A follow-up check found 78 rows with text changed during typing before the
boundary and, across all counterfactual output contexts, 38 control and 1,323
lexical context keys not already registered; no new control surface keys were
found. The two deterministic ablation runs' 6,000 public output contexts are
retained in `neighbor-history-v1/counterfactual-observed-v1.jsonl` (SHA-256
`8230c5b79776f0b7960d6e5bce54a6f71f06e4e5dfde1e87823a13caeae19697`) and
registered in both permanent ledgers. Two independent registrations were
byte-identical, preserving all previous entries and incomplete coverage flags.
The source-bound check, mutation refusal and actual new-context refusal tests
are CI-wired. These outputs inherit the adjacent public corpus attribution;
their unsalted hashes are not anonymous.
