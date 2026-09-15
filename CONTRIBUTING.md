# Contributing to Rune Keyboard

Thank you for helping improve Rune. Small, focused changes are easiest to review.

## Report a bug

Open a [GitHub issue](https://github.com/Mesteriis/rune.keyboard/issues) with:

- Rune version and installation source;
- Android version and device/screen configuration;
- selected languages and relevant settings;
- steps to reproduce, expected behavior and observed behavior.

Use sample text. Do not attach private conversations, passwords, tokens or unreviewed diagnostic exports. Crop notifications from screenshots.

## Develop

Follow the [README build instructions](README.md#build-from-source). Initialize the pinned submodule with `git submodule update --init --recursive`.

Use a branch for your change. Preserve the plain Android View architecture, existing behavior in protected fields, and the separation between input, model delivery and model inference. Do not introduce a network dependency into the typing path.

For a behavior change, add a regression test that exercises the user-visible case. Run relevant unit tests and lint. Before proposing a release or changing privacy/runtime boundaries, run the full commands in [RELEASE.md](docs/RELEASE.md).

Instrumentation tests change keyboard/settings state. Run them on a disposable emulator; do not run the complete suite on a personal phone. The CI matrix covers API 26 and API 37.

## Submit a pull request

Explain the problem and resulting behavior, include the exact checks you ran, and attach screenshots for visible UI changes. Mention untested cases. Keep unrelated formatting and generated evaluation outputs out of the patch.

Translations live in `app/src/main/res/values-*/` and `fastlane/metadata/android/`. Preserve resource placeholders and keep store descriptions consistent with implemented features.

By contributing original code, you agree to distribute it under this project's MIT License. Preserve third-party license notices and identify any imported material separately.
