# A4: live IME checks on API 26 and API 37

The current debug IME and separate `:qa_editor` field were tested on freshly
created disposable arm64 emulators at API 26 and API 37. Each ran three native
instrumentation methods: preserve `инн.` after the case suggestion appears and
delete the period, select `Инн` manually, and correct `смотруть.` to `смотреть.`
then restore `смотруть` by Backspace. All three passed on each API, with the
fixture's content-read counters at zero. Both emulators were stopped and their
task-owned AVDs deleted.

APK SHA-256: `306e75b46df3a563a6506c53cad847b5d1194c66ee81d23d1a60befce10869c1`;
instrumentation APK SHA-256:
`8ef3ded4bd8248b57b0dabaa2921a01be2d8185b038ee120cdfd8ee293219c15`.
Raw logs are `build/review-a4-native-20261028/native-a4.log` (SHA-256
`360706cd9df68235deffc97e26327a3955d2bfdb7791c8d0f26cd8a45e432da4`) and
`build/review-a4-native-api37-20261028/native-a4.log` (SHA-256
`637e3b07f6da038bd81cbab0a1f3cbb4aa75f7991ded6d9e6deb35e6296b61f1`).
The generic cleanup script's `testsCompleted` field refers to a different U9
filename and is false; the native instrumentation logs and result JSON are the
evidence for these test results.

These are synthetic editor/emulator tests, not physical Fold acceptance. Colon
was covered in the host replay, not these native methods. Fold protected
abbreviation, useful correction and exact Undo remain required for A4.
