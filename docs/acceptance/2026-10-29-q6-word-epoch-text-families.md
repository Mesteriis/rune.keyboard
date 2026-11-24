# Q6: dictionary family exclusions for archived text fragments

The verified public archives contain 630 historical word-ranking and additional-epoch text records. Four new ledger entries conservatively record every dictionary analysis of Russian lexical surfaces extracted from those retained fragments. Their source article and segment keys are recomputed and matched against the existing text-segment parent entries. The pinned dictionary receipt, archives, sources and helper hashes are bound and rechecked. The original 164 entries and incomplete coverage declaration are unchanged.

| Fragment set | Records | Distinct surfaces | Resolved | Unresolved | Family keys |
| --- | ---: | ---: | ---: | ---: | ---: |
| Additional epoch test | 200 | 11,158 | 9,921 | 1,237 | 6,327 |
| Word ranking train | 253 | 10,072 | 8,920 | 1,152 | 5,903 |
| Word ranking dev | 85 | 4,960 | 4,481 | 479 | 3,357 |
| Word ranking test | 92 | 4,985 | 4,379 | 606 | 3,273 |

Across the four sets, 11,450 distinct family keys include 5,259 not previously present; 3,229 exact unsupported-surface keys include 3,116 new ones. Ambiguous dictionary analyses all contribute families. Unknown forms are exact exclusions only, not guessed lemmas; truncated fragments can contain partial words. These entries cover the retained fragments, not every source article or a complete linguistic or canonical-family analysis. Other historical coverage and fresh qualification remain open.

Two independent importer runs produced byte-identical ledger and receipt; the receipt SHA-256 is `a65abd52de11edc0449b8156013dd0744ba633f09a191b8863d40546cff26cb9`. Existing stored entries were compared individually and retained exactly; the four new family arrays use the existing compact encoding. A real dictionary family newly added by this step was accepted by the prior incomplete ledger with completeness explicitly disabled and refused by the updated ledger with `LEDGER_OVERLAP:family`. The focused unit test covers ambiguous analyses, unknowns, mismatched parent/article and overlong surface refusal. The complete standard-library inventory passed 781 tests across 154 modules with no skips; no model or APK was changed.
