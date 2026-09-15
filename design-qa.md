# Design verification — Rune 0.4.0

## Scope

Five dark monochrome keyboard themes, taller rows, a redesigned home/settings flow and downward key flicks for secondary symbols. Native Android Views implement the UI; the home preview uses the real keyboard component.

## Verified behavior

- Theme choices persist and apply to the keyboard; letters remain borderless while action keys differ by theme.
- Home preview supports typing, Unicode deletion and selection replacement without learning or persistence.
- Settings search finds controls, opens their section and preserves navigation/query state.
- Detail headers respect system insets. Earlier typography and empty-search hierarchy findings were corrected.
- Downward flicks enter one secondary character on release across EN/RU/ES. Retreat restores the primary letter. Cancellation, sideways escape, multiple pointers and reconfiguration discard pending input.
- Long-press accents and `ё`, spacebar language swipes and backspace cancellation remain functional.
- Flicks do not train touch geometry. An accessibility action exposes secondary symbols.

## Validation before release preparation

- Build, JVM tests and lint passed: **981 JVM tests**, zero failures/errors/skips.
- API 37 flick/regression run passed **10 tests**: five key-view cases, three real IME cases, language swipe across five themes and backspace cancellation.
- Earlier menu verification passed four menu cases and three additional controls/IME/consent cases. Initial fixture failures were corrected; failed runs were not counted as passes.
- English, Russian and Spanish hint rendering and the selected flick state were visually inspected at 1080 × 2340 on an emulator.
- Normal, large-text and landscape menu checks were completed during menu implementation. No new API 26 run was part of that phase.

## Physical screenshots

The [published screenshots](fastlane/metadata/android/ru-RU/images/phoneScreenshots/) were captured from the native app on a Samsung Galaxy Z Fold7 cover display, using only Rune's own home, settings and practice field. System bars and the edge handle were cropped from the 1080 × 2520 captures. No application pixels were redrawn. The temporary text is synthetic.

## Release preparation

The complete release boundary gate initially found that shared menu controls transitively referenced destination activities. Navigation callbacks now belong to the activities; the generic controls remain presentation-only. The existing diagnostic boundary and its negative fixtures pass without relaxing the checks.

Exact release validation and remaining limits are recorded in the release notes. Raw intermediate device logs and machine-local artifacts are intentionally not published.
