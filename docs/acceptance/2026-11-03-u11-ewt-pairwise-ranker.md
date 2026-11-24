# U11: experimental English ranking on disclosed EWT candidates

The preceding model-free replay produced 186 EWT annotated single-edit cases.
The intended source form appeared in the full candidate pool for 89. It was
visible in the collapsed strip for 88 and was the first non-original suggestion
for 77. These figures describe this filtered, already disclosed corpus and its
unverified annotations; they do not measure natural typing quality. They show
that, on this slice, the main limitation is not a candidate being present but
hidden beyond the visible strip.

A separate, offline pairwise linear ranker was trained using six numerical
features already emitted by the real English candidate generator. It does not
call the model, change the product, or make an automatic-admission decision.
The generator's existing full-alternative order is the comparison baseline;
that order is not always the same as the visible strip order. Exact corrected
word forms occurring in training are excluded from development; the test
partition also excludes exact words seen in development. This does not prove
morphological-family separation.

Only groups where the labelled target appears among at least two English
candidates are scored. There were 51 training groups, nine development groups,
and five test groups after this filtering. A fixed three-choice epoch sweep
selected 25 epochs using development only; a tie would have kept the baseline.
The selected ranker placed the labelled target first in 9/9 development groups,
versus 5/9 for the existing full-pool order. On the test groups both ranked it
first in 4/5. All five test groups came from searches that exhausted the state
budget. Therefore their pool is incomplete and none supplies evidence for
allowing automatic replacement. The small post-hoc sample, lack of independently
verified correct-word/name controls and prior exposure preclude a precision or
quality claim. This candidate is not suitable for promotion.

The [aggregate receipt](2026-11-03-u11-ewt-pairwise-ranker.json) records the
fitted numerical weights, counts, source/registry bindings and explicit
non-qualification. It contains no input text or candidate words. Two independent
training runs produced identical receipts from a replay whose projection matched
the previously registered candidate contexts. Five host tests cover target
separation, deterministic training, dev-only selection, malformed inputs and
receipt bindings. The label-free replay and host-only labels were recreated in
private temporary build directories and removed after the experiment. No
product model, APK, keyboard setting or phone was changed. U11 and Q6 remain
open for broader training, labelled safety controls and independent acceptance.
