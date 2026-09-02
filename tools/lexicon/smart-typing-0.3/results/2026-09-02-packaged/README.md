# Packaged reader evidence — 2026-09-02

Final debug APK and test APK hashes are in `pr06-packaged-apk-proof-fixed.json`. The same final pair passed on API26, API37 and physical USB Fold API36. Each run executes the actual APK mappings/validation, 24 fixed exact references, missing/compressed/manifest-negative checks and a tiny positive-offset/FD-closure regression. Initial failed logs are preserved; the region-domain defect is fixed rather than skipped. The initial API26 log predates the fix and new FD regression.

`metrics.json` contains the numeric rows from final logs. Language IDs here are 0=EN, 1=ES, 2=RU. Each language is loaded once, sequentially in one process. Later memory snapshots may include earlier mappings and other process memory; reclamation is uncontrolled. These are incidental functional-run measurements, with debug code, unconstrained page-cache/thermal state and potentially overlapping host work. They are not p95, isolated component memory, cold-storage, release-speed or energy evidence. There is no forced GC/unmap. All mapped bytes are public dictionaries.

No user text, editor content, serials or credentials are recorded. The fixture uses only its own cache file and removes it. Fold updates used install -r without uninstall/data clearing; prior installed APK is retained privately outside versioned evidence. Do not copy that device backup into this package.

The host staging failure is preserved. The fixture-only temp-root canonicalization subsequently passed all five tests; production scope and symlink validation were unchanged. Final full local lint/build/privacy/dependency/native gates passed separately. Fresh post-commit JVM and full IME/API/Fold/quality gates remain independent.
