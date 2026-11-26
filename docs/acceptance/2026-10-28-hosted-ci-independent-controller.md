# Hosted CI: independent controller editor tests

The published main workflow failed the contextual punctuation editor and owned
batch tests on API 26 and API 37. On a disposable API 26 emulator, the unisolated
fixture reproduced the punctuation failure: after one composing operation the
remote editor reported one finish operation, no composing span and selection
at position 5. The actual text length was five. The separately created controller
and the resident IME controller both observed the same editor; the resident
controller correctly closed a span it did not own.

The test-only helper ends the resident controller session on the IME main
thread before returning the real remote editor connection to the independent
controller. This does not issue an editor command or change product ownership
handling. Failure messages now report numeric remote counters and positions.
These fixtures exercise the independent controller and real editor connection;
they do not establish the behavior of the resident service controller.

Validation on local disposable ARM64 emulators:

- Before isolation, contextual tests reproduced the missing-span failure on
  API 26; numeric diagnostic evidence is retained under
  `build/review-hosted-editor/diagnostic-api26.log`.
- After isolation, the three contextual punctuation tests and owned batch test
  passed together on API 26 and API 37: 4/4 on each. Logs are
  `build/review-hosted-editor/isolation-api26.log` and `isolation-api37.log`.
- `:app:assembleDebugAndroidTest :app:lintDebug --offline` passed. The app APK
  SHA-256 was `4ec78729849a0d86bed2e9636c1717e859692e86836a6f2e98ef075ed1af82f3`;
  the test APK SHA-256 was
  `72dade446ed5e7628068058f37fb7ef8602890cd92979a8d21f1898e41881fa3`.
- Base commit was `70d9f19ab33dc843821e987c2512cea11aa3a6d2`; changes in
  this slice affect Android test sources only.

This is targeted local evidence, not a hosted workflow rerun or complete Q7
acceptance. Other hosted failures and an actual hosted rerun remain open.
