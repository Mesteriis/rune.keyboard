# U18: API 29 navigation modes

Installed the Google APIs ARM64 API 29 SDK image and created a task-owned
emulator. The gestural overlay and then the three-button overlay were selected
and read back. In each mode the palette-change/text-preservation test and the
settled synthetic screenshot capture passed (`OK (2 tests)` per mode). The QA
editor contained only `h`. Visual inspection of all four screenshots found the
gesture handle and three-button icons distinguishable in both palettes; this is
not a measured contrast guarantee.

Logs and captures are retained in `build/review-u18-api29/`. SHA-256 of the
gesture log is `090edb39f7b49118d661a489e4e31d786a2eb4cbb65a8ec1eb2d22c1b624863f`;
the button log is `591465546b851e44838c17d582bc39df6973849e20e60ac00916caf9903ff0ef`.
Debug APK SHA-256 was `111afa4e09889499ea35318bcb2c4fd6b56892e15b44e101f02a382ff3cc1e40`;
test APK was `fc29b82104601ac073874a137bc8918c2f49fa6e464240db38dc20184310ea39`.
The SDK image remains installed for future tests. The temporary emulator was
stopped and removed. Fold, manual accessibility and distribution acceptance
remain separate work.
