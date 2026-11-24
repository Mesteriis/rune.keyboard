# A4: colon on the symbols layer is not a passing correction

On an API 26 arm64 emulator with debug APK SHA-256
`306e75b46df3a563a6506c53cad847b5d1194c66ee81d23d1a60befce10869c1`, two
native tests typed Russian using Rune, selected `?123`, then typed `:`. The
abbreviation test passed: `инн:` remained unchanged and Backspace restored
`инн`. The useful-correction test **failed**: after the `смотреть` suggestion
appeared, `смотруть:` remained literal instead of becoming `смотреть:`.
Instrumentation reported two tests, one failure. Raw log:
`build/review-a4-colon-api26-20261028/colon.log`, SHA-256
`32dbf401d5a05b69ea1ca1a114759dd6ba27f69ee736e941f9b7b99db09388cc`.
The task-owned emulator was stopped and deleted.

Source inspection explains why the host replay was insufficient: it sends `:`
while the keyboard is on the letters layer, whereas selecting `?123` causes
`RuneInputMethodService` to invalidate the candidate and finish owned
composition; boundary replacement also requires the letters layer. The native
failure is consistent with both restrictions, although this run does not isolate
their individual effects. Changing either requires maintaining editor ownership,
protected token and other symbol-layer behaviors. The failing instrumentation
test is retained with an explicit `@Ignore` until a verified fix removes it; it
must not count as a pass. A4's useful colon path and physical Fold acceptance
remain open.
