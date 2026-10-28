# Changelog

## Unreleased

- Correct local-learning privacy disclosures in English/Russian consent, the
  privacy policy and guide: word/phrase fragments, optional raw correction
  examples, deterministic hashes, bounds, incognito exclusions and separate
  reset controls are explicit. Disabling raw-example collection can still leave
  hash-only typo-pattern recording enabled; existing data is kept until reset.
  This changes copy only, not storage, consent defaults, model policy or release
  version metadata.

- Normalize native source/build paths at compilation and verify the exact F-Droid
  preparation delta without restoring removed wrappers. The renewed runtime is
  qualified with the exact model on Fold and ARM64 API 26/37 (16 KiB on API 37),
  including real self-test/scoring and production Binder/duty/idle checks.
  Normal and locally F-Droid-prepared unsigned APKs match byte for byte at
  180,096,157 bytes, including 9,957,040 bytes of native libraries. This uses the
  same host/toolchain/cache; independent build-server/distribution acceptance
  remains open. Isolated debug qualification uses its own application/storage;
  rejected IME test setup can no longer alter the owner IME during cleanup.

- Add the release `apkFootprint` gate with a 183,000,000-byte universal APK limit,
  a 185,000,000-byte unpacked limit and per-component/native-ABI budgets derived
  from the stripped review build. Budget changes require a reviewed source commit
  and a CHANGELOG entry; oversized compressed assets are rejected too.

- Strip packaged native libraries with the runtime's pinned NDK and verify all
  four APK libraries against stripped build outputs. The initial strip-only
  checkpoint preserved the existing runtime identity; the later source-path
  recipe above has its own renewed identity and execution qualification.

## 0.4.2 — 2026-09-16

- Ordinary letters are no longer dropped when a small upward finger drift rejects a secondary-symbol flick while the contact remains inside the key.
- Downward flick symbols, long-press alternatives, cancellation, accessibility and multi-touch delivery retain their existing behavior.
- Privacy-preserving diagnostics now distinguish verified autocorrection refusal stages without recording words, coordinates, key labels or hashes in metadata.

## 0.4.1 — 2026-09-16

- New neon Rune launcher artwork with a dedicated circular variant.
- Transparent adaptive-icon background, removing the extra blue backing around the artwork.
- Original icon artwork and five additional shape variants preserved in the source tree.

## 0.4.0 — 2026-09-15

- Five monochrome dark keyboard themes with borderless letter keys and taller rows.
- Downward key flicks for secondary numbers and symbols in English, Russian and Spanish; retained long-press accents and `ё`.
- A persisted key-flick toggle and an accessibility action for secondary symbols.
- A redesigned home screen with interactive keyboard preview and theme choices.
- Grouped, searchable settings with navigation back to the selected section.
- Shared menu controls no longer depend on destination activities, preserving the debug diagnostics boundary.
- MIT licensing, public contribution/privacy documentation, physical-device screenshots and F-Droid submission metadata.

## 0.3.2

Local autocorrection and candidate retrieval improvements. See the [dated acceptance report](docs/acceptance/2026-09-12-rune-0.3.2-autocorrection.md) for scope and evidence.
