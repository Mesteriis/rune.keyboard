# Named acceptance examples — current frozen controller outcomes

**Incomplete product demonstrations: three requested targets are absent.** This report projects the already retained final controller replay; it performs no new inference, typing replay, threshold adjustment or policy change. Every exact occurrence of the eleven named tokens is included, in every language and both model-ready/unavailable modes. All17 unique examples happen to belong to the frozen calibration corpus; they are not unseen holdout results or physical editor observations. The source-file and per-line SHA256 bindings allow comparison to the complete row-evidence archive.

| Language / named input | Exact ready-mode outcome in the retained context |
| --- | --- |
| RU автокрекция → автокоррекция | Missing target:8192 states exhausted, zero verified alternatives |
| RU арфография → орфография | Correct target shown as suggestion; no automatic replacement |
| RU сообшение → сообщение | Correct automatic replacement, exact Undo |
| RU причём, kubectl, AIGate | Preserved; also preserved in the EN/ES corpus copies |
| EN teh → the | Missing target: certified cost-first top3 are ten/eh/tea; the is outside the returned set |
| EN recieve → receive | Correct target shown as suggestion; no automatic replacement |
| EN adress → address | Correct target shown as suggestion; no automatic replacement |
| ES mensage → mensaje | Correct automatic replacement, exact Undo |
| ES correcion → corrección | Missing target:8192 states exhausted; partial suggestions omit corrección |

Ready-mode totals:2 correct automatic typo replacements,3 correct suggestions without automatic replacement,3 missing requested typo targets,9 preservation examples. Unavailable-mode totals:5 correct suggestions without automatic replacement,3 missing targets,9 preservation examples. No incorrect automatic change occurs in this named selection. This is not a substitute for the full false-positive and coverage reports: the complete ready/unavailable calibration/holdout reproduction, including its false changes, remains under `2026-09-06-final-controller-replay`.

A complete requested-width certificate proves the retrieval comparator's order, not semantic recall. Exhausted searches correctly prohibit AutoReplace. Lowering confidence thresholds cannot recover an absent candidate, and forcing the named words would bypass the qualification contract. Independent source triage finds a product retrieval limitation, not a demonstrated radius/certificate or safety regression. The automatic arrows and the specific ES suggestion cannot all be marked PASS. Separate general retrieval experiments must retain existing evidence and undergo appropriate evaluation before extending automatic qualification.

`named-rows.jsonl` records exact authored prefixes, current model admission, returned/displayed alternatives, resulting text, search status/budgets and Undo evidence. Protected rows with no actual candidate request retain null generation metadata. The initial projection's null-request assumption failed before writing outputs; its extractor and a reporting note are preserved. To reproduce the projection, restore the final extract.py to `build/smart-typing-0.3/named-acceptance-20260906/extract.py` with the bound source archive restored to its listed build path, then run it. This changes no product state.

Other requested families (mixed scripts, valid words, hostname/camelCase, accents and punctuation) retain their full corpus and Binder evidence elsewhere. A consolidated actual installed-build demonstration of every named case remains separate; these host records do not close it.
