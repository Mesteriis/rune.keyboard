# U11 English candidate-pool diagnostic

The disclosed Q7 regression corpus contains 180 English frequency-list source
surfaces, each with a deterministic middle-character deletion and a first
unequal adjacent transposition. All 360 transforms differ from their source
surface. These are constructed hypotheses, not verified typing mistakes: a
transformed spelling may itself be a valid word, and adjacent frequency-list
entries used as context are not natural sentences. The data is disclosed and
cannot serve as an independent holdout or estimate natural typing quality.

The retained product observation gives the following exact-string availability
(case-folded English target, within the recorded full-token alternatives):

| Measure | Deletion | Transposition |
| --- | ---: | ---: |
| Constructed transforms | 180 | 180 |
| Source surface present among alternatives | 87 | 107 |
| Present while search permits automatic replacement | 21 | 32 |
| Present but search prohibits automatic replacement | 66 | 75 |
| Source surface absent from recorded alternatives | 93 | 73 |

In 165/360 cases the search ended with `STATES_EXHAUSTED`; 55/360 were marked
`VALID_WORD`. Only 53/360 contained the constructed target in the recorded
alternatives and had `prohibitsAutoReplace=false`. This is an upper bound for
this particular recorded pool and search condition, not a prediction that 53
can be safely corrected: source qualification, admission, model calibration,
valid-word preservation, names and other guards remain separate. A ranker alone
cannot choose a target absent from the candidates supplied to it; changes to
search, search budgets or policy would require their own qualification.

The actual current-product replay was run twice over the 2,160-row multilingual
corpus. Both projections matched the retained baseline, with zero differing rows
and projection SHA-256
`e2f5b604d83eceb3d75cf75ec69f73e679ab847dfebdbf7ddc408b455c0cb0ea`.
The diagnostic validates the original generator and frozen baseline, checks row
and source-group alignment and transform identity, and records input/analyzer
hashes. Two runs were byte-identical; the [numeric receipt](2026-11-03-u11-english-candidate-ceiling.json)
has SHA-256 `08863bb1035cae6d42bdc5f01e5edb5ce9f1c6d93c46664ca35ca6264d9a8902`.
Three focused tests cover candidate versus search refusal and malformed or
misaligned inputs. The screen is CI-wired; hosted CI was not run. No model,
application or APK was changed, and U11 remains open for the in-process model,
separate calibration, independent holdout, Undo and Fold budgets.
