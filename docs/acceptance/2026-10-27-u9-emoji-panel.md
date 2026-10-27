# U9 — native emoji panel and isolated insertion (partial)

Symbols and Symbols Alt now expose Emoji in allowed editors. Letters retain their
existing default bottom row; the optional letters-row setting is still pending.
The reducer refuses entry in sensitive, raw-key, number, phone and date/time
editors. Symbols add a 0.9-unit entry, reducing Space from 5.65 to 4.75 while the
row remains ten units. The native panel uses three row heights for categories and
GridView, plus a fourth for ABC/Delete/Space/Enter. Candidate-strip visibility
retains the existing typing policy, so the four-row check excludes that strip.

GridView/BaseAdapter recycles TextViews with localized CLDR names. A horizontal
native strip selects categories; Paint.hasGlyph is checked lazily and cached for
visited entries. Catalog loading happens on first panel creation/opening, without
network work. These structural properties do not prove the opening/startup budget.
Recents are view-local RAM only, at most 32 unique sequences, added only after an
accepted commit. Incognito hides recents and never adds to them. No persisted
recents option was added. Skin-tone selection remains a separate stage.

Insertion uses CommitText, finishes owned composing without correction or word
learning, and clears ranking/revision context. A native regression exposed a
missing boundary proof: after that clear, the next `teh` had a candidate but Space
kept it literal. The final controller records only the numeric caret after the
accepted palette delimiter. Direct ABC return preserves this proof; external
cursor changes, invalidation, session end and deletion outside owned context
revoke it. Unknown external-word fencing remains in force. No synthetic whitespace
or earlier text is inserted into model context. The preview now uses the same
grapheme-boundary helper for its local Backspace.

Final validation:

- 1,246 JVM tests, zero failures/errors/skips, including policy/weights, exact
  commit, isolated context, finish refusal, external fencing, next-word correction
  and revocation of the numeric boundary proof.
- Fifteen source/generator tests, imeIntelligenceBoundary, privacyGateRelease,
  lintDebug, assembleDebug and assembleDebugAndroidTest pass; combined exit zero.
- Twenty-three native scenarios pass on one isolated API 36 arm64 emulator:
  three emoji cases, eight public editing cases and twelve existing
  WebView/Compose/preview/editor-boundary cases. Compose uses the separately
  source-bound fixture, with runeComposeQa=true and no skips. The installed Rune
  APK SHA matches the final local debug APK.
- Emoji cases prove literal `teh😀`, subsequent `teh → the` at Space, accepted
  recents with a localized name, native named/selected category actions, named
  TextView cell click actions, unchanged four-row content height, ZWJ `👩‍💻` and
  flag `🇪🇸` insertion and one-Backspace deletion, and hidden incognito recents.
  All six payload-read counters stay zero before deletion; ordinary grapheme
  deletion may use the existing bounded non-sensitive editor read.
- Fresh ordinary replay: all 12,000 rows exactly match the previous projection
  after excluding only hostStageNanos and fullTokenGenerationNanos. All 88 source,
  18 scoring-asset and driver bindings are checked. EN calibration volume and EN
  holdout precision/volume gates remain failed; ES holdout retains one aggregate
  false change/1,000 controls. No renewed full quality qualification is claimed.

Development failures are retained separately, not counted as passes: the first
native run had two failures (missing next-word correction and empty-field hint
comparison); waiting for a candidate did not repair the real correction failure.
The second native run still failed that correction case. A sentinel prefix fixed
the empty-field assertion, and numeric delimiter ownership fixed the product bug.
Two early revocation-unit runs omitted actual ordered editor acknowledgements;
the corrected fixture acknowledges them and verifies fresh candidate ownership
before asserting refusal. The final native/JVM results above follow those changes.

U9 remains open: optional letters-row key/settings, opening/cold-start/PSS budgets,
old API 26 font and glyph cases, modifier insertion coverage, physical Fold on
both displays and manual TalkBack traversal. Named native actions alone do not
prove a complete TalkBack review. The task-owned emulator was stopped/deleted;
there was no phone action or update. The full owner review remains open.
