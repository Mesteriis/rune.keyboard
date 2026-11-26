# U9: recent emoji lookup after lazy name decoding

After per-entry name decoding, a linear scan of the opened filtered list would
decode each preceding entry just to find a tapped glyph. The filtered list now
supports glyph-only lookup and materializes only the matching entry. A JVM test
uses a later item to check that preceding names remain unloaded and a second
commit is deduplicated. Other lookup fallback and bounded recents behavior are
unchanged.

The 17 catalog JVM tests, IME/scoring boundary and debug/test builds passed.
The real API 26 `EmojiPanelInstrumentedTest` passed all four methods. Its first
run failed before test bodies because the sample fallback IME crashed and its
dialog covered the QA window; after dismissing it on the emulator, the complete
four-method run passed. Raw logs are in
`build/review-u9-recent-lookup-20261028/`; the successful log SHA-256 is
`d538860c5d8ab71ec27fe8266f63140d873f37fd6a9307118f825da47bd14e96`.
The debug APK SHA-256 is
`1097cb5fb89428ffdc972af3039790c4db7716694d4592a6094a9a57680f0b5a`.
This change is not a new opening-speed measurement; U9's 50 ms gate and
physical/accessibility acceptance remain open. Fold was not used.
