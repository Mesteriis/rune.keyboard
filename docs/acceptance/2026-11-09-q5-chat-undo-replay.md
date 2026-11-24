# Q5: chat-regression replay with verified Undo text

At source `852592c7`, a clean temporary checkout regenerated the disclosed
Tatoeba chat-shaped corpus using the historical lexical ledger recovered from
Git revision `3a18d3e166b38c23df4f1038182833ccf16cf11f`. Its ledger SHA-256
`6f9bc49549e5628655fe2de74b720f96ecd25ccce6ce95997a031eeea7bc18f5`, source
and generator matched the original manifest. All 34,330 generated rows matched
the original rows SHA-256
`c25d9afed4b75f78490f2e360c3eb0a0e06aaf97e3291d79f0bdd29aec0ee62f`.

The current-product JVM controller replay completed all rows and its own
source, toolchain, assets and input bindings passed. The new v2 chat reporter
independently compared the actual pre-boundary and post-Backspace text for
every observation and rejected no inconsistencies. All 16,819 changed
boundaries had exact text Undo; the report counted zero Undo failures and
zero prefix or input transformations. The aggregate `overall`, `controlRows`
and `controlClusters` values match the earlier committed report: 41 of 9,543
unproofread source-control rows changed. Its descriptive Wilson interval is
0.317%–0.582% and is not a verified false-change rate.

The replay observations SHA-256 was
`a8c32113c8b7a3e57e25d246a2a5851bcb5893544d59665f9932508153c3bf53`, and
the v2 report SHA-256 was
`e467a3962c09d63c3790adcf0ade4860b03398742cdcfee764f2d1536b705b24`.
One replay and one report were executed; no repeated-run determinism is
claimed. Temporary source, rows, observations, compiled harness and report
were removed. The previous 34,330-row raw observation file was not recovered;
this is a fresh replay of the same input rows, not verification of that file.

The source is previously disclosed, synthetic edits can be valid words and
source controls have not been independently proofread. This does not establish
a natural-chat false-change rate, independent qualification, real-device
timing or multiword revision behavior. No model, policy or APK was changed.
