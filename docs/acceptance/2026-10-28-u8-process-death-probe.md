# U8: process-death fixture probe (not acceptance)

On the API 37 emulator, a disposable experimental instrumentation fixture
connected the real Rune IME to the debug editor in `:qa_editor`, entered `old`,
and pasted `foreign` through the editing panel. While the instrumentation was
still active, the host verified distinct main and editor processes and killed
only the main process through `run-as`. The instrumentation ended, the QA
editor process disappeared and the launcher became foreground. An ordinary
completed instrumentation phase also removed the editor before a later phase.
Consequently this setup did not retain the editor across process death and did
not test post-death typing or foreign-text isolation. The experimental fixture
was removed rather than committed as a passing test.

A meaningful next fixture needs an editor in a separate application package or
another host-controlled process that survives instrumentation teardown, with
explicit process identity, editor continuity and no-extra-payload-read checks.
This probe used only synthetic text on an emulator; no Fold or owner data was
used. U8 remains open for actual process death and physical/manual acceptance.
