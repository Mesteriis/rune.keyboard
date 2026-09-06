# Physical inner Fold probes — 2026-09-06

Source base fd8872f; both installed APK hashes equal the previous qualified
local app/test artifacts in preflight.json. The phone reports physical OPENED
state,1968×2184, with no override. Post-run state is retained in results.json.

- Composing15 + mechanical3:18/18 PASS,137.854s.
- Live candidates4 + settings6 + actual installed-model typing1:10/11 PASS,
 144.473s. Real model Space correction and first-Backspace Original both passed.
- The sole failure is the settings fixture's unconditional Unavailable summary
  when a qualified model is Ready. Its raw failure stays in live-settings-model.log.

The new contextual Binder tests and corrected exact-availability settings test
compiled, but replacing the test APK was rejected by Android with
INSTALL_FAILED_UPDATE_INCOMPATIBLE. test-update-rejected.json binds the old and
new test APK identities. They have not run on this phone. No uninstall or model
removal occurred. The old app/test APK remain installed; their passes must not
be assigned to the new tests or subsequent contextual policy.

The local JDK/debug keystore and Android SDK installation differ from the earlier
host setup. A local-only backup of no_backup and shared_prefs is under ignored
build/smart-typing-0.3/phone-preservation-2026-09-06/. Its GGUF was independently
hashed to the required396704416-byte7a97111c…dd9c4 artifact. Personal settings and
the backup archive are not committed. Reinstallation/restoration requires the
requested user confirmation because the old matching signing key was not found.

A manual folding preflight could read the public QA editor's numeric hierarchy,
but the legacy shell UI dump did not expose IME key nodes. No coordinates were
inferred from an image, no text was injected around Rune, and no folding success
is claimed. The preceding default IME and enabled state were restored.

These are functional inner-screen observations. They do not qualify folding
transitions, third-party editors, rapid typing, frame/event loss, cold-storage
loading or unplugged battery use. No phone screenshots or private editor text
were collected; all test text is a fixed public fixture.
