# Third-party notices

The root MIT License applies to Rune's original code and documentation. It does not replace the licenses of the following separately distributed components and assets.

| Material | License / authoritative notice | Source and modifications |
| --- | --- | --- |
| llama.cpp | [MIT](runtime-llama/src/main/cpp/llama.cpp/LICENSE) | Pinned [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) submodule; local JNI adapter and restricted build configuration |
| Material keyboard icons | [Apache-2.0](artwork/keyboard-icons/LICENSE) | [Source URLs and conversion notes](artwork/keyboard-icons/README.md) |
| Material menu icons | [Apache-2.0](artwork/menu-icons/README.md) | Source vectors converted to Android resources |
| English dictionary | [SCOWL copyright and component notices](app/src/main/assets/smarttyping/lexicon/notices/SCOWL-Copyright.txt) | Normalized and packed dictionary; includes the original WordNet/UKACD notices |
| Spanish dictionary | [Selected MPL-1.1 option](app/src/main/assets/smarttyping/lexicon/notices/ES-MPL-1.1.txt) | LibreOffice Spanish dictionary, normalized and packed; [attribution](app/src/main/assets/smarttyping/lexicon/notices/ES-README.txt) |
| Russian dictionary | [Alexander I. Lebedev terms](app/src/main/assets/smarttyping/lexicon/notices/RU-Lebedev.txt) | LibreOffice Russian dictionary, normalized and packed |
| Frequency data | [CC-BY-SA-4.0](app/src/main/assets/smarttyping/lexicon/notices/CC-BY-SA-4.0.txt) | Hermit Dave / FrequencyWords / OpenSubtitles2018; transformed into terminal ranks |
| Russian morphology | [CC-BY-SA-3.0](app/src/main/assets/smarttyping/lexicon/notices/OpenCorpora-CC-BY-SA-3.0.txt) | OpenCorpora-derived morphology; [pinned provenance](app/src/main/assets/smarttyping/lexicon/provenance/morphology-manifest.json) |
| Experimental ranking/context weights | [CC-BY-SA-3.0 and attribution](app/src/main/assets/smarttyping/experiments/NOTICE.md) | Derived from a pinned Wikimedia Wikipedia snapshot through text extraction, synthetic perturbations, model fitting and numeric export |

Exact sources, hashes and transformation scripts for dictionary assets are documented in [packaged lexicons](app/src/main/assets/smarttyping/lexicon/provenance/PACKAGED_LEXICONS.md) and [the lexicon pipeline](tools/lexicon/smart-typing-0.3/README.md). Small model provenance and training instructions are in [typing experiments](tools/typing_experiments/README.md).

The optional Rune Text model is a separate download, not an APK asset. Its source and distribution notices are documented in [Rune Text 0.1](tools/model/rune-text-0.1/README.md).
