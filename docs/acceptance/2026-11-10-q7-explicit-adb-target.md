# Q7: explicit emulator target in CI setup

The hosted Android setup verified that exactly one connected device was its
owned emulator, but several later shell ADB commands omitted a serial. A device
appearing after the check could make those commands fail or otherwise change
their target selection. The setup now uses the serial returned by the existing
owned-emulator guard for both APK installs, logcat, settings, IME setup and
activity launch. The app is installed directly from the just-built debug APK;
the earlier build remains responsible for creating it. Existing device guards,
suite scheduling and failure capture remain in place. This change targets
direct ADB calls; it does not assert that Gradle's connected tests are scoped
by the serial or protect against every emulator reconnection race.

Five host-side shell tests pass. They verify the guard/build/install order,
explicit target on all direct ADB commands, preservation of suite and capture
exit statuses, and independent failures of each APK install stopping setup.
The test runs shell functions as fakes; no device or hosted workflow was run.
The same five tests passed in a staged source archive without `build/`; the
archive was removed. Physical Fold acceptance and hosted CI remain open.
