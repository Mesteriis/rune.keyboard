# Q7 deterministic API 26 system spelling-popup regression

The debug-only QA editor can now seed a known misspelling with an Android
`SuggestionSpan` when a test-only intent extra is present. This is an actual
framework spelling-suggestion popup, not a synthetic `PopupWindow`. On Android
8 the framework's editor invokes its suggestions window for an easy-correction
span; see the [Android 8 Editor source](https://raw.githubusercontent.com/aosp-mirror/platform_frameworks_base/android-8.0.0_r1/core/java/android/widget/Editor.java).
The fixture is absent from the release variant and disabled by default.

The API 26 instrumented regression requires the system suggestion container to
appear, checks that the same helper used by `focusField` dismisses it only when
present, and confirms a subsequent key reaches the same field without losing
its original text. Three fresh invocations passed. A controlled mutation that
makes the helper refuse a visible popup failed at the expected assertion; the
fixed code was restored and tested. The targeted editor-boundary class plus
this regression passed together: six tests, zero failures and zero skips.

The mutation log SHA-256 is
`65186196834bbe1fe1d3bfe39f515548438c2c583bffcd5221725f5a6992aa16`;
the six-test log is
`80d679ba080cd2929a1d898cb94a779ae6f799c478c273eee9ef6e419d1b380b`.
Raw logs are retained in ignored `build/q7-real-spelling-fixture-20261103/`.
This adds deterministic API 26 coverage to the previous real intermittent
reproduction; it does not establish a new full CI or hosted CI result. The
separately recorded full local API 26 repeat predates this test-only change.
