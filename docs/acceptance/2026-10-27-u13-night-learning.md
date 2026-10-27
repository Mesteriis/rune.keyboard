# U13: charging, screen-off night evaluation

The service used deep Doze (`isDeviceIdleMode`) as its runtime idle condition.
On an isolated Android 36 emulator at night, charging with the screen asleep,
the old APK at fe2c663 rescheduled the actual job (failure count 1), never entered
PROMOTING and did not change the active profile. Deep Doze was false. No
force-idle command was used.

The runtime check now requires `!isInteractive`. JobScheduler charging, idle,
battery and storage constraints remain intact, as do consent, night, thermal,
periodic cancellation and final commit checks. This changes local suggestion
pattern evaluation, not automatic correction admission or model qualification.

The same observer test APK verified the old and fixed worker. A declared
synthetic public-word fixture uses actual APK retrieval and evaluation: 20 held
out examples, 8 improvements and no regressions. With the fixed APK, PROMOTING
was observed, active became candidate, rollback retained the previous profile,
and the durable write succeeded. Updating the installed APK preserved the
fixture bytes. A second fresh-emulator run verified the final APK after the UI
formatting fix. Neither run forced Doze or rebooted between observation and
commit. `jobscheduler run -f` deliberately bypasses scheduler readiness to test
the service's independent guard; this does not prove natural multi-night
scheduling, real-user quality or long-term benefit.

Learning Lab now displays eligible holdout, correction and unchanged-word counts
against the existing 20/10/5 minimums. Counts share the evaluator's rejection and
conflict filtering. Enough samples are explicitly distinguished from passing
validation. EN/RU explanations cover unchanged candidate, insufficient samples,
cancellation, incomplete evaluation, regressions and lack of gain.

Validation:

- 1,162 JVM tests: zero failures, errors or skips, including three new tests.
- IME intelligence boundary and release privacy gates pass.
- Debug lint, app APK and test APK builds pass.
- Final APK instrumentation: threshold progress and actual unchanged-candidate
  refusal pass; scheduler constraint test passes (one test each).
- Two early fixture preparations failed for too few usable targets; expanding
  the declared vocabulary resolved preparation without weakening thresholds.
- Initial lint caught concatenated display text; a localized format resource
  fixed it, followed by final lint and final APK UI validation.

The task-owned disposable emulator and AVD were removed after draining tests.
Fold was not accessed. Source, artifact and log hashes, exact Gradle checks and
numeric observations are recorded in the adjacent evidence JSON. U13 is verified
locally; other review cards retain their individual open requirements.
