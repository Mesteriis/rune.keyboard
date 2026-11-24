# U18 final theme suite on API 26 and 37

After the home-preview integration and navigation-capture test addition, the
complete `KeyboardThemesInstrumentedTest` class ran on task-owned arm64
emulators with the final production debug APK. API 26 passed 9 tests in 168.076 s;
API 37 passed 9 tests in 147.78 s. Both instrumentation summaries reported
`OK (9 tests)`. This includes all five shapes with both palettes, settings,
live changes with preserved text, fixed-viewport captures, language swipes,
system palette, home preview and synthetic navigation capture. The API 37 run
used its normal gesture navigation mode; the prior dedicated navigation receipt
covers the three-button mode separately.

SHA-256 bindings:

- Debug APK: `a5880c41ce5320f9c12c372e8c6cdead6f86ada1ffa7d8e83cdd4a97cb86fdba`
- Test APK: `fd1c94c3e8c14a4cc8586f3caa5e70e052714e5572cae09367bd8b898bcbeea0`
- Test source: `0459cbb6c98175acdfc5d0c7c7c487c58a155443cd84a3291da3bb603149a5b1`
- API 26 raw log: `6270dd39768caa6d677a95117f01a2c2c5c071d208d0f84d5bffeb31e51e3dc1`
- API 37 raw log: `57ea38dcf8271ddcdab79de42fcc4df88cd816e53d5ae589138e2c75b6ebedc8`

Raw logs are retained locally in ignored `build/u18-final-suite/`. Both task-owned
emulators were stopped. This does not cover Fold, manual TalkBack, other API or
screen configurations, or distribution acceptance.
