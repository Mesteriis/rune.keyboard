# Smart Typing 0.3 — exact candidate-set widths, 2026-09-03

Baseline: `ab8029b729c1cc12d15c2b487b401ca0b08c19ca`. Production code and
version0.2.0 are unchanged. This slice evaluates a necessary choice before
ranking calibration; it does not enable automatic replacements.

## Requirement and experiment

The specification requires original plus **at most seven alternatives**, not
exactly seven. The current implementation always requests seven, which makes
its completion requirement more expensive than necessary. The plan also calls
for measuring model sets of2/4/8 candidates. We therefore compare exact top1,
top3 and top7 alternatives plus original, using the same production packed
reader, corpus, ranking order, language routing and limits8192/64.

Each width is fixed **before search**. The selector streams that many candidates
only after their exact global order is certified, or exhausts the frontier for
a shorter list. This never reclassifies an exhausted seven-alternative request
as complete: every exhausted request at its own declared width retains its veto.
The full-neighborhood oracle is truncated only to the independently declared
requested width, and verifier metadata must match it. Exact membership,
protected/valid-word policies and original preservation remain unchanged.

Host-only source overlays change the requested width and its proof label.
Compiled source/asset hashes, original sources, overlay paths and tool hashes
are recorded. The production export CLI has no source-override flag; its default
still compiles production sources. Explicit experimental identity is required
for the internal overlay API, which rejects unknown or out-of-repository paths.
Width8 control output is byte-identical to the previous production calibration.

## Calibration feasibility

All6000 public spelling calibration rows ran for every width, including1000
typo rows per language. Input files are byte-identical across runs. Values below
are **correct candidate present / correct candidate present with complete search**.
They are retrieval counts, not AutoReplace precision or passing quality gates.

| Total candidates, including original | EN | RU | ES |
| --- | ---: | ---: | ---: |
| 2 | 855 / 852 | 798 / 791 | 813 / 802 |
| 4 | 952 / 475 | 925 / 583 | 925 / 537 |
| 8 | 972 / 184 | 962 / 366 | 947 / 314 |

Width4 provides substantially more complete retrieval while retaining more
correct candidates than width2. This makes it a strong candidate for subsequent
combined-ranker calibration, rather than accepting the width8 completion ceiling.
The final choice remains subject to >=99% replacement precision, <=0.5%
correct/protected false changes, >=300 holdout replacements per language and
device/resource measurements. No threshold was fitted and no holdout was run.
Repeated corpus panels remain repeated observations; unique typed inputs per
language are1500/1500/1499, not6000 independent words.

Fresh full-neighborhood oracle comparisons:773 requests each, zero violations.

| Total width | Complete | Incomplete, veto retained | Policy |
| --- | ---: | ---: | ---: |
| 2 | 683 | 53 | 37 |
| 4 | 393 | 343 | 37 |
| 8 | 238 | 498 | 37 |

Complete sets match the full oracle's exact requested prefix; incomplete results
contain only valid verified representations. Malformed UTF-16 and explicit
cancellation controls remain outside this strict UTF-8 harness. Production JVM
coverage of those cases does not itself qualify every experimental width; the
parameterized production implementation still needs dedicated boundary tests.

## Radix reader feasibility

A separate host prototype reads the actual RDX1 assets, validates hash/header,
UTF-8, structure, lengths, terminal IDs and the decoded word-stream hash, then
evaluates every scalar within compressed edges with the unrestricted recurrence.
It retains the original exact-membership reader and all shared caps. No
certificate can occur inside an unfinished child-list/edge expansion.

It passed the773-request oracle (241 complete /495 incomplete /37 policy), but
lost24 previously complete calibration cases to verification exhaustion while
gaining22 from state exhaustion. Complete-correct counts EN175/RU371/ES316 do not
solve the EN bottleneck. The prototype is **not adopted**. Its full-path scratch
also adds1048832 bytes and keeps original mappings for membership/ranks; no
production memory, cold-load, CPU or battery improvement is claimed. New Kotlin
parser negative/cancellation matrices and Android qualification were not run for
this rejected trial. The offline converter's four tests are separate evidence.

## Validation and next step

Nine exporter tests, nine comparison/qualification tests and four converter
tests pass. Prescribed lint/build/privacy/dependency/native gates pass
(238 tasks,25 executed). No Android/model/energy run was performed in this slice.
The mandatory fresh post-commit JVM run is reported separately after commit.

Evidence: `tools/lexicon/smart-typing-0.3/top-seven/results/2026-09-03-candidate-widths/`
and `tools/lexicon/smart-typing-0.3/radix/results/2026-09-03-search-probe/`.
Next: support explicit requested width in the production generator/certificate,
retain the maximum of seven, qualify all widths and cancellation paths, then
calibrate deterministic/model-assisted decisions and measure device costs.
PR7 automatic replacement/Undo, PR9 contextual punctuation, physical Fold,
final quality/energy/release gates and model publication remain open.

Post-commit JVM follow-up: the fresh run after `03cea45` reported596 tests /1
failure in an existing duty-trace fixture. Root cause and atomic-clock correction
are documented in `2026-09-03-smart-typing-0.3-duty-trace-idle.md`; the initial
failure is preserved rather than reported as a passing run.
