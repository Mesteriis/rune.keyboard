# Q1 — release footprint gate and compression-resistant budgets

`:app:apkFootprint` consumes the actual release APK directory from AGP's artifact
provider and selects its one SINGLE/unfiltered output from output-metadata.json.
It accepts the signed or unsigned basename declared there, without stale APK globs.
The task joins `check` and the CI build command; its Python regression task is a
dependency. CI uploads the JSON report and exact reviewed budget file, including
on failure. The CI configuration changed locally; no remote job is claimed here.

The baseline is the stripped release artifact bound to commit 551fcdf in the
u16-packaged-native receipt: 180,129,837 bytes, SHA-256
`cf9a51d5b65a4f359b2616d330b65b25d61e39e849fdd717c576e5a73dc8f71c`.
Limits in tools/apk-footprint-budgets.json are explicit source policy. The APK and
unpacked totals allow about 1.6%/1.5% growth from that artifact; category/ABI limits
have separate rounded headroom. The tool never recalibrates them. Changes require
a reviewed source commit, fresh measured basis, growth explanation and CHANGELOG.

| Component | Measured bytes | Maximum unpacked bytes |
| --- | ---: | ---: |
| lib | 9,983,936 | 10,500,000 |
| lexicon | 109,877,695 | 111,000,000 |
| experiments | 57,767,890 | 59,000,000 |
| res | 3,541,197 | 4,000,000 |
| dex | 741,796 | 1,000,000 |
| other | 305,759 | 500,000 |
| Unpacked total | 182,218,273 | 185,000,000 |
| APK file | 180,129,837 | 183,000,000 |

Native payload also has independent measured ARM64 (4,787,344 / 5,000,000) and
x86_64 (5,196,592 / 5,500,000) limits. These are native-byte limits inside the
universal artifact, not a measured ARM64-only APK or a new split distribution.
Container overhead (ZIP headers/signing/alignment/padding) has a 1,000,000-byte
limit. Every non-directory member belongs to exactly one category. Both declared
ZIP compressed/uncompressed sizes are reported; entries are not decompressed.
This is a size gate, separate from native integrity, privacy and runtime checks.

The report includes APK SHA-256 and the SHA of the exact budget bytes used, fixed
violation codes and passed status. APK identity/size/mtime/ctime are checked around
measurement/hash to reject an artifact changing during measurement. Budget
failures write passed=false and exit nonzero. Malformed policy/ZIP/metadata removes
an older report and exits nonzero; report paths cannot overwrite the APK, policy
or files inside its input artifact directory. JSON duplicate keys, duplicate/unsafe
ZIP members, nonempty directory entries and unknown/missing ABI sets refuse.
No payload strings or absolute source paths are exported in the report.

## Verification

- Eleven Python cases pass, including independently exceeded categories/ABIs,
  exact budget boundaries, appended ZIP padding, compressed growth, changed APK,
  stale metadata selection, malformed policy, failure reports and input safety.
- The Gradle footprint task and release privacy gate pass against the SHA-bound
  release APK. Its output is app/build/reports/apk-footprint/release.json.
- A closed negative fixture adds exactly 60,000,000 zero bytes under experiments
  using ZIP deflate. Its APK stays below 183 MB, but the gate exits 1 with
  UNCOMPRESSED_TOTAL and CATEGORY_EXPERIMENTS. Thus compressibility cannot hide
  the added payload. The fixture was not installed or published.
- The saved historical unstripped APK also exits 1 with APK_TOTAL,
  UNCOMPRESSED_TOTAL, CATEGORY_LIB and both native-ABI violations.
- The adjacent evidence binds the final tool/policy/Gradle/CI source, actual
  check exits, reports and artifact identities. No fresh ordinary typing replay,
  device test, native-model smoke, distribution build or publication occurred.

Q1 remains open for clean-source release enforcement, F-Droid/distribution and
release/model/device evidence. The strict source-path audit from U16 still fails;
this passing footprint check does not resolve it or grant release acceptance.
