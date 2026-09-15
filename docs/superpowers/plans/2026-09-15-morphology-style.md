# Morphology and Personal Style Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement and review these independently testable tasks.

**Goal:** Run three-way local correction evaluation and prepare private Telegram writing-style adaptation.

**Architecture:** Reuse production Kotlin candidate observations. Add a host-only morphological lexicon adapter and bounded ranking policy, alongside an independent Telegram-to-JSONL importer and n-gram trainer. Private artifacts stay local; no experimental change is promoted into the qualified keyboard.

**Tech Stack:** Python 3.11+, pinned pymorphy3/OpenCorpora dictionary; existing Kotlin/JDK replay toolchain.

**Spec:** docs/superpowers/specs/2026-09-15-morphology-style.md

## Global Constraints

- Never log, commit or upload message text or sender identities.
- No new Android/runtime dependency or weakening of existing qualification.
- Original remains available; preserve protected and incomplete-generation vetoes.
- Expected labels are evaluator-only. No fitting on the validation split.
- Record input/source/model hashes and actual check results.

## Task 1: Telegram importer and private style model

Files: tools/morphology/telegram_style.py, tools/morphology/test_telegram_style.py.

Produces `build_model(texts: Iterable[str]) -> dict`, `StyleModel(payload: dict)`, `StyleModel.bonus(prefix: str, candidate: str) -> float`. The bonus is bounded 0..1, based on normalized bigram/trigram support; unseen or empty context gives zero. Serialized model has `schemaVersion: 1`, `trainingSha256`, `messageHashes`, `unigrams`, `bigrams`, `trigrams`; keys for ngrams are space-joined normalized words. Consumers validate finite numeric limits. Import command takes repeatable --input, --self-id and fresh --output under an ignored build directory. Group entire chats into train/validation, deduplicate across files before split, preserve enough train coverage and refuse evaluation claims with fewer than two chats. Prepare JSONL `{"text": ...}` for each split, model.json, content-free report/receipt.

- [x] Write failing tests for outgoing selection, rich text, forwarded/service exclusions, malformed envelopes, duplicate exports, disjoint chats and duplicate text, restricted output, fresh output, ngram context support and no cross-message transitions.
- [x] Implement importer and trainer with explicit sender identity, validated bounded input, private file permissions and fail-closed errors.
- [x] Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools/morphology -p test_telegram_style.py`.
- [x] Review source and evidence; no real-data claim before exports arrive.

## Task 2: Morphology ranker and three-way evaluation

Files: tools/morphology/ranker.py, tools/morphology/evaluate.py, tools/morphology/test_ranker.py, tools/morphology/requirements.lock, tools/morphology/README.md.

Consumes actual production observations with original, candidates, distance/frequency features, completion/local-search evidence and prefix; optional StyleModel from task 1. Produces bounded decisions for baseline, morphology and morphology_style, preserving dictionary ambiguity and original. Download/install dictionary only in ignored venv, pin dependencies and record dictionary hashes. Generate graph rows on demand from dictionary analyses; no invented morphology labels.

- [x] Write tests for ambiguous analyses, missing dictionary entries, protected/valid inputs, incomplete search, context boundaries, wrong-language candidates, lack of margin and style support.
- [x] Implement morphology lookup and soft evidence over bounded context and real candidates.
- [x] Connect current production generator/replay, keeping labels outside ranker inputs.
- [x] Execute a frozen public evaluation and retained private diagnostics, labeling descriptive/revealed data honestly; save timing and error counts.
- [x] Run focused tests and existing analyzer regression tests; inspect full diff.

## Task 3: Integration, review, and private run when available

- [x] Review both modules and interface compatibility independently; repair actionable findings.
- [x] Document exact CLI commands, measured results, current limitations and original checkout export path.
- [x] If exports exist, validate sender identity, import, train and run held-out evaluation locally. Otherwise report the exact missing data without fabricating results.
- [x] Keep implementation on codex/morphology-style for review, without installing or replacing the phone app.

## Completion evidence

Implemented all three experiment stages. Added personal_holdout.py and six tests for synthetic recovery from disjoint validation chats. Final scoped validation: 53 new-module tests and 19 existing analyzer tests passed. Real Kotlin exports processed 4000 public,273 unlabelled dogfood and800 personal synthetic rows. Independent review findings on consumed-path hashes, production width, original retention, lazy load timing and helper-source binding were fixed and re-reviewed. Private results remain in ignored build/private; no user text or learned model is tracked. Android runtime promotion and neural weight training are outside this host-experiment slice.
