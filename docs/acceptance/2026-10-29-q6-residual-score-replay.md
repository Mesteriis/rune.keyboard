# Q6 historical residual model score replay

`tools/typing_experiments/replay_historical_residual_scores.py` extends the
existing sampled residual-model reference checks to every retained training
vector for v9–v14. It compares the legacy scalar calculation, the residual
ranker's raw and bounded outputs, and the batch scorer in bounded memory blocks.
The model, plan, groups, weights, vectors and scorer-source hashes are checked
before and after; models remain unqualified. Its source SHA-256 is
`d9a19a3016a700751f4607d237651955e11bd27052b083d867c5762a15a9abc5`.

A focused stdlib guard test rejects outside output and optimized Python. The
full local comparison is running at this checkpoint; no all-model result is
claimed. It requires ignored historical build inputs and the scientific Python
environment, so CI runs the guard test rather than this replay. This calculation
is training-vector parity, not independent quality qualification.

The initial full run completed all 428,865 v9 vectors with zero differences,
then failed at v10: the driver incorrectly selected the 202-feature decoder for
the 221-feature model. No aggregate receipt was written. Its log SHA-256 is
`bcd02b9872a5efaa048e4168d98e1e734d29feb873139e87dac7f95920cf0c1d`.
The corrected driver selects the decoder by the frozen model width (202, 221 or
242) and verifies the additional decoder source identity. A separate 32-vector
smoke for each of the six actual models returned zero raw, bounded and batch
differences; all four existing guard tests pass. The corrected source SHA-256 is
`f9f283e5096e8b550b017109a553fe72d99af841262a0b2847196a95e8c0656d`.
A fresh complete corrected run is in progress; the smoke tests do not replace it.

## Completed corrected replay

The completed local replay compared six retained v9–v14 composite models on
all 2,858,290 recorded training candidate vectors. Per model, v9–v14 contained
428,865, 445,321, 473,067, 503,679, 503,679 and 503,679 rows. Feature widths
were respectively 202, 221, 242, 242, 242 and 242.

For every row the retained scalar tree evaluator, the composite decoder and
the batched evaluator agreed exactly on the raw score; the decoder's bounded
score also matched the independently calculated transform exactly. There were
no non-finite values. The driver checked each frozen record's model, plan,
group, vector and weight hashes and its applicable scorer-source hashes before
and after each model; each record declared the model unqualified.

The completed command exited 0 using
`tools/typing_experiments/replay_historical_residual_scores.py`; its ignored
local JSON receipt has SHA-256
`375ec66df6846bb30fdb7842cccdd216b1c576ee13701a029e65c7626f4dd810`.
A previous run terminated at v10 due to choosing a decoder by model name; the
corrected driver selects by the frozen feature width. This completed run is the
corrected run.

This checks score implementation parity on the retained **training** vectors;
it does not demonstrate independent model quality, complete transitive source
provenance, Android runtime parity or qualification. Q6 remains open.
