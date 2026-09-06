# Contextual calibration diagnosis — 2026-09-06

This is development evidence, **not a qualified policy or holdout result**.
The replay script pins the archived600 calibration inputs/scores and their
complete receipt. It does not open the held-out score cache. Authored contexts
repeat across five current words, so rows are not independent observations.

```sh
python3 tools/eval/smart-typing-0.3/pipeline/diagnose_contextual_calibration.py
```

Token averages can favor an added punctuation token simply because the negative
sum is divided by a larger count. For example, a total of−3 over2 tokens becomes
−1.5 and beats an original−2 over1 token, although its total probability is lower.
On the archived calibration, replacing averages with totals changes ES clear
precision from73/100 to97/97. Ambiguous suggestions remain too frequent with
totals alone. Requiring a total-score advantage over Original and the best rival
further reduces those suggestions in this development comparison.

| Diagnostic policy | EN correct/suggested clear; ambiguous suggestions | RU | ES |
| --- | --- | --- | --- |
| Current token average |100/100;88 |91/100;100 |73/100;100 |
| Total only |98/98;61 |86/91;79 |97/97;69 |
| Total, Original delta>0.5, rival delta≥4 |91/91;4 |54/54;5 |79/79;5 |

Each language has100 clear and100 ambiguous rows. The margins came from an
exploratory calibration-only grid, not a precommitted release protocol. No
product code, model bytes or frozen historical reports are modified by this
diagnostic. A separate development patch implements the two-margin policy;
it still requires a freeze and evaluation on a new unseen holdout. These
calibration numbers cannot qualify it. Score sums are over the same common-prefix
divergent-span contract, without generated text or new editor access.
