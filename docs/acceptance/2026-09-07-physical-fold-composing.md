# Physical Fold composing transition — 2026-09-07

Device: Samsung SM-F966B, API 36. Test build based on `6609538` plus the
configuration-view lifecycle fix in this change.

The physical test began on the cover display (`1080 × 2520`) and, after the operator
opened the device, observed the inner display (`1968 × 2184`). It used the real Binder
`InputConnection`, with no editor text readback.

Result: **PASS**.

`PhysicalFoldComposingInstrumentedTest` completed in 24.628 seconds with 0 failures.
The editor preserved `ab`; composing ownership was invalidated without replay; the
same IME service instance remained (`SAME_IME_SERVICE=true`); Shift presentation,
subsequent `C` input and Delete all completed successfully.

The verified fix recreates the attached input view after a configuration change only
when it was active before the transition. This covers Fold firmware which retains the
focused editor but does not call `onStartInputView` again. It neither refocuses the
editor nor reads or restores editor payload.
