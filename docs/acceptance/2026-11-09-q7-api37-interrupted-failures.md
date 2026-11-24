# Q7: interrupted API 37 boundary run and targeted repeats

At source `8bcf703b`, a clean isolated ARM64 API 37 (16 KiB) emulator ran
the Android boundary suite with the CI navigation property, software GPU
options, a dedicated ADB server and Rune selected as the IME. The visible
navigation inset was observed in `dumpsys window`. Setup and APK installation
succeeded. A preceding setup attempt stopped before tests because it wrongly
required the navigation property to be readable on API 37; the temporary
environment from that attempt was removed.

The local setup did not disable system animations, although the hosted CI
workflow explicitly requests this. This fixture difference may affect UI
timing; no causal link to the failures has been established. The result is
therefore not an exact reproduction of the hosted CI configuration.

The general suite was deliberately stopped after Gradle progress output reached
242 of an initially reported 354 cases, with 37 skips and 11 failures. Those
are interim progress counters, not a complete fresh JUnit report or a passing
suite. The failures covered two expanded-candidate tests, two foreign-edit
tests, one navigation inset test, one stale-key test, four IME lifecycle tests
and one password-preview test. Several failures observed no typed text or no
tap events, while the preview positive control observed no changed pixels.
One contemporaneous screenshot showed an empty QA screen; window state showed
the QA activity focused and no obscuring window. These observations do not
establish the cause or identify a product defect.

After stopping the runner and reinstalling the same debug and test APKs on
that emulator, each of the 11 failed methods passed direct instrumentation:
the three-method expanded-candidate class, the two foreign-edit methods,
the inset method, five lifecycle/stale-key methods and the password-preview
method. Each run reported the expected test count, `OK` and instrumentation
code -1. The expanded-candidate class included one additional passing method;
the Russian candidate method was also rerun once separately. Reinstallation
and restarting instrumentation changed the state, so these repeats do not
establish why the longer run failed or its stability under the original order.

The suite's separate scopes and restart phases did not run after interruption.
The emulator, temporary checkout, screenshots and APKs were removed. No raw
logs or screenshots were retained. No hosted x86_64, Fold or full API 37 pass
is claimed; the failures require a source-bound sequential reproduction and
diagnosis before any fix or acceptance.
