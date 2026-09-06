# Initial eight-case editor extension — 2026-09-06

Both API 26 and API 37 pass all seven real Binder non-normal forward-typing cases: password, NO_PERSONALIZED_LEARNING, email, URL, number, phone and date/time. Each has an actual NORMAL model/caps observer positive control. These do not claim read-free Backspace in NORMAL-policy non-text modes.

The eighth protected-form case fails on both APIs before selecting the colon alternate: UiAutomator cannot find the expected alternate cell. Full results are **7 PASS / 1 FAIL** (API26:175.943s; API37:165.432s), not a passing eight-case run. The exact initial source and APK receipt are preserved. Subsequent helper changes inspect the actual in-process non-focusable popup geometry while retaining real MOVE/UP; that change requires a new device run.
