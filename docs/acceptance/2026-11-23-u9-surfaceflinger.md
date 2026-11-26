# U9 Emoji opening in SurfaceFlinger FrameTimeline

The first fully populated Emoji grid crossed the 50 ms review budget in a
process-cold API 37 test. The trace-only build tied its first populated grid
draw to a display frame that SurfaceFlinger classified as `On-time Present`
at 52.147 ms after the release of the Emoji key. On the unchanged build, a
separate repeat put the first Rune layer update after panel construction at
50.748 ms in one classified display frame. The latter trace lacks the
populated-grid marker.

## Test and frame correlation

- Source `61658b9eda2627d31c8695588ecaefb6d726ec9d`. Disposable 4 GiB ARM64
  API 37 emulator, image build `15611780`, software GPU and a 60 Hz virtual
  display. The non-debuggable, shell-profileable IME and separate debug QA
  editor were installed from the same source. ART speed compilation succeeded.
- A preliminary unchanged-build capture ran while Gradle was active. The two
  five-sample series ran after each build completed. The IME process was
  force-stopped with Rune deselected before each sample, then reselected and
  observed in the empty QA editor. The process IDs were distinct. The test
  used ADB taps on Symbols and Emoji and entered no editor text. Filesystem
  caches were warm.
- The temporary instrumentation wrapped the first `GridView.dispatchDraw`
  after a panel render in a constant trace section once the first cell's
  `TextView` held a glyph. Each positive trace contains one such marker, nested
  under `Choreographer#doFrame`. The Symbols-only control contains neither the
  grid draw nor the Emoji construction marker. Pixel hashes of a 1080 × 310
  crop containing the grid matched the populated reference in all ten
  positive captures and the Symbols reference in the control.
- Perfetto v59.1 used the SurfaceFlinger FrameTimeline data source, Android
  `gfx`, `view`, and `input` trace categories, Rune app sections, and a process
  snapshot. The analysis joined the Choreographer token to Rune's
  `VRI-InputMethod` SurfaceFrame and joined its display token to the
  SurfaceFlinger DisplayFrame. On the unchanged build it used the first
  same-thread Choreographer frame after the Emoji `Rune#rebuildKeys` section.
  The start time is `eventTimeNano` from the `MotionEvent UP` ancestor of
  `Rune#emojiConstruct`. Clock snapshots differed by less than 1 μs between
  monotonic and boot time. The endpoint is the DisplayFrame's `ts + dur`.
  All twelve captures used for analysis had zero trace import error and
  data loss counts.
  [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
  [AOSP DisplayFrame tracing](https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/services/surfaceflinger/FrameTimeline/FrameTimeline.cpp#1331)

| Build | Surface tokens → display tokens | Emoji key release to display endpoint, ms | Display classification |
| --- | --- | ---: | --- |
| Preliminary unchanged | 13188 → 13203 | 108.326 | On-time Present |
| Trace marker 1 | 16978 → 16985 | 27.223 | Unspecified Present |
| Trace marker 2 | 18655 → 18662 | 34.218 | Unspecified Present |
| Trace marker 3 | 20395 → 20402 | 40.859 | Unspecified Present |
| Trace marker 4 | 21991 → 21999 | **52.147** | On-time Present |
| Trace marker 5 | 23712 → 23719 | 32.312 | Unspecified Present |
| Unchanged repeat 1 | 26453 → 26460 | 39.201 | Unspecified Present |
| Unchanged repeat 2 | 28048 → 28055 | 39.565 | Unspecified Present |
| Unchanged repeat 3 | 29805 → 29812 | 40.136 | Unspecified Present |
| Unchanged repeat 4 | 31370 → 31377 | 27.318 | Unspecified Present |
| Unchanged repeat 5 | 33003 → 33011 | **50.748** | On-time Present |

The eight unspecified endpoints are retained as trace observations without a
presentation classification. In the classified trace-marker sample, the app
SurfaceFrame ended at 30.274 ms and the matching DisplayFrame ended 21.873 ms
later. The corresponding values for the classified unchanged repeat were
28.293 ms and 22.455 ms. That interval includes time after the app finished
its frame. The samples do not identify a single app routine as the cause or
establish behavior on physical hardware. Fold display coverage, manual
TalkBack, and the opening budget remain open.

## Build identities

The clean profile and debug APKs and trace-only profile built successfully.
The profile passed release lint vital in each build. Removing the marker and
rebuilding yielded the original profile hash. On-device APK hashes matched
the host files. The trace marker was applied in the disposable checkout only.

| Artifact | SHA-256 |
| --- | --- |
| Original and rebuilt profile APK | `d47b0e6a8b1979de187736effe30ade299707f65c630d753e23f1cd730401f13` |
| Trace-only profile APK | `7150c86932367a1edd7037cda7e5f5e52c9cc4849928224e156a368418f8a798` |
| Debug QA APK | `beed1896f2ad7077eb118fd6560968eaac5039dd26ea889742bc5be44f8b2b8b` |
| Temporary marker diff | `3d6ec432a64de7b041890c46117503566d09e9ffcb0cbf4689c7919c4b4dcd57` |

## Follow-up: reduce allocations during first catalog read

The reader now fills a bounded byte array directly and passes only its populated
range to the strict UTF-8 decoder. The shipped 142,268-byte TSV fits within
the initial 144 KiB. The buffer grows for larger inputs, with one extra byte
at the limit to detect overflow. Runtime validation, source order, and the
lazy entry decoding path are preserved. The reader still runs on the first
Emoji open.

An isolated OpenJDK 17 ARM64 differential check compiled the original and
modified `EmojiCatalog` with distinct package names and used the same packaged
bytes for both. After warm-up, six alternating-order pairs of 40 reads used a
fresh in-memory stream for each read and sampled thread allocations. The
original allocated 1,656,048 bytes per read. The changed reader allocated
1,136,760–1,137,096 bytes per read, a saving of 518,952–519,288 bytes
(about 31%). These are host allocation counts for parsing, with no font or
UI work. They do not measure retained heap, Android allocation counts, or
SurfaceFlinger latency.

The focused parser suite passed 19 tests. The full debug JVM suite passed
1,413 tests with zero failures, errors or skips, including exact TSV
reconstruction and acceptance at 320,000 bytes with rejection at 320,001.

On an isolated API 26 ARM64 emulator with 2 GiB RAM, the default-package
debug and Android test APKs built and their installed hashes matched the
host files. Six Android tests passed with zero skips: both font and tab
tests and four real-IME scenarios covering recents, the private editor, ZWJ
and flags, and modifier insertion/deletion. An earlier qualification-package
run passed the two font/tab tests and failed four real-IME setups because
the driver requires the default package. The rerun used that package with
the same product source. Fold and post-change presentation timing remain open.

## Paired API 37 comparison after the reader change

Six pairs compared the old reader at `663daba5` with the new reader at
`094a18e3` in the same profile build setup. The temporary grid marker had
the same diff hash as in the first experiment. Restoring just the old
reader produced the comparison APK. SHA-256 comparison of all 129 ZIP
member payloads found a difference only in `classes.dex`.

Both versions used the same API 37 image (build `15611780`), ARM64 software
renderer, 4 GiB RAM, 60 Hz virtual display and empty QA editor. Pair order
alternated. Each sample installed the appropriate APK, verified its bytes
on the device, ran ART speed compilation and confirmed the Rune process had
stopped before activating it in the editor. The samples ran after both
builds finished. Perfetto v58.2 found one catalog-read and one populated
grid marker per opening. All twelve resulting grid image crops matched
the prior populated reference. The Symbols-only control matched the prior
Symbols reference and emitted neither marker. No trace import error or data
loss counter was nonzero.

All values below are milliseconds. Draw start and DisplayFrame end are
relative to the release of the Emoji key. A dash in the display classification
columns denotes `Unspecified Present`.

| Pair | Catalog before / after | Draw start before / after | Display end before / after | Display class before / after |
| --- | ---: | ---: | ---: | --- |
| 1 | 1.131 / 1.095 | 6.022 / 14.824 | 45.237 / 35.171 | — / — |
| 2 | 1.439 / 1.102 | 7.164 / 8.354 | 29.492 / 51.847 | — / — |
| 3 | 1.010 / 1.115 | 12.534 / 8.691 | 32.990 / 31.051 | — / — |
| 4 | 1.236 / 1.110 | 9.155 / 6.084 | 31.895 / 27.905 | — / — |
| 5 | 1.243 / 1.176 | 13.929 / 14.706 | 34.842 / **50.750** | — / On-time Present |
| 6 | 1.219 / 1.377 | 13.720 / 17.487 | **49.466** / 39.032 | On-time Present / — |

Median catalog time was 1.228 ms before and 1.113 ms after. Median grid draw
start was 10.845 ms before and 11.698 ms after. This small series does not
establish a draw or presentation speedup. The 50.750 ms classified frame had
a Rune SurfaceFrame end at 30.450 ms. The trace associates surface token
`39656` with display token `39663`. For the classified comparison frame the
matching tokens were `44426` and `44434`. A supplemental
`dumpsys SurfaceFlinger --latency` returned the display period and no frame
rows for the thirteen captures. The ten unspecified FrameTimeline endpoints
remain diagnostic. The opening budget still has a confirmed miss in this
emulator setup. Physical Fold timing and accessibility remain open.

| APK | SHA-256 |
| --- | --- |
| Old catalog reader | `8073737d758d70289b985e3c1bc8ecdd5070992d090c15b34c7c92cdb51f6c6e` |
| New catalog reader | `edc0ce519b5bd8c0e1292907aba0427c58720df6a73426521cb7d9775d460271` |
| QA editor | `416c524f0f5f122dd37ccf46facea0aed11fcd68c850cf0dce68ffacbcb7caf0` |
