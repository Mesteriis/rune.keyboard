# Q7 API 37 secondary-key gesture failure and targeted retry

The ongoing full Gradle-connected API 37 general suite failed
`KeyFlickImeInstrumentedTest.allThemesAndLanguagesCommitSecondaryCharactersWithoutTheBaseLetter`:
the editor contained `1@` where the fixture expected `1@?`. The full run was
performed on an AVD with hardware-key configuration and without the CI software
navigation option; a separate inset test also failed there. These facts do not
establish the cause of the missing gesture.

The same test and APKs were run alone on a newly created task-owned API 37
ARM64 emulator with the CI navigation option. It passed one test with zero
skips. The direct runner log SHA-256 is
`0041d6462e65730c14330efb64b55a8feb6b714434d1e2d6e74ec25a426bd9b5`
(`build/q7-flick-retry-api37-20261029.log`). The emulator was deleted. This is
one isolated pass under different conditions, not proof of the failure cause or
stability under the full suite. The original failure remains a failure; the
full run and hosted CI must still be evaluated. No physical device was used.

## 2026-11-24 recurrence with software navigation configured

The full Gradle-connected run at `40e45595` reproduced a failure at the
same assertion on the 16 KiB ARM64 API 37 AVD launched with the requested
software-navigation option. This time the field contained `1@@` after
the fixture expected the point-key flick to append `?` to `1@`. The
preceding two field assertions passed. The live stack identifies the
assertion immediately after `flick(".")`.

The failure capture shows the composing field focused in Rune and a
distinct period button visible to accessibility at `[841,2116][936,2263]`.
The `a` button is separately visible at `[63,1822][168,1969]`.
Those are post-failure bounds. The capture contains no record of the node
selected before the swipe or which key received its DOWN event.
The isolated pass above remains useful as a positive control. The new
failure establishes recurrence after configuring software navigation.
The cause remains open.
