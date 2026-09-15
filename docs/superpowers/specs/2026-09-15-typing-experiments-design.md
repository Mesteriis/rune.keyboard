# Learned mobile typing experiments

User approved all three research directions and individual settings on 2026-09-15.

## Scope
1. Ship an actually trained, compact candidate scoring model and a reproducible comparison against baseline, including a small CatBoost host reference. Candidate features combine spelling distance/frequency with context and existing permitted personal/touch signals. If training does not demonstrate superiority, label it experimental and report the actual metrics; never promote automatic authority.
2. Ship a compact specialized local neural context model, trained from public repository text only. It scores existing candidates and predicts next letters; it does not generate arbitrary editor edits. RU support initially, other languages explicitly unavailable. No private chat corpus in public weights or APK.
3. Implement a conservative dynamic tap resolver with OFF, shadow-only, and applied behavior represented by two switches (experiment enabled and apply to taps). Center taps, deletion recovery, stale context, non-letters, sensitive editors and disabled state preserve ordinary input. Shadow is the default when experiment is enabled.

## Architecture
Pure bounded Kotlin inference and tap policy, asset loading off the UI thread. Exact versioned assets, strict caps and finite numeric validation. Existing generated candidate IDs and automatic admission remain authoritative. New scoring reorders manual alternatives only and preserves original. Context comes only from acknowledged Rune-owned session text, never InputConnection readback. Features can be independently disabled. Dynamic taps can use the compact model independently of the compact ranking switch.

## Controls and observability
learnedRanking, compactContext, dynamicTouch, dynamicTouchApply default false; disabling all extras clears all four in the same transaction. Configured and effective diagnostics append four fixed bits (schema6) and tap shadow/changed counts or fixed reasons without coordinates or words. Existing consent and release no-op policy apply. Status text must accurately describe RU availability, experiments, shadow/apply dependency. No new network permission or runtime ML framework.

## Validation
Host reproducible training and held-out evaluation separated from training and private data, artifact provenance and Python/Kotlin inference parity. Meaningful pure tests for inference/codec and tap invariants. Controller and Android tests for actual toggles, tap paths and lifecycle, diagnostics schema/gates, JVM suite, lint, assembleDebug, privacy and IME boundary. Report on-device latency if measured; never label host timings Android timings.
