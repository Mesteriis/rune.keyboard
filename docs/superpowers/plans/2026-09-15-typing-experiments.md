# Typing Experiments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Implement the three approved mobile typing experiments with independent controls.
**Architecture:** Pure Kotlin bounded models and resolver; off-thread public assets; existing editor ownership. Parent owns settings/diagnostic integration while sequential workers implement isolated cores.
**Tech Stack:** Kotlin/Android, host Python training, existing Gradle gates.
**Spec:** docs/superpowers/specs/2026-09-15-typing-experiments-design.md

## Global Constraints
- New switches default false and are included in disable-all.
- No private chat corpus in public weights or APK.
- New scoring reorders manual alternatives only and preserves original.
- Context comes only from acknowledged Rune-owned session text, never InputConnection readback.
- No new network permission or runtime ML framework.
- Experimental quality claims require held-out evidence; no automatic-authority promotion.

## Task 1: Trained scoring and compact context core
Create smarttyping/experiments pure model inference, strict public asset codecs and Android off-thread resource owner; tools/typing_experiments reproducible train/evaluate/parity and provenance; focused Kotlin/Python tests. Training source is existing public calibration corpus, separate holdout. Expose candidate feature scoring and next-letter probabilities with RU support readiness. Export numeric bounded weights, not executable Python. Include actually trained CatBoost reference and compact neural context model.
- [x] Freeze public input identities and split before fitting; assert no holdout fitting.
- [x] Implement and run training/evaluation, save raw reports under build/typing-experiments; ship public assets and provenance.
- [x] Write inference and malformed/finite/size tests, implement strict Kotlin loader and bounded scorer; run focused tests and parity.
- [x] Self-review and report exact files, APIs, checks; task review before integration closure.

## Task 2: Dynamic tap resolver
Create pure resolver plus RuneKeyboardView/KeyboardKeyView hook and tests. Consumer passes current owned prefix and next-letter probabilities. Resolve physical short single-pointer alphabetic taps only. Preserve center region, cap distance and prior influence, keep static after backspace until boundary, clear on geometry/editor/settings changes. Shadow reports decision but commits original. Apply preserves case and emits matching touch sample. No disk or expensive model recomputation per tap.
- [x] Add pure geometry/prior/cancel/disable invariant tests and implement bounded resolver.
- [x] Integrate physical tap callback with original key fallback and instrumentation tests for shadow/applied/non-tap paths.
- [x] Run focused checks and provide exact API plus evidence for task review.

## Task 3: Controls, session integration and validation
Parent edits KeyboardSettings, KeyboardPreferences, SettingsActivity/resources, DiagnosticFeatures/TypingFeaturePolicy/debug serializer/analyzer and frozen gates, TypingPersonalization/AndroidTypingPersonalization/TypingSessionController, RuneInputMethodService. Provide owned prefix accessor and candidate scoring inputs; never replace auto policy. Tests cover independent off switches, unavailable assets/language, sensitive fields and disable-all.
- [x] Wire all four persisted switches and status/help strings, dependency disabling and atomic disable-all.
- [x] Append schema6 flags and tap outcome observer fields or fixed events; update strict analyzer and gate inventories without broadening text flow.
- [x] Integrate loaded cores with controller and service lifecycle; bounded cached next-letter predictions.
- [x] Run focused regression checks, full JVM/lint/privacy/boundary/diagnostics checks and owned-emulator instrumentation. Save exact results.
- [x] Review complete diff, fix findings, document behavior and evidence; package debug APK and retain branch.
