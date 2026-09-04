# Smart Typing 0.3 AutoReplace 95% profile — 2026-09-04

The user selected 95% as the default spelling AutoReplace precision profile. The existing schema-3
`HIGH_CONFIDENCE` preference remains storage-compatible and is shown as `Auto-replace (95%)`.
`OFF` and `SUGGESTIONS` retain their behavior. A ready local model may automatically apply a
qualified spelling decision; the deterministic branch remains suggestions only. Protected tokens,
valid-word substitutions, incomplete search, unsupported editors and explicit Original retain their
vetoes. The first Backspace continues to restore the exact original through the single typing-owned
transaction.

The unchanged frozen v2 product holdout decisions meet the revised point-precision gate: EN
293/304 (96.38%), RU 342/359 (95.26%), ES 396/408 (97.06%). All languages have at least 300
model-assisted replacements; false changes are respectively 0/1000, 1/1000 and 0/1000, and Original
is always present. No threshold was fitted on that revealed holdout. The earlier 99% result remains
an immutable historical FAIL; this acceptance records the later user-selected release policy.

The historical export cannot be re-executed by the current strict verifier because it predates the
required `corpusDirectory` receipt field and production source hashes have moved. The verifier
correctly returned `HOLDOUT_RECEIPT`; the old report and numeric evidence were not rewritten. Fresh
Candidate-05 evaluation uses the new explicit profile end to end and remains a publication gate.

Focused checks: evaluator 28/28 PASS, product evaluator 8/8 PASS, and JVM correction/settings 41/41
PASS. Complete JVM passed app 644/644 plus runtime 19/19. Lint, debug/release/profile,
privacy release/profile, dependency boundaries and native symbols passed. The physical Fold/API 36
settings journey passed 1/1 in 14.156 seconds with the new RU/EN 95% text and independent preference
persistence. Physical ordinary-typo/model behavior and immutable model publication remain pending.
