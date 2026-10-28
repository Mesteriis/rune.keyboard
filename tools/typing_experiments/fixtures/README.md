# Disclosed context-ranking regressions

`context_ranker_regressions_20261026.jsonl` freezes the 35 raw top-1 regressions of the rejected unified-context experiment. These are regression checks only. Do not use them as training examples or as independent qualification data.

The sentence fragments come from the official Russian Tatoeba **CC0** subset; typed corruptions are synthetic. Sentence IDs, normalized sentence hashes, and original split IDs are retained in each row. Dataset/source-lock details and limitations are documented in [the preceding experiment](../../../docs/acceptance/2026-10-26-context-feature-ranking.md). Tatoeba's [download documentation](https://tatoeba.org/en/downloads) describes the CC0 subset.

The previously correct raw winner used packaged model SHA-256 `a917f63010b23cbb3ff06f8069460398b366bce389f70d61f77ad5c156783dcb` plus its frozen character score. The rejected 108-feature unified model SHA-256 was `99fe30f45b068002b9c3c4b591001c676f75612e0d949407da7275e70f82e310`. These are candidate-ranking regressions, not 35 observed incorrect automatic editor replacements.

`conversation_supervised_false_proposals_20261026.json` references five incorrect proposals from a later, separately frozen audit of the directly conversation-trained model. It retains only dictionary-word corruption/target/proposal triples, source sentence/contributor references and context hashes; sentence context remains in the ignored local experiment archive. Source sentences came from Tatoeba's CC BY 2.0 FR detailed export and were evaluation data only. These cases are likewise forbidden for training or independent requalification. Exclude their `sourceSentence` IDs when constructing subsequent data; resolve context hashes through the preserved source manifest when needed.

On 2026-10-26 the owner explicitly authorized learning from the disclosed conversational audit and lowering required proposal precision to 95%. The separate `conversation-supervised95-20261026` experiment therefore promotes that audit's original 4,000 contexts (including the five referenced errors) to training. This overrides their regression-only designation for that training run, with provenance retained; they cannot qualify that run independently. The earlier experiments and their recorded failures are unchanged. The 35 older regressions remain excluded from training. See [the follow-up training record](../../../docs/acceptance/2026-10-26-conversation-ranking-95.md).


The current [source and exclusion audit](../../../docs/acceptance/2026-10-28-q2-disclosure-tools.md)
verifies all 35 CC0 source rows and all five detailed-source references against
the pinned original data, without model execution. Their known source identities
are already covered by the durable exclusion registry. The five-case historical
training exception applies to the recorded original 4,000-context training run;
it does not authorize reuse as independent qualification.
