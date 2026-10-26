# Experimental Russian typing model attribution

The numeric model weights in this directory derive from Russian Wikipedia text by Wikipedia contributors, via the public Wikimedia Wikipedia dataset snapshot 20231101 (wikimedia/wikipedia revision a634f78b1c435397c07001e175fa74cc4ad5e775).

Source dataset: https://huggingface.co/datasets/wikimedia/wikipedia
Original works: https://ru.wikipedia.org/

Source corpus metadata declares CC-BY-SA-3.0 and GFDL-1.3. These derived model weights are distributed under Creative Commons Attribution-ShareAlike 3.0 Unported: https://creativecommons.org/licenses/by-sa/3.0/ . The full CC-BY-SA-3.0 license is already packaged at smarttyping/lexicon/notices/OpenCorpora-CC-BY-SA-3.0.txt.

Changes by Rune contributors: public corpus selection, synthetic typo examples, deterministic neural and CatBoost training, compact numeric export. Aggregate evaluation, exact source identities and asset SHA-256 values are in provenance.json; reproducible training is in tools/typing_experiments in the Rune source repository. No private messages or touch events were used in training. The frozen additive Russian autocorrection policy identified in provenance.json is qualified only for its documented spelling scope. The remaining model components are experimental and do not establish general chat or touch accuracy.

`ru-joint-ranker.bin` uses the same attribution and CC-BY-SA-3.0 license. Its independent short-word and conservative long-word qualifications, rejected policies, exact hashes and remaining errors are recorded in `joint-correction-provenance.json`.

`ru-joint-rescue-ranker.bin` uses the same attribution and CC-BY-SA-3.0 license. Its separate long-word acquisition qualification and unchanged original-word protections are recorded in `joint-rescue-provenance.json`; its exact frozen policy is `ru-joint-rescue-policy.json`.

The unified contextual model `ru-contextual-ranker.bin` and its Wikipedia count table `ru-wiki.ctx` retain the Wikipedia contributor attribution and CC BY-SA 3.0 license above. The grammatical index `ru-context.gram` derives from OpenCorpora 0.92 / revision 417150 under CC BY-SA 3.0 (https://opencorpora.org/); dictionary-only analyses, including the pinned analyzer's е/ё alternatives, are projected to compact grammatical tags with ambiguity retained. The license text is packaged at `smarttyping/lexicon/notices/OpenCorpora-CC-BY-SA-3.0.txt`.

The conversational count table `ru-conversation.ctx` derives only from the official Russian Tatoeba CC0 training subset (https://downloads.tatoeba.org/exports/per_language/rus/rus_sentences_CC0.tsv.bz2). The unified model also trained on owner-authorized promoted contexts from the official Russian Tatoeba detailed export under CC BY 2.0 FR (https://tatoeba.org/en/downloads). Sentence/contributor attribution, source links, license and the synthetic-corruption adaptation description are in `contextual-tatoeba-attribution.json`. Raw source sentences are not packaged. Model policy, hashes and evaluation provenance are in `contextual-provenance.json` and `ru-contextual-policy.json`. The combined derived model is distributed under CC BY-SA 3.0 with the original Tatoeba attribution retained.
