# Named-example acceptance triage

Read-only follow-up at `6f7c35eda1ee11a9f0a510eadadd0fbf2912356c`, 2026-09-06. The original final integration review is unchanged. Sources inspected: `PackedTopSeven`, `CandidateGenerator`, `PrefixDistance`, `CandidateLexicon`/shared search control, weighted Damerau-Levenshtein profiles, specification sections 13/14/24, and the existing `replay-calibration-ready.jsonl` named rows. No test, build, device, model, network or implementation work was performed.

## Assessment

**These outcomes expose incomplete named-example product acceptance, but do not establish an incorrect search implementation or unsafe correction.** They must be reported explicitly; aggregate precision does not establish named-example recall. A 95% precision requirement measures correctness of changes made and permits abstention. It does not establish that a requested target was retrieved, suggested, or automatically applied.

The section 24 arrows are concrete intended demonstrations. They cannot all be marked PASS at this source. Section 14 simultaneously requires qualified confidence and preserves Original when confidence is insufficient; it does not authorize forcing an automatic replacement merely because its input appears in the named examples. “All kinds of typos” is not a safe basis for bypassing this rule.

| Existing observation | Interpretation |
| --- | --- |
| `автокрекция`: 8192 states, zero verified alternatives, exhausted | Safe bounded-search abstention; named `автокоррекция` retrieval/demo remains unfulfilled. No model decision is possible without a candidate. |
| `correcion`: exhausted; `correction`, `correcto`, `correctos`, missing `corrección` | Safe partial suggestions and automatic veto. The specifically allowed suggestion/auto target is not demonstrated. This is retrieval coverage, not a confidence-threshold failure. |
| `teh`: COMPLETE top three `ten`, `eh`, `tea`, missing `the` | Concrete candidate-policy recall gap before the model. Radius 1 includes a single transposition; the target is displaced by the current weighted cost-first width-three selection. COMPLETE certifies that comparator's requested top-N, not semantic recall. |
| `арфография`, `recieve`, `adress`: correct target suggested, no automatic replacement | Retrieval succeeds. Conservative automatic abstention is permitted by the confidence contract. Report suggestion-only; do not claim the automatic arrows passed. |
| `сообшение`, `mensage`: correct automatic replacement | Positive automatic examples in these exact replay contexts, not evidence about every context or installed editor. |
| `причём`, `kubectl`, `AIGate`: unchanged | Positive preservation examples in these exact contexts. |

## Source grounding

- `PackedTopSeven.kt:44` sets UNIT radius 1 for short words and 2 otherwise. A neighboring-character swap is within UNIT radius 1. `WeightedDamerauLevenshtein.kt:12` deliberately sets INITIAL transposition cost to five quarter-units, while ordinary insertion/deletion costs four and adjacent substitution costs three. This is a documented feature policy, not an arithmetic error.
- `CandidateGenerator.kt:247` sorts first by INITIAL weighted edit cost, then language prior, frequency and deterministic ties. `PackedTopSeven.kt:83` stops with a complete global-order certificate after the requested width. The production width is three alternatives (`CalibratedSpellingPolicy.MAXIMUM_ALTERNATIVES`). Frequency/model evidence cannot recover a candidate excluded at this stage.
- `PackedTopSeven.kt:48` retains exhausted status while returning only verified partial alternatives. `CandidateGeneration.prohibitsAutoReplace` retains the exhaustion veto. The observed RU/ES behavior follows that contract. Their rows alone do not prove an unsound lower bound or omitted eligible branch; no such bug was established by this source inspection.

## Smallest bounded general remedy to consider

There is **no justified one-line threshold/cost/budget change that fixes all three retrieval misses while retaining current qualification**. Do not hardcode the words, lower the transposition weight to make this example win, increase the 8192/64 caps, or relabel partial results COMPLETE.

The smallest focused improvement for the demonstrated `teh` mechanism is a **generic adjacent-transposition suggestion lane**: enumerate at most length-minus-one unequal adjacent scalar swaps; perform existing exact membership checks on routed dictionaries; independently verify accepted candidates; share the same total state/terminal budget and cancellation control. Define an explicit deterministic candidate-diversity rule that can retain a verified swap within the existing bounded output, rather than sorting it away again under the unchanged cost-first comparator. This is a retrieval-policy change, not a correction exception. It should first be suggestion-only, with the existing qualified automatic candidate path left intact. It would address an edit class, not promise every transposition's target or all typo types.

The exhausted RU/ES cases need a separate search-efficiency investigation. A conservative first experiment is query-directed/deeper-prefix ordering only among frontier regions with equal existing lower-bound/prior keys, preserving the complete covering frontier, existing certificate and shared budgets. Such scheduling can find useful terminals earlier without falsely certifying them, but **this review cannot claim it retrieves these targets or improves global recall**. If it does not, an offline bounded edit/deletion index is a larger general design option, not a small fix justified by these three rows alone.

Any diversity policy, additional candidate source or changed returned set needs frozen source/candidate identity, general edit-class and negative coverage, and evaluation under the unchanged 95%/false-change gates before extending automatic qualification. Current revealed-data results remain development evidence; changing retrieval must not silently inherit old candidate-set qualification. Neither proposed direction was implemented or measured here.

## Required reporting outcome

Keep formal completion open and record the three missing targets as explicit retrieval limitations. Record the three suggestion-only outcomes separately from automatic success. The original integration review's lack of a demonstrated blocking code regression stands; it must not be interpreted as completion of these named product examples. If satisfying every named arrow is a hard release requirement, these unmet demonstrations are an additional product acceptance blocker until improved or explicitly revised by the user.
