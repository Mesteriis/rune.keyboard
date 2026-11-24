# U14 authored short-word expanded-order check

The actual current-controller candidate-order observer ran twice for the three
previously disclosed `мето`, `двох` and `собй` cases. The projections matched
and no external model was called. For each case the two visible correction IDs
are the exact prefix of the seven-item validated order; all the observed
candidate contexts were already registered in both public ledgers.

This corrects the earlier wording that `двоих` was an ordinary visible
suggestion: it is the third generated correction but is hidden by the current
two-correction strip. `метро` is fifth and also hidden. `собой` is first and
visible. The existing expanded row is opt-in and can offer hidden candidates;
the controller-order observer itself does not select an item or prove the UI.
These are disclosed synthetic controls, not independent ranking qualification.

The `russianMetroIsSelectableFromExpandedSuggestions` instrumentation case
sets Russian and manual expansion on the task-owned emulator, types `мето`,
opens the row and selects `метро`. It passed once on API 26 and once on API 37,
without skips. The editor contained `метро` after selection. The debug APK SHA-256
was `2f61e8102f535107107fdd15cf1140fff1da529b4c976d742bb4f8f92b7cf4f4`;
the instrumentation APK SHA-256 was
`8b8ebe500c1eccc429708b8284dcf8538c9bc3260b170da8e3b58ec43ce0771c`.
Logs are `build/u14-metro-api26-20261029.log` and
`build/u14-metro-api37-20261029.log`. Both task-owned emulators were deleted.
This is a manual suggestion selection, not an automatic-correction test.
Fold layout and manual TalkBack remain outstanding.

The local two-pass replay and bound receipt are in
`build/q5-short-hidden-order-20261029/`.
