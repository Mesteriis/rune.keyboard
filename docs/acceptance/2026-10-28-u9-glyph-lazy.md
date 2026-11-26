# U9: glyph filtering without eager name decoding

The catalog still validates the whole source before returning. Font filtering
now reads validated glyphs without constructing every entry and localized name;
the filtered list decodes and caches individual entries when accessed. Tests
cover unloaded entries, invalid indices, once-only concurrent publication,
source order and exact full-catalog reconstruction. The decoded catalog text,
source offsets and per-entry cache remain reachable for the palette lifetime;
no reduction in PSS is claimed. Recent lookup still scans the opened list and
can decode entries during that scan.

The predeclared series repeated the previous API 26 preview procedure: three
clean task-owned AVDs, four fresh palettes each, with no retries or tracing.
All twelve handlers were below 50 ms. First populated window draw-start times
in milliseconds were:

| AVD | Four draw starts, ms |
| --- | --- |
| 0 | 26.22, 11.71, 14.73, 15.13 |
| 1 | 29.53, 13.09, 20.81, 15.61 |
| 2 | 51.58, 14.76, 12.13, 16.74 |

One of twelve draw starts exceeded the budget, so the performance gate remains
**failed**. The previous series had four exceedances; these uncontrolled runs
suggest a possible improvement but do not establish a causal speedup or a
reliable tail bound. This measures a preview's click-to-draw start, not GPU
presentation, touch delivery, cold IME startup, release performance or Fold.
Eight native emoji font/panel/key tests passed after timing on the first AVD.
All three task-owned AVDs were stopped and deleted; Fold was not used.

The full debug JVM suite passed 1,370 tests with zero skips, as did 15 emoji
source tests, debug lint and the IME/scoring boundary. The APK hashes, raw
measurements, logs and cleanup receipts are in
`build/review-u9-glyph-lazy-20261028/`; `acceptance-result.json` SHA-256 is
`1a4e33d29add5bcd3e04aa2fdc46a8578b38a71c983b1584c90b65de303953ee`.
No replay or physical-device performance result is asserted here. U9 remains
open for the failed budget and its other device/accessibility requirements.
