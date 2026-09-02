# Scoped independent review — settings fix 2

**APPROVE. The faulty empty-editor oracle is corrected without weakening the privacy requirement. No new P1/P2 found.**

Reviewed patch SHA-256 `ac20e2ee5b88ceebee87db464404d83eed4c72e262c06e218377792cf1a163f4`. All eight entries in `identities.json` matched; the copied baseline matches current root, and the diff exactly matches the before/overlay change.

The preserved API26 log reports 12 tests / one failure in 166.162 seconds. The failing empty-string comparison received `Composing Binder fixture`, which exactly matches `qa_composing_hint` set by `ComposingQaFixture.kt:37`. The driver compares accessibility text directly. That observation does not establish nonempty editor content, and the failed log did not independently record Editable length; the report correctly preserves this distinction.

The replacement asserts the existing numeric `length` statistic equals zero. `ComposingQaFixture.publish` at lines 101–109 computes it directly from `editor.length()`, separately from the hint. The fixture publishes initially and on its existing editor/connection callbacks. Thus genuine nonempty text, including text equal to the hint, cannot satisfy the corrected emptiness condition.

The following exact `w` insertion, absence of old/new Original candidate labels, zero composition and all six readback-counter assertions remain unchanged. The earlier held-key, repeated-toggle, CANCEL and identity checks are intact. No production policy, shared driver behavior, fixture, Undo or candidate logic changes are included. The test continues to require a cleared private editor and no resurfaced candidate content.

Read the saved affected-test-plus-unchanged-helper compile command/log: **exit 0**. The isolated patch dry-run also reports **exit 0**. These establish source compilation and applicability only. The corrected API26 targeted run and full affected API37 matrix are still prospective; the original eleven passes remain historical evidence.

Review was limited to the source delta, existing fixture/driver seam, preserved failure, compilation/applicability records and read-only hash/diff arithmetic. No tests, builds, devices, model or corpus operations were rerun. This review file is the only write.
