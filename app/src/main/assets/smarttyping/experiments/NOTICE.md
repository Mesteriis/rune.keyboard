# Experimental Russian typing model attribution

The numeric model weights in this directory derive from Russian Wikipedia text by Wikipedia contributors, via the public Wikimedia Wikipedia dataset snapshot 20231101 (wikimedia/wikipedia revision a634f78b1c435397c07001e175fa74cc4ad5e775).

Source dataset: https://huggingface.co/datasets/wikimedia/wikipedia
Original works: https://ru.wikipedia.org/

Source corpus metadata declares CC-BY-SA-3.0 and GFDL-1.3. These derived model weights are distributed under Creative Commons Attribution-ShareAlike 3.0 Unported: https://creativecommons.org/licenses/by-sa/3.0/ . The full CC-BY-SA-3.0 license is already packaged at smarttyping/lexicon/notices/OpenCorpora-CC-BY-SA-3.0.txt.

Changes by Rune contributors: public corpus selection, synthetic typo examples, deterministic neural and CatBoost training, compact numeric export. Aggregate evaluation, exact source identities and asset SHA-256 values are in provenance.json; reproducible training is in tools/typing_experiments in the Rune source repository. No private messages or touch events were used in training. The models are experimental and do not establish production spelling, chat or touch accuracy.
