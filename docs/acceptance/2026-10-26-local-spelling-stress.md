# Local spelling stress audit while Fold is reserved

> Historical report retained from its original date. Its measurements and
> qualification claims apply to the original recorded inputs and implementation.
> Current source-presence checks are in [the README source audit](2026-10-28-q2-readme-sources.md);
> they do not establish fresh model, device or complete Q6 acceptance.

The owner authorized local expansion of typo/control coverage, investigation of seven remaining abstentions, and retrieval/ranking measurements while AURA finishes its physical cycle. No Fold command or installation was performed for this audit. The earlier application patch remains pending physical acceptance and installation.

## Frozen discovery corpus

`tools/typing_experiments/local_spelling_stress.py` creates 1,676 deterministic cases: 1,548 single-edit intentions and 128 correct-word controls. Thirty authored everyday Russian words receive missing-letter, repeated-letter, adjacent-transposition and horizontal-key-neighbour edits. Each is observed without context and after neutral `ну`. Controls include short forms, names, brands and plausible competing words. Labels do not enter the Kotlin observer.

Frozen rows SHA-256: `9a31473456b9a282319894645434d742e20fd7a02d17903353e6e864b4051d2d`. Label-free inputs SHA-256: `fa400451aaa627aa07ade0ed75d50cffa26f6f3f24727023bb4fae2c199caeea`. The corpus was generated before its observations were opened. It is an authored discovery set, not independent policy qualification or natural typing accuracy. Each row replays one word boundary after its prefix, not a physical phrase.

Three fresh JVM processes produced identical boundary text, displayed candidates and exact Backspace documents for all 1,676 rows. All 128 controls were retained; zero unintended spelling substitutions, prefix changes, input transformations or Undo failures were observed. The intended spelling was applied on 881/1,548 edit rows.

| Family | Cases | Intended output |
| --- | ---: | ---: |
| Missing letter | 322 | 92 |
| Repeated letter | 322 | 231 |
| Adjacent transposition | 262 | 180 |
| Horizontal neighbour | 642 | 378 |
| Correct controls | 128 | 128 |

Six further changes were canonical casing of dictionary-valid names: `ир → Ир`, `жень → Жень`, `кинга → Кинга`, each in two contexts. They do not match the authored typo intentions (`мир`, `день`, `книга`) and are reported separately, not credited as corrections or called spelling substitutions. Of 92 edit rows that were actual dictionary-valid originals, 86 were retained and six only changed case. Many missing-letter mutations form valid words, so the low intended-output count is not sufficient evidence to weaken original-word protection.

The report also preserves 491 abstentions with **no admission callback**, grouped by observed baseline/recovery/joint completion. These are not assigned an invented precise refusal. Other observed abstentions are 86 dictionary-valid originals, 76 `WINNER_AMBIGUOUS`, two `ORIGINAL_VALID`, and six `RIVAL_OTHER_LEMMA`.

## Seven existing abstentions rechecked

The previous 24 cases were replayed with the instrumented harness; boundary text, displayed candidates, exact Backspace documents and completion status matched the prior checked harness on all 24. All seven remaining intended words are first manual corrections with optional manual expansion enabled. Automatic output remains unchanged.

| Input → intention | Observed evidence |
| --- | --- |
| `куа → куда` | Baseline complete, joint search returns `VALID_WORD`, no joint pool or admission callback |
| `поггорим → поговорим` | Baseline `STATES_EXHAUSTED`; joint pool complete; model ranks `прогоним` 0.768 over `поговорим` 0.631 |
| `нуден → нужен` | Actual original `VALID_WORD`; manual option present, automatic original retained |
| `будкт → будет` | Complete joint pool; near-tie `будет` 0.764992 versus `будки` 0.764162 |
| `позвоеить → позвонить` | Baseline `STATES_EXHAUSTED`; joint pool complete; scores 0.872783 versus `позволить` 0.769748 |
| `рал → рад` | Baseline complete, joint search returns `VALID_WORD`, no joint pool or admission callback |
| `сттл → стол` | Complete joint pool; model ranks `стал` 0.834222 and `стил` 0.714420 over `стол` 0.681442 |

These observer facts support keeping the current safeguards. There is no threshold change or new finite exception from this discovery set. Missing-letter retrieval/ambiguity and context ranking remain the next improvement areas; any broader model change needs a separately frozen qualification set.

## Desktop stage measurements

Developer-only timers exclude observer score export and serialization. Each process includes JVM warmup; model observation scoring may warm caches before controller ranking. These are neither cold-start nor physical Android timings, and the controller stage includes admission as well as ranking. Optional manual expansion is enabled in this observer.

| Stage | p95 range over three runs, ms |
| --- | ---: |
| Baseline retrieval | 2.641–3.972 |
| Recovery retrieval | 1.038–1.508 |
| Joint retrieval | 0.966–1.364 |
| Manual retrieval | 1.875–2.698 |
| Controller candidate ranking/admission | 1.558–1.727 |
| Space boundary | 0.068–0.088 |

The measurements do not justify increasing search budgets or asserting Fold deadlines. No product hot-path code or packaged model changed in this audit.

## Checks and evidence

- Current-source Kotlin replay harness compiled successfully with the pinned toolchain.
- Three production-controller replays: 1,676 complete observations each; identical text/display/Undo results.
- Previous 24-case text/display/Undo parity: passed.
- Python audit and quality-slice regression suites: 16 tests passed.
- `git diff --check`: passed.

Raw observations, compiler receipt, source hashes, per-process reports, seven-case extraction and check logs are retained under ignored `build/local-stress-20261026/`. Physical checks and update remain pending explicit Fold handoff from AURA, as the owner requested.

Subsequent physical window: the update was checked and installed after explicit handoff; see [physical results and retained intermittent failures](2026-10-26-fresh-phrase-ranking.md#physical-fold-results). This local audit's host measurements remain distinct from those physical results.
