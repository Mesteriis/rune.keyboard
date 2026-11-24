# Q1: local F-Droid binary scanner

The unsigned APK from the [current-source local F-Droid build](2026-10-29-q1-current-fdroid.md) was checked with `fdroidserver.scanner.scan_binary` from fdroidserver 2.4.5, using its configured cached SUSS signatures and Android build-tools 36.0.0 `dexdump`. The APK was the 180,122,901-byte artifact from source commit `1b3d8c332d388c5434d786a5ef2a532ec75cb009`, SHA-256 `5ed8115a4d985029704e0580824054587a0906f59b392bc58d0318187a958f7c`. Its identity was verified before and after scanning.

The scan returned **zero problems**. Network access was blocked; the local scanner loaded 471 error code signatures and no warning code signatures. One `dexdump` invocation succeeded and the scanner extracted 173 class-name matches. These are the scanner's matches, not a count of every class in the APK. The scan also invoked its APK signing-block inspection on this unsigned artifact. Raw script and output are in ignored `build/q1-fdroid-binary-scan-20261029.py` and `build/q1-fdroid-binary-scan-final-20261029.log`.

This is a local signature-based scan of the specified earlier APK, not a new release, independent build-server run, scan of a signed artifact, or proof of complete security or licensing review. The source snapshot, F-Droid build and ordinary local build are described in the earlier receipt. The newer review commits have not been built and scanned here. The independent build server, source export and distribution acceptance remain open.

At clean source commit `fd37bcf8`, a fresh isolated run used fdroidserver
2.4.5 with the previously recorded scanner SHA-256
`4de525a85ba519a41838cf1ed7e70184d0b9df782da8a6c82c6dea5234adf7e1`.
The real source scanner, with network disabled and all 31 exact data-policy
entries verified, returned zero fatal findings and the same two warnings:
the calibration gzip and upstream Keynote file. It loaded 114 error Gradle
signature patterns.

A separate clean offline `:app:assembleRelease` produced an unsigned APK of
180,122,901 bytes, SHA-256
`d9c746f834852766115bd81667a5c5eb0548e5c1c4627857484c976ee8e8c115`.
The real binary scanner, again with network disabled, reported zero problems,
used 471 error signatures and invoked `dexdump` once; 173 scanner class-name
matches were found. The APK hash was unchanged across the scan. These are
local source and binary scans, not an F-Droid `build_local`, build-server run,
signed release, device test or distribution acceptance. Both temporary
checkouts, scanner environments, caches and APK were removed.

At source commit `6c58cd0c`, the actual fdroidserver 2.4.5 source scanner was
run again in a temporary clean Git checkout with no initial root `build/` and
the pinned llama.cpp source exported from its local Git object. The exact
31-entry data policy passed; the scan used its 19 exact ignore paths and five
delete paths, leaving seven inventory-only paths. It reported zero fatal
findings and two warnings, classified as an executable binary and a gzip
archive. It loaded 114 Gradle error signatures. The scanner module SHA-256
was `4de525a85ba519a41838cf1ed7e70184d0b9df782da8a6c82c6dea5234adf7e1`,
and the embedded SUSS default string SHA-256 was
`c262fb68063777dad15ff701b07bbb1b3a9c9e19aa623a0ddea524ff0a5c3a33`.
The signature controller was explicitly set to use those embedded defaults;
Python socket TCP connection entry points were disabled during the scan, not
an OS-wide network isolation. The temporary scanner environment, package cache
and checkout were removed. The policy's 12 tests and prepared-source policy's
15 tests also passed locally. No new APK, binary scan, F-Droid build-server
result, signed release, hosted CI or device result is implied.

At source `b1cb9162`, a clean Git checkout with the locally initialized pinned
llama.cpp submodule and no initial root `build/` passed offline release
assembly, release privacy, APK footprint, IME boundary, forbidden runtime
dependency and native-symbol gates. It used the installed Gradle 9.4.1, JDK 17,
Android SDK/NDK and read-only dependency cache, with a temporary Gradle user
directory and build cache disabled. The unsigned APK was 180,122,901 bytes,
SHA-256 `cba4547513ac38e436755290495ca231e6f24e592bb0ce6b2d0f478c804ffbf0`.
The actual fdroidserver 2.4.5 binary scanner reported zero problems: one
successful `dexdump`, 173 scanner class matches, 471 error signatures and
zero warning signatures. The scanner and embedded SUSS default hashes match
the source-scan values above; the APK hash was unchanged during scanning.
Embedded defaults were selected explicitly and Python TCP connection entry
points were disabled during the scan; this is not OS-wide network isolation.

Three earlier setup attempts failed and are not passes: the read-only Gradle
cache was first pointed one directory too deep; a later native compile hit a
temporary-path length limit in `sccache`; and a third stopped at the release
source guard because the locally cloned submodule was not registered in Git.
The final run used the correct cache root, a short temporary path without the
shared compiler cache, and a separately verified initialized submodule. The
temporary checkout, Gradle outputs, scanner environment, package cache and APK
were removed. The native-symbol gate ran, but the additional packaged-APK
`--require-no-local-paths` mode was not invoked in this run. This was a local
unsigned build and scan, not F-Droid `build_local`, a build-server result,
signed release, hosted CI or physical-device acceptance.

At source `67177669`, a separate clean offline unsigned release assembly and
the native-symbol gate passed with the pinned initialized llama.cpp submodule.
The APK was 180,122,901 bytes, SHA-256
`4270e0253a4eec4351022a5f9e822b4b85a237a728b0caa19335439600d70ada`.
`tools/verify-native-runtime.sh` with `--require-no-local-paths` passed for
both supported ABIs: all four packaged libraries matched the stripped build
outputs byte for byte, and the APK hash was unchanged by the check.

The path check now also rejects common temporary directory and Homebrew path
prefixes in addition to `/Users/` and `/home/`. Eight focused tests pass,
including negative path cases and a permitted Android path. This is a check
for the specified prefixes, not proof that every possible host path is absent.
An initial test invocation using a package-qualified module name failed on its
import; the documented unittest discovery invocation passed all eight tests.
The clean build and APK were removed after verification. This APK was not
scanned by F-Droid, installed on a device, signed or built by an independent
build server; the scanner result above applies only to its identified APK.

## Source scanner after historical exclusion expansion

On `56b61eecfbef37714a7d221ee6538f3c0e441b19`, fdroidserver 2.4.5 ran
`scan_source` on a temporary clean Git checkout with its pinned initialized
llama.cpp submodule and no initial root `build/`. The exact data policy passed:
19 ignore paths, five delete paths and seven inventory-only paths. The scanner
reported zero fatal findings and two warnings: the previously disclosed
calibration gzip and upstream Keynote file. The 114 Gradle error signatures
came from embedded SUSS defaults; the scanner module and default signatures
matched the SHA-256 values documented above. Python TCP connection entry points
were disabled during the scan; this is not OS-wide network isolation.

An initial setup exited before scanning due to a mistyped expected SUSS hash;
the package's actual module and default hashes were independently checked
against the pinned package, the typo was fixed and the scan above passed. Both
temporary checkouts and scanner environments were removed. No binary scanner,
F-Droid `build_local`, build-server, hosted CI, signed release or device
acceptance is implied by this source scan.

## Current clean release, strict native and binary scan

At `bf63b7da651d18899ad28346a9eaba2f006c8af6`, a temporary clean checkout with
the pinned llama.cpp submodule passed the source checkpoint before and after
offline release assembly, release privacy, APK footprint, IME boundary,
forbidden runtime dependency and native-symbol gates. The unsigned APK was
180,122,941 bytes, SHA-256
`3a964e735b977382c0a8a2ea0062bcd4abb0727b7d2e0a924a619fb39eef3710`.
The strict native runtime verifier passed for both supported ABIs, including
packaged/stripped byte matching and the specified local-path refusals.

The actual fdroidserver 2.4.5 binary scanner returned zero problems for that
APK. Its pinned scanner module and embedded SUSS defaults matched the hashes
above; it loaded 471 error signatures and zero warning signatures. Android
build-tools 36.0.0 `dexdump` succeeded once and the scanner found 173 class
matches. The APK hash remained unchanged during scanning. Python TCP connection
entry points were disabled during the scan, not OS-wide networking.

The temporary checkout, APK, Gradle outputs and scanner environment were
removed. This is a local unsigned build and scan, not F-Droid `build_local`,
independent build-server reproducibility, hosted CI, signing or Fold acceptance.

## Clean source and unsigned APK at 1a7916f8

A clean clone with the pinned llama.cpp submodule passed the release source
checkpoint before and after the offline Gradle 9.4.1 build. Release assembly,
privacy, footprint, IME boundary, forbidden runtime dependency and native
symbol tasks exited zero. The strict packaged native check passed for ARM64
and x86_64. The unsigned APK was 180,122,941 bytes with SHA-256
`1a29befa30b154e76daaf04d5675cb75c2ea108cf15efbc0091af6dde4e091a1`.

In a separate clean clone, the F-Droid data policy verified 33 entries.
The actual fdroidserver 2.4.5 source scanner reported zero fatal findings
and logged two warnings for the calibration gzip and the upstream Keynote
file. The source scan applied 19 exact ignore paths and five declared
deletions. After the scanner cleanup and F-Droid signing scrub, the prepared
source guard verified all 11 approved changes.

The binary scanner initially stopped during SDK setup because the test
driver had left its Java mapping unset. The corrected driver supplied an
empty Java mapping and selected Android build-tools 36.0.0. A traced scan
confirmed one successful `dexdump` invocation, 173 scanner class matches
and zero reported problems. The APK hash stayed identical throughout.
The scanners used the same verified module and embedded SUSS hashes
recorded above, with Python TCP connection entry points disabled.

Both ordinary and scanner-prepared sources assembled successfully at
`1a7916f8`, but the APKs were **different**. The prepared APK was the same
size and had SHA-256
`e9047d0078cb96646787e2900e352913e32fbe7ae3d6e4694d7e222e7caa26c0`.
All 129 unpacked entries were compared. Only the two `librune_llama.so`
files differed. In each file, the 20 differing bytes were the GNU Build ID
descriptor. The unstripped ELF debug strings contained the checkout path as
passed to Clang. CMake normalized the resolved path prefix but Clang also
received the symlink spelling of the source root. This comparison failed the
byte parity check.

A candidate CMake change added prefix maps for both path spellings. Both
isolated candidate builds stopped at `QUALIFICATION_METADATA_DRIFT:RUNTIME_BUILD_ID`
before compilation. The runtime identity binds the CMake recipe. The
candidate was removed from the working checkout and the qualification
identity was preserved. The subsequent comparison used the original
committed source and clean checkouts addressed by canonical paths.

Passing the resolved temporary directory to Gradle was insufficient on this
host. Both builds passed their source and strict native gates, but their
APK hashes still differed because the compiler command continued using the
`/tmp` spelling. The next repeat used two fresh directories outside the
system temporary symlink. The actual compiler commands then used the same
checkout path spelling as their debug prefix maps.

The two unaliased clean checkouts produced byte-identical unsigned APKs:
180,122,941 bytes, SHA-256
`1170a173870bd5214577faf4da577cc7d7f8dbfec4178a1bccd54850f084f114`.
Both strict native gates and both source checkpoints passed. The binary
scanner returned zero problems for this digest, with one successful
`dexdump` and 173 class matches. The 29 F-Droid policy tests and eight
packaged-native tests passed. All task copies, APKs, logs, isolated Gradle
homes and the scanner environment were removed. Independent F-Droid
build-server acceptance and parity for a checkout reached through a symlink
remain open.

## Current recovered-v6 source snapshot

At `d22466f1`, a clean Git source archive plus the pinned llama.cpp submodule
archive passed the 35-entry F-Droid data policy. The actual fdroidserver
2.4.5 `scan_source` returned zero fatal findings using 19 declared ignore
paths and five declared deletions. The two existing warnings remained for the
calibration gzip and the upstream Keynote file. The two recovered v6 archives
were covered by the inventory and did not add source-scan findings.

The scanner module and embedded SUSS default digests matched the earlier
test. The fresh scanner environment installed the pinned version online after
the offline cache did not contain it. Python TCP connection entry points
were disabled during the scan. This was a local source scan of the clean
snapshot. The independent F-Droid builder and publication review remain open.

An ordinary clean Git clone of the same source and pinned submodule passed
offline Gradle 9.4.1 release assembly, lint vital, release privacy, IME
intelligence boundary, forbidden runtime dependencies, native symbol gate
and APK footprint. Both ABI payloads passed the strict native package check.
The clone was clean after the build. The unsigned APK was 180,122,941 bytes
with SHA-256
`08ad193c53afe6c8c5ac1044ff8c3e28543e83893d9eae9d769ed3f52d24b680`.
The actual fdroidserver binary scanner returned zero problems, with one
successful `dexdump` call and 175 scanner class matches. The APK hash stayed
identical. The unsigned binary was built through the ordinary Gradle entry
point. F-Droid `build_local`, an independent build server and signing were
outside this run.

## 2026-11-23 independent Linux release comparison

Both builds used a clean checkout of `88b815308970048701752222975a2f57e259cdab`
and llama.cpp `36b10154383b60eb15baac2c7a40d2a5f784faa7`. The release source
check reported zero status entries and one matching submodule on both systems.
The first disposable checkout's source check refused the inactive submodule
after its URL entry was removed. Restoring the URL from `.gitmodules` made
the submodule active and the check passed.

The Linux build used the official F-Droid Debian trixie image on `linux/amd64`,
digest `sha256:1ea8bef1820bff06c2974e31b4fc4c79c364cd24231b86e71fa4b926797e0dac`,
image source revision `8f52ae3ce287bc28964db544b970b88dce9c38bf` and Debian
OpenJDK 21.0.12.1. Gradle, SDK platform `android-37.0` revision 2, build-tools
36.0.0, NDK 29.0.14206865 and CMake 3.31.6 were provisioned in the disposable
container. It read the trusted source checkout through a read-only mount. It
used an empty Gradle home and had no macOS SDK or dependency-cache mount.
[Official buildserver image definition](https://gitlab.com/fdroid/fdroidserver/-/blob/8f52ae3ce287bc28964db544b970b88dce9c38bf/buildserver/Dockerfile)

The macOS Arm64 reference used JDK 17, an isolated Gradle home and the installed
SDK and read-only dependency cache. Gradle ran offline and returned zero after
`assembleRelease`, `privacyGateRelease`, `nativeSymbolGate` and `apkFootprint`.
The strict package verification passed for both ABIs. The unsigned APK was
180,122,941 bytes, SHA-256
`724531e2573ca244078058cbb422996454467f0f9b957e796644dd1157a9d251`.

Separately, the fdroidserver 2.4.5 source scan examined a Git export of this
commit and its pinned submodule. It matched the 35-entry data inventory, used
19 exact ignore paths and five deletions, and returned zero fatal findings.
The two established warnings were the calibration gzip and the upstream
Keynote file. The package scanner used pinned SUSS defaults with network
disabled. The macOS-built APK scan returned zero problems and used one
successful `dexdump` call.

The Linux build completed in 12 minutes 52 seconds after provisioning. All
four Gradle gates passed. The unsigned APK is 180,122,757 bytes, SHA-256
`516a49a513db3cfcc23c30224ffc57ac2c67df21cf2b72dd03ebaa86be12888f`.
The strict native package check verified both ABIs against copied Linux
stripped outputs. The fdroidserver 2.4.5 scanner ran on that exact Linux-built
APK, returned zero problems and used one successful `dexdump` call. Its hash
was unchanged by scanning. Both APK scans ran on macOS. An in-container
scanner setup stopped because that image lacked `ensurepip`.

The APKs have the same 129 ZIP entries in the same order. Of those, 127 have
identical uncompressed bytes, including both `libc++_shared.so` libraries.
Only the two `librune_llama.so` entries differ. Each Linux ELF is 184 bytes
smaller. Its section set is unchanged and 24 section payloads compare equal,
including the executable code. The two differing sections are the 36-byte
`.note.gnu.build-id` and the toolchain strings in `.comment`, 523 bytes on
macOS and 335 on Linux. The cross-platform whole-APK reproducibility check
therefore remains open.

This used the ordinary Gradle release command within the F-Droid container
image on a local Arm64 Docker host. An actual remote F-Droid build-server
job, signed distribution and release smoke on Fold remain open.

## 2026-11-24 published APK baseline

The GitHub Releases API reported `v0.4.1` as the latest public release.
The downloaded 202,892,432-byte APK matched both the GitHub asset SHA-256
and its published checksum file. Android Build Tools 36.0.0 verified the
single APK Signature Scheme v2 signer and 16 KiB ZIP alignment. Package
inspection reported `io.github.mesteriis.rune.keyboard`, version code 7
and version name `0.4.1`, with API 26 minimum and API 37 target.
[Published release](https://github.com/Mesteriis/rune.keyboard/releases/tag/v0.4.1)

| APK entry | Bytes | ELF debug sections |
| --- | ---: | --- |
| `arm64-v8a/libc++_shared.so` | 1,374,336 | No |
| `arm64-v8a/librune_llama.so` | 45,084,920 | Yes |
| `x86_64/libc++_shared.so` | 1,337,488 | No |
| `x86_64/librune_llama.so` | 44,846,144 | Yes |

Both Rune libraries export `JNI_OnLoad`. All four libraries' ELF LOAD
alignments are 16,384 bytes. The current footprint verifier refused this
published APK with `APK_TOTAL`, `UNCOMPRESSED_TOTAL`, `CATEGORY_LIB`
and both native ABI budget violations. This provides a real published
negative control for Q1's strip and size checks.

The local `v0.4.2` annotated tag points to `d332c0e`. The public remote
lists `v0.4.0` and `v0.4.1` under `v0.4.*`. The official package page
and package metadata path in F-Droid's master branch both returned HTTP
404. Signed review-candidate distribution, the remote F-Droid build and
the Fold release smoke remain open.
[F-Droid package path](https://f-droid.org/packages/io.github.mesteriis.rune.keyboard/)
[F-Droid metadata path](https://gitlab.com/fdroid/fdroiddata/-/raw/master/metadata/io.github.mesteriis.rune.keyboard.yml)
The task container, downloaded image, temporary source checkouts, caches and
both APKs were removed after verification.

## Local F-Droid source scan on the CI candidate

Candidate `0ecfca8c951d2` was exported with the pinned llama.cpp
submodule into two disposable source trees. A source-only export used
a local policy projection that omitted the two absent v3/v4 archive
entries. The hosted-style tree included the exact reconstructed
archives, verified by the replay command, and used the candidate's
unmodified inventory. The resulting inventories had 32 and 34 entries.

The actual fdroidserver 2.4.5 source scanner passed on both trees with
zero fatal findings, 19 exact ignore paths and five deletions. The
scanner module and embedded SUSS digests matched the earlier pinned
run. The only scanner warnings were the existing calibration gzip and
the upstream Keynote file. TCP entry points in the Python scanner were
disabled after provisioning. The scanner environment and both source
exports were removed. The 32-entry policy was confined to the probe.

A fresh Git checkout of the same candidate passed the workflow's offline
Gradle build, lint, both privacy gates, IME boundary, forbidden runtime
dependencies, native symbol gate and APK footprint. Gradle returned zero
in 4 minutes 15 seconds. All eight packaged-native tests and the strict
native package verifier passed on the unsigned release APK.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Debug APK | 183,186,249 | `c8b6597a9b9d50f9f83922195907828b53abb49f075d18938eda3f09a453e36c` |
| Profile APK | 180,127,437 | `a34fb1feb16105ad1c889504cebf7e9f9df69d5b8c863a138213e2c97659dd07` |
| Unsigned release APK | 180,123,301 | `2412fde19cc0918fc57e636e478e9728d9da669186b796c37464c4626656b82d` |

The footprint receipt SHA-256 was
`5b8cc494990ffa821b5e7a05319753e473ab90f3e3f3617c2ee2a867767731fc`.
The local builds used the installed SDK and dependency caches. The
checkout, generated APKs and temporary logs were removed. The hosted
build, exact APK scan with fdroidserver, distribution and physical
device acceptance still require separate evidence.

A second independent local checkout of `0ecfca8c951d2` repeated offline
release assembly, release lint, privacy, dependency and footprint gates.
Its 180,123,301-byte unsigned APK had the same SHA-256 as the previous
build, `2412fde19cc0918fc57e636e478e9728d9da669186b796c37464c4626656b82d`.
The strict native package verifier passed again.

The actual fdroidserver 2.4.5 binary scanner ran on this exact APK using
the same pinned scanner code and embedded SUSS defaults. It returned
zero problems, with one successful Android build-tools 36.0.0
`dexdump` invocation and 173 scanner class matches. The APK SHA-256
was unchanged after the scan. The scanner log SHA-256 is
`556a7a1680df52b1f2eda3fc5ff3206dce3bf21cbbbdaf212f26f7f5c275d7c5`.
The temporary checkout, unsigned APK, scanner environment and logs were
removed. This establishes local binary-scan evidence for the candidate.
Signing, the remote F-Droid builder and distribution remain open.

### APK parity across review-only commits

Two fresh offline release checkouts verified the builds at
`0ecfca8c951d` and `0d1a40b919ea`. Both APKs contain 129 ZIP
entries and have size 180,123,301 bytes. The older revision reproduces
`2412fde19cc0918fc57e636e478e9728d9da669186b796c37464c4626656b82d`.
Two builds of the newer revision both produced
`dfe77780e969722137fc6dbeea66bc45466800ff14f6d92389776a4d941bbb4c`.

Only `META-INF/version-control-info.textproto` changed content.
The 128 other entries, including DEX and all four native payloads,
matched in both compressed and uncompressed bytes. Two ZIP entry
offsets shifted. A separate Gradle extraction produced the expected
revision in each 120-byte metadata file. Substituting the same
revision token in both made the metadata byte-identical.

The APK comparison receipt SHA-256 was
`1daa83ef2cf2c6b700ceacbe23aeab10dc229ba6c1497e0ee965537b2d43d739`.
The metadata receipt SHA-256 was
`63b28ab52ba0aaefe56b4f527ce6674e0767f4baabd4240d6a050f777c1e04ce`.
The checkouts and APKs were removed. The earlier F-Droid binary
scan applies to the recorded older APK. Published signing and the
remote build remain separate acceptance requirements.

### Release scan for the prepared CI candidate

A clean checkout of `4cb8066907b815c45dc7f6bb75eba0e0de8c73ec`
passed offline Gradle release assembly, release lint and privacy, the
IME and forbidden-dependency checks, the native symbol gate and the APK
footprint budget. The unsigned Rune 0.4.2 APK (version code 8) was
180,123,301 bytes with SHA-256
`595d48596414167acb18aab40d849375b47a92016fc21d08b7a44048ca95ff56`.
Android build-tools verified 16 KiB ZIP alignment and package metadata.
The strict native verifier passed, and all four packaged native library
digests matched the prior locally qualified build. The complete APK
digest differs from that of the prior build.

The pinned fdroidserver 2.4.5 binary scanner reported zero problems,
one successful dexdump invocation and 173 class matches. The APK digest
was unchanged by the scan. The scanner log SHA-256 was
`556a7a1680df52b1f2eda3fc5ff3206dce3bf21cbbbdaf212f26f7f5c275d7c5`.
The temporary checkout, APK and scanner environment were removed.
Hosted CI, the independent F-Droid builder, signing and the physical
Fold check for this candidate remain open.

### Release scan after the English pronoun boundary fix

Candidate `94819126a417435afec503acc8d49e873f401972` passed offline
release assembly, lint, privacy, the IME boundary and forbidden-dependency
checks, the native symbol gate and the APK footprint budget. The strict
native package verifier and 16 KiB ZIP alignment check passed.

The 180,123,301-byte unsigned APK has SHA-256
`5da83b97e9e94e91546b6a0ea5cbe0094f43a9c5c1323fa0c3b2c9f15b9a3f9d`.
The digest-pinned fdroidserver 2.4.5 scanner returned zero problems,
one successful dexdump invocation and 173 class matches. The scan
left the APK digest unchanged. The scanner log SHA-256 is
`556a7a1680df52b1f2eda3fc5ff3206dce3bf21cbbbdaf212f26f7f5c275d7c5`.
The unsigned APK, temporary checkout and scanner environment were removed.
Hosted execution, independent signing and the Fold check remain open.

### Release scan of the refreshed hosted CI candidate

Candidate `123d0a5246b4e173a787102ede60b24c8cdc786d` and its pinned
llama.cpp gitlink were checked out into a clean temporary repository.
Offline Gradle passed lint, release assembly, release privacy, the IME
intelligence and forbidden-dependency gates, native symbols, and the APK
footprint budget in 2 minutes 27 seconds. Gradle executed 127 tasks and
restored 71 from cache. The Gradle log SHA-256 is
`0048d938eaf0ff43952acfd2f22a741052c7832bc7bec4ef41de4f20de24ca3a`.

The unsigned APK is 180,123,301 bytes, with SHA-256
`9b3e63624384a45dd15674bf0bfdfe125c207637c9f5861920d510d3c1309e88`.
The strict verifier passed for all four packaged native libraries
across arm64-v8a and x86_64. ZIP alignment passed at 16 KiB. The
digest-pinned fdroidserver 2.4.5 scanner used its bundled signatures
with networking disabled, reported zero problems and 173 class
matches, and left the APK digest unchanged. There was one successful
dexdump invocation. The scanner log SHA-256 is
`556a7a1680df52b1f2eda3fc5ff3206dce3bf21cbbbdaf212f26f7f5c275d7c5`.

The repository, build outputs, scanner environment and APK were deleted.
Hosted build-server validation, signed distribution and physical Fold
acceptance remain open.

### Release scan with the A2 and editor changes

Candidate `75d06f6f3de543baea505a33e79614ea5867a1c5` and its pinned
llama.cpp source were checked out in a temporary repository. Offline
Gradle passed lint, release assembly, privacy, IME intelligence and
forbidden-dependency gates, native symbols and APK footprint. Gradle
executed 127 tasks and restored 71 from cache. The build log SHA-256 is
`1c396d077d266fbdd3e91fb2181204309e50ff7eec008c2724f9f59cd7f31763`.

The unsigned APK is 180,123,301 bytes, with SHA-256
`fb1e51327f975cdba75878896ad57991d9b16304e040550724061ceab45bc829`.
Strict packaged native checks passed for both libraries on each ABI.
Combined library sizes were 4,773,648 bytes on arm64-v8a and 5,183,392
bytes on x86_64. ZIP alignment passed at 16 KiB. The digest-pinned
fdroidserver 2.4.5 scanner reported zero problems, 173 class matches
and one successful dexdump invocation. It left the APK digest unchanged.
The scanner log SHA-256 is
`556a7a1680df52b1f2eda3fc5ff3206dce3bf21cbbbdaf212f26f7f5c275d7c5`.

The temporary repository, scanner environment, build outputs and APK
were removed. The signed release, independent build-server result and
Fold smoke test remain open.

### Release scan with the same-window U14 row

The clean checkout of candidate `687361c8ac48eee16217c23b7510c18129817f6f`
and its pinned llama.cpp source passed offline lint, release assembly,
privacy, IME intelligence and forbidden-dependency gates, native symbols
and APK footprint. Gradle executed 127 tasks and restored 71 from cache.
Build log SHA-256 was
`c2bdb77aca38e7ec80c9d67cc21844c58bb58c3b4cfdefd13f5abb52e4e4ecd4`.

The unsigned APK measured 180,123,301 bytes, with SHA-256
`60a44e088b300db51fc5cd24269603548c420ec0da527ad4daf43daced603f3b`.
All four packaged native libraries passed strict validation and the APK passed
16 KiB ZIP alignment. The offline, digest-pinned fdroidserver 2.4.5 scan
recorded zero problems, 172 class matches and one successful dexdump.
The scan preserved the APK digest. Its log SHA-256 was
`89ef9a057c2e1a4b91a6bf8df112f4d33ca4c41b107da88f32642a4dc341b6b2`.

The temporary checkout, scanner environment, build outputs and APK were
removed. Signed distribution, the independent build-server result and
the Fold smoke test remain open.
