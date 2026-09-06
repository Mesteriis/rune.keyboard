# API 37 full instrumentation — 2026-09-06

The fresh full application suite at `27d07ea` ran 131 tests in 1071.729 seconds:
**127 passed, three optional installed-model assumptions, one failure**.
`passwordFieldSuppressesPopupWithNormalFieldPositiveControl` observed zero changed
pixels in the ordinary-field preview crop. Its public-QA screenshot showed the
keyboard and pressed key, with no visible preview. The initial failure is retained.

The unchanged isolated privacy class subsequently passed **2/2** in 27.663 seconds
on the same emulator and APKs, without a restart. This repeat does not establish
the cause or turn the failed full suite into PASS. The separate JNI contract class
passed **6/6**, without skips, in 0.160 seconds.

`results.json` identifies the API 37 Google APIs ps16k arm64 image, revision 6,
and all three APKs, whose installed bytes were checked against the build artifacts.
Compressed logs retain every terminal result. Only status bundles with both class
and test names count; 1506 numeric measurement status bundles are excluded.

Full-suite stability, the absent editor-matrix scenarios and physical-device
qualification remain open. No full model was installed in this emulator.
