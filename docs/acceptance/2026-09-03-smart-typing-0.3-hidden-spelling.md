# Independent spelling availability — 2026-09-03

Baseline `0958a8e` implements qualified boundary correction/Undo. Its mandatory
fresh post-commit JVM run passed 630/630, zero failures/errors/skips. The exact
debug APK `617e97a9d250c9bcbc409b20a7b3c66275351a398a399570c4418865dfdbf4a7`
was installed and launched on the reconnected Fold; setup still reports that
Rune is not enabled. This is installation evidence, not physical typing or energy
qualification.

The candidate coordinator now separates strip presentation, local spelling work
and model spelling work. A hidden strip permits retrieval in HIGH_CONFIDENCE
only when at least one automatic branch is qualified for the current language.
It permits model demand only when the model-assisted branch is qualified.
Deterministic-only automatic availability does not attach the model client,
activate its readiness source, or schedule a scoring pause. OFF and SUGGESTIONS
with a hidden strip have no spelling consumer. Visible suggestions retain their
existing independent demand. Sensitive editors, inactive views, selection and
non-letter layers veto both paths.

The actual service reads qualification from its typing controller for each fresh
owner snapshot. This is immutable quality evidence, not a preference or model
Ready flag. `SpellingQualification.CURRENT` remains closed until final product
holdout qualification. Tests inject admission only through the existing internal
controller seam; this change does not unlock production automatic replacement.

Five new coordinator tests cover all 48 mode/strip/qualification combinations,
hidden deterministic correction and immediate Undo with zero model demand,
hidden model result consumption without boundary scheduling, cancellation when
hiding the strip leaves only deterministic work, and privacy/ownership vetoes.
They use the actual local worker, controller and model coordinator with an
in-memory lexicon and fake model transport; they do not claim Binder or physical
energy results. The prior real-executor boundary tests remain in the JVM suite.

Fresh JVM635/635 PASS with zero failures/errors/skips; full lint, debug/release/
profile, privacy/dependency/IME/native gates and Android test assembly PASS
(277 tasks, 3m37s). Android execution was not rerun for this slice; automatic
hidden consumer Binder/Fold evidence remains open. Post-commit JVM is required.

Enter/editor
actions, contextual suggestions, final frozen product holdout and complete
API26/API37/Fold/energy/release matrices remain open. Version stays 0.2.0; no
push, remote PR or model publication was performed.

Evidence: `tools/qa/smart-typing-0.3/results/2026-09-03-hidden-spelling/`.
