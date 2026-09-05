# Installed-model and composing probes

Source base10e894e. Individual provenance JSON files record installed debug
app/test APK and optional probe source hashes. `results.json` records outcomes
and artifact hashes. The15-test composing run used the original10e894e APKs,
identified separately. All editor fixtures are public synthetic text. Logs keep
only test names, numeric status/metrics and sanitized fixed assertion messages.

The failed extended probe lacked an explicit foreground owner; its UNAVAILABLE
result remains archived without an exact claim about the suspension cause.
The final probe launches a visible Rune settings activity, preserving the
production background/memory/CPU policies. It sends120 requests at500-ms cadence
without retries, then waits50+15 seconds without requests to observe idle unload.
CPU comes from the own-UID model process's `/proc` stat ticks and `_SC_CLK_TCK`;
RSS comes from its status counter. Raw process files, PID/name and input content
are never emitted. These coarse counters exclude editor/client CPU and do not
measure battery energy. The service test has a180-second JUnit deadline; the
host uses a200-second subprocess timeout.

With the reviewed APKs and exact active model already installed, on the
explicitly checked phone (exactly one authorized USB target):

```sh
adb -d shell am instrument -w -r \
  -e class io.github.mesteriis.rune.keyboard.intelligence.inference.RealModelServiceInstrumentedTest \
  -e runeRealService true -e runeRealServiceDuty true \
  io.github.mesteriis.rune.keyboard.test/androidx.test.runner.AndroidJUnitRunner
adb -d shell am instrument -w -r \
  -e class io.github.mesteriis.rune.keyboard.qa.RealModelTypingInstrumentedTest \
  -e runeRealTyping true \
  io.github.mesteriis.rune.keyboard.test/androidx.test.runner.AndroidJUnitRunner
```

Capture only fixed numeric/status records, never unrestricted framework stdout
or screenshots on a personal device. Ordinary CI leaves these flags unset and
skips the optional probes before starting an activity or model. Full scope:
`docs/acceptance/2026-09-05-smart-typing-0.3-fold-qualified.md`.
