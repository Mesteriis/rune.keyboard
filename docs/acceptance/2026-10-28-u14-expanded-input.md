# U14: typing while the expanded row is open

An additional actual-IME test opens the hidden row for the synthetic input
`addess`, taps `m` outside the row and verifies that the editor contains
`addessm` and the old hidden suggestion disappears. A separate test explicitly
selects that hidden suggestion. Both passed on API 26 and API 37 emulators,
with the QA driver's settings restoration. The adjacent evidence binds the
test and both APKs. This complements, rather than replaces, the earlier held
popup touch cancellation and controller ownership tests.

The popup overlays the upper keyboard row while open, so this check deliberately
uses a key outside the overlay. Fold layout, manual TalkBack and real-device
acceptance are still outstanding. The emulators used for this run were shut
down after the tests; no physical phone was changed.
