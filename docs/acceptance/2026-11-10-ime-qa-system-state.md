# QA IME system-state restoration

The earlier physical Undo run reported that at least one of four system IME
settings differed after teardown, but its host wrapper retained only an aggregate
comparison; the original values cannot be reconstructed from that receipt.
Separate repetitions of the canonical and ready-model methods each passed with
all four settings equal. A later independent late-model attempt failed before
typing because Rune was not selected successfully; its before/after settings
also matched. Those observations do not identify the earlier mismatch.

`ImeTestDriver` now snapshots the selected subtype as well as the selected IME,
enabled IME list and hardware-keyboard flag. It validates captured values before
changing state, detects Rune as an exact component, avoids an unnecessary IME
restart when the original is already selected, and checks restoration by field.
It restores an originally absent setting by deletion rather than writing `0`.
The teardown attempts the remaining restorations even after an earlier failure.
Values unsafe for the command interface are refused before use. For an enabled
IME list containing semicolons, it first verifies that the device command
interface treats the separator as a literal argument; otherwise it refuses the
write. It checks all four values again after restoration.

One intermediate Fold run failed during subtype restoration and then refused a
malformed subtype on the next setup. The host wrapper had retained the exact
pre-run values and restored all four; diagnostic files displaced by rotation
were retained in a private, ignored recovery directory. The intermediate code
wrapped shell values in quotes, which the device command interface can pass as
literal characters. The revised code passes validated values without quotes and
uses a separate fail-closed semicolon check. The original aggregate mismatch is
still not attributed to that intermediate error.

With the revised test APK, eight instrumented fake-setting and command-interface
tests passed on Fold without changing the four system settings. A subsequent
physical three-case run was interrupted; its final host output and pre-run
snapshot are unavailable. Android's test log records two finished cases and a
failure in the third when its QA editor became unavailable, followed by failure
to switch the IME during cleanup. This is a failed run, not evidence that the
original four settings or displaced diagnostics survived it. The current
selected keyboard was observed as Rune after the interruption; the lost
pre-run values were not guessed or overwritten.

The exact installed app and revised test APK were then copied into a temporary,
read-only Android API 37 emulator on an isolated ADB server. Three existing
canonical and synthetic-model Undo tests passed with zero skips; all four
system IME settings matched before and after. The emulator, ADB server and
copied APKs were removed. The CI Android-boundary parser's 23 host tests passed.
The revised test APK built successfully in a temporary pinned-submodule clone,
which was also removed. This does not establish the cause of the interrupted
physical failure, physical release acceptance, API 26 behavior or hosted CI.
