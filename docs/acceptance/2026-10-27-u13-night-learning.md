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

## Current-source repeat on API 26 and API 37

At `fd35ae99b29982898fee0a5822183add4f0d2863`, a clean source clone built the
ordinary debug and Android test APKs. Each was installed and verified by
installed SHA-256 on separate disposable ARM64 Google APIs emulators,
2 GiB on API 26 and 4 GiB on API 37. The AVD timezone was set at launch to
`Asia/Tokyo`, placing the observed local clock within the 01:00–05:00 window
without changing the host clock. The emulator simulated AC power and 95%
battery. The first API 26 setup attempt failed resolving the local APK path
before installation. The corrected setup ran both API series.

| Exact scenario | API 26 | API 37 |
| --- | --- | --- |
| JobScheduler charging, idle, battery and storage constraints | Passed | Passed |
| Seed from complete candidate pools in installed assets | 20 held out, 8 gains, 0 regressions | 20 held out, 8 gains, 0 regressions |
| Night worker observed in `PROMOTING` and commits candidate, preserving previous active profile for rollback | Passed | Passed |
| Learning Lab shows threshold progress and the unchanged-candidate refusal | Passed | Passed |

Each API produced four exact successful instrumentation cases with zero skips.
The observer recorded screen asleep, charging, local night, unchanged boot
and no deep idle. It used the existing `tools/qa/review-night-learning.py`
observer with `--expected promoted`. As in the original acceptance run,
`cmd jobscheduler run -f` triggered the service after the observer was ready.
This verifies the service and durable store under those conditions. Natural
scheduler dispatch and hosted CI were outside this repeat. The two fixture
methods and the Learning Lab case remain opt-in skips in the general suite.

| Artifact | SHA-256 |
| --- | --- |
| Debug APK | `419c9a4f87f07f4a2b67ac25785c24fcd0cd9493204904d1a6bba2445a3aa547` |
| Android test APK | `d833f4d9cc57f84311d777780f6389e30285e4f724908049785798bd955ec920` |
| Seed summary, identical across both APIs | `d62e4884bb37b5ecd9b88e6e010d7fa154a68345d649ecfc2b1c7509ccb236eb` |
| Night observer summary, identical across both APIs | `5973372b2d88e607b5671a93f3c13b8fc9c53bcd6acf49505aa760909f2ee3d4` |

### Complete local CI runner on fresh API 26 and API 37 AVDs

The workflow's `android_night_learning.py` entry point passed on two fresh
ARM64 emulators using the [API 37 boundary source with the startup fix](2026-11-24-q7-api37-connected-boundary.json).
It installed the ordinary debug and instrumentation APKs, verified all four
instrumentation cases per API, and emitted a passing receipt for each.
Both seeds had 20 held-out cases, eight improvements and zero regressions.
Both observer runs recorded promotion while charging with the screen off
during the configured night window, and verified the durable active and
rollback profiles.

The [runner evidence](2026-11-24-q7-night-learning.json) binds the APKs,
runner and original receipts. Logs and reports are retained locally in
`build/ci-q7-api37-repeat-general/night-learning-startup-fixed-api26-api37.tar.gz`.
The synthetic runner invokes JobScheduler explicitly. Natural dispatch,
hosted CI and device acceptance remain open.
