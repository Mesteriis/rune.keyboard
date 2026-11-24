# U9: follow-up on black IME captures

The [preceding five-sample trace](2026-10-28-u9-live-ime-trace.md) was initially
reported as having three black captures. That claim was wrong: the original PNG
pixels were rechecked and all five keyboard-area crops are byte-identical to the
visibly populated grid in sample 1. The apparent black captures resulted from
our interpretation of the image preview, not from those stored screenshots.
The separately captured later and post-tap images have that same crop identity;
the previous claim that a tap restored visibility is also withdrawn.

The same task-owned API 26, 2 GiB ARM64 emulator and the exact same installed
profile APK (`5ba876ef07c0bf30f3d2fc74f3fb18ae1fe5a8376eefb0b46cacc704bd36f3a4`)
were used with the separate public QA editor. On five untraced iterations, the
system IME was selected and captured, Rune's profile process was force-stopped,
Rune was selected, then ADB taps opened Symbols and Emoji. Three screenshots
were captured starting about two seconds after the Emoji tap, followed by one
after tapping a category tab. Five subsequent traced iterations used the same
sequence with `am app view gfx` atrace enabled. This was a sequential,
unrandomized series on one emulator, not a paired fresh-device experiment.

All five system-IME controls showed its keyboard. All 30 Rune screenshots before
the tab tap showed the same populated emoji grid: their 1080×610 keyboard-area
pixel bytes are identical, and representative images were inspected. The ten
post-tab screenshots also show the grid. Each traced iteration contains one
profile start-process marker, one `Rune#createInputView`, one
`Rune#emojiConstruct` and one `Rune#emojiCatalogRead`; all five trace-import
error/data-loss checks returned zero nonzero rows. The control screenshots were
taken in the untraced series only.

The first screenshot is seconds after the tap, so these results cannot establish
the first presented frame, the 50 ms budget, a physical Fold result, or absence
of an intermittent bug. No black screenshot was established in either series.
Source HEAD was
`748cf8305c333c7d3cf07f79283a26c1f94100f6`; the installed profile APK matched
the prior run. Screenshots and atrace files remain under
`build/review-u9-redraw-20261028/`. The task-owned emulator was stopped.
No production code, APK, phone or performance threshold changed.
