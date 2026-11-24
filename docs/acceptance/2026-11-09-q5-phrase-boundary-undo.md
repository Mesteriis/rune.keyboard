# Q5: Undo for each observed phrase correction

The full 9,543-phrase controller replay was repeated twice at the current
product source; both outputs matched. It contained the same 156 automatic
boundary edits as the prior recorded replay. The original phrase observer
checked Undo only for 33 edits on a phrase's last word.

For each of the 156 observed edits, a separate controller/editor session was
replayed through that word, and its text immediately before and after the
boundary was required to match the full-phrase observation exactly. Backspace
then had to return `HANDLED` and restore the exact pre-boundary text. All 156
checks passed: 94 edits on the first word used the existing single-word observer,
and 62 used the full multiword observer. The latter include the previously
checked 33 final words and 29 earlier positions. The selection and evidence are
bound to source, assets, registries, toolchain and original result hashes in
the [numeric receipt](2026-11-09-q5-phrase-boundary-undo-evidence.json).

This is a replay of separate sessions up to each position. It does not check
what happens after Undo when the original full phrase continues, nor does it
cover real Android IMEs, timing, user intent or an independent holdout. The
underlying public source is previously disclosed and unproofread. Two focused
runner tests cover selection and rejection of mismatched decisions and failed
Undo. Temporary observations and build files were removed.
