# U8: process death at the start of foreign text

On API 37, the independent Compose editor retained `oldforeign` and its
zero-offset caret after the Rune process was killed. The editor process identity
remained unchanged. Android hid the IME, and clicking the field to reopen it
moved the caret to the end. The test returns it to zero with Rune's editing-panel
Home command before typing. It then verifies `abc the oldforeign` and no
additional editor payload reads during the two typed words. The first attempt
failed at the zero-caret assertion after that click; it is retained as a failed
attempt, not silently counted as a pass.

The final right-context post-kill phase reports `OK (1 test)`, as does a fresh
left-context regression phase. Each preparation phase is intentionally killed
by the host and reports an instrumentation process crash, not JUnit success.
The right-side test proves the editor retained its zero selection through the
kill and the resumed input after an explicit Home action; it does not prove
that reopening the IME leaves selection unchanged. Raw logs are in
`build/review-u8-process-death-right-20261028/`.

The test APK SHA-256 is
`bf011e3da6bb9fb73f8423c078a49cc893ad1e0bb741c895d902bb3879b52032`.
The same APK was then tested on API 26: both right- and left-context post-kill
phases report `OK (1 test)`. The independent editor PID survived each kill.
As in the API 26 left-context receipt, the test explicitly switched to the
sample fallback IME and back to Rune before measuring subsequent payload reads;
this is not evidence of automatic IME window recovery. The zero position was
checked after the rebind, and Home was available if reopening the field moved
the caret. Logs are retained in
`build/review-u8-process-death-right-api26-20261028/`; right and left result
SHA-256 values are `c7de2ae0802f160952c89797353e31785f39e410aaaf404a40d40fc4b268697e`
and `c4ca98c10f21e50ae63eb2579e8a44d23977813be547d0bef5ee601e184ccbcc`.
Fold and manual accessibility remain open. No physical phone or owner data was
used.
