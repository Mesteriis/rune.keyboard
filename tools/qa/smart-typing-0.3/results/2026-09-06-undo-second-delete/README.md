# Second Backspace after automatic Undo — 2026-09-06

Coverage addition on base1a5826e; no production changes. Both existing end-to-end test sequences now continue after the first Backspace restored Original.

- Public numeric-fake spelling over resident IME, real scoring-service Binder and real editor Binder: `a helllo` → Space → `a hello ` → Undo → `a helllo` → next Backspace → `a helll`. Caret/span and command deltas prove exactly one composing edit, no extra commit/region/finish/key events or editor payload reads.
- Packaged Russian canonical case: `я москва` → Space → `я Москва ` → Undo → `я москва` → next Backspace → `я москв`. The owned start remains unchanged; end/caret become7; exactly one composing edit and no extra commit/region/finish or payload reads.

API26 affected scope2/2 PASS (38.054s); API37 affected scope2/2 PASS (33.279s). Full prescribed local lint/build/privacy/dependency/native-symbol gates PASS (240tasks). Test/source and unchanged app hashes are in inputs.json. These are the two changed cases, not a claim that a new complete152 suite or a physical-phone run occurred. They verify these one-letter graphemes; broader Unicode/grapheme unit coverage remains separate. Mandatory postcommit JVM evidence will be recorded after commit.
