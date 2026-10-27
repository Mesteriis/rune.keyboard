# U4: finish a reported composing region after ownership loss

Reproduced both losses on the old real IME and an unchanged remote editor
connection: inserting `X ` before `hello`, then typing `x`, produced `X x`;
replacing `--` with `—` before a pending owned space produced `a— bx` instead of
`a— b x`. The editor mutations preserve composing spans and explicitly notify
selection, without removing spans or calling `restartInput`.

The controller now sends one non-text `FinishComposingText` when a selection
callback reports a remaining composing region, even when Rune no longer owns it
or has no local composition. It clears its context/Undo/candidates and retains
the existing session-only disable rule for lost ownership. No shifted span is
adopted by length and no old text is sent back. A callback already reporting no
span does not gain another finish. If publication or a cleanup callback starts another session, session/revision
guards keep the obsolete cleanup from affecting that replacement editor.
A rejected finish is attempted once and cannot revive ownership; removal in an
editor that refuses cleanup is not guaranteed.

The debug fixture has dedicated Insert prefix and Rewrite dash buttons. On the
fixed APK, both scenarios preserve the word/pending space and subsequent `x`,
increase the finish counter, keep the same InputConnection and perform no new
composing writes after ownership loss. Together with full editor rewrite and
explicit dropped-span controls, all four instrumented scenarios pass on a fresh
disposable Android 36 arm64 emulator. It was stopped and its AVD deleted.

All 1,191 JVM tests pass with no failures/errors/skips. New regressions cover the
independent editor document/selection model, an unknown reported span without a
Rune composition, refusal without retry and cleanup starting another session.
An initial pending-space simulator left old acknowledgements queued and mistook
the shifted span for one of them. Correcting the fixture to acknowledge writes
synchronously reproduces three old-code failures against the exact HEAD source;
all pass with the fix. Existing unknown-region and stale-Undo expectations now
require non-text cleanup while still forbidding buffer replay or Undo revival.

The frozen 12,000-row ordinary current-product replay is byte-identical before
and after excluding host timings, including candidate/admission, boundary text
and commands, and exact immediate Undo. Metrics and product gates are unchanged.
That replay does not generate external selection deviations and is regression
proof only; simulator and real editor tests prove this fix. Existing EN quality
limitations and the ES holdout false change remain separate review work.

Full JVM, debug/test APK builds, IME boundary, release privacy and debug lint pass.
Exact commands, failures, identities and outcomes are in the adjacent evidence
JSON. This proves local/emulator acceptance. It does not provide a universal
composition guarantee for editors hiding changes or refusing finish, physical
Fold acceptance, or full review completion.
