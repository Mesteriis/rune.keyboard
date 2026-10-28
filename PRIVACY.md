# Privacy

Rune Keyboard processes typing locally on your Android device.

## Network access

The app declares `android.permission.INTERNET` for a model download that you explicitly start in settings. The download provider receives ordinary connection metadata such as your IP address. Rune does not send typed text with the request. There are no analytics or advertising SDKs.

The optional Rune Text package is downloaded from an immutable Hugging Face URL and checked against its expected size and SHA-256. Importing an existing model file is also supported. Local dictionaries and ordinary keyboard input work without a model download.

## Local data

Settings, user-added words, abbreviations, protected words and data from enabled learning/personalization features can be stored in app-private storage. The home screen's sample text is temporary and does not enter learning.

Enabled learning features store word and phrase fragments, including readable words, in two separate app-private files outside Android backups:

- `no_backup/personal-typing/profile.bin`: confirmed words with language; original/replacement pairs, accepted counts and rejection flags; short phrase prefixes/continuations, language and support counts. Personal learning records phrases on committed words, not only after an explicit correction. Limits are 512 confirmed words, 512 feedback pairs, 1,024 phrases and 1 MiB. Words are normalized letters, up to 48 characters; each phrase prefix/continuation has one or two words, and counts saturate at 255.
- `no_backup/learning-lab/learning.bin`: up to 512 distinct evidence records / 512 KiB. Each record contains language, original/expected SHA-256 hashes, feedback source, edit type, holdout/training/conflict flags and, when example collection was enabled for that record, original/expected words. The file also stores active and rollback pattern counts by language/edit type. Hashes are deterministic deduplication keys, not encryption or anonymization; dictionary guesses can identify hashed words.

Turning off personal learning stops new personal-profile learning and keeps existing entries. Turning off example collection stops retaining new raw example words; typo-pattern learning can still record hashes and flags. Turn off both learning-lab switches to stop all new evidence. Existing raw examples are retained until reset. Password (`SENSITIVE`) and no-personalized-learning (`INCOGNITO`) fields do not contribute to either store. These exclusions also apply to personal suggestions and typing diagnostics; ordinary owned-text correction may still work in incognito.

Model scoring uses bounded input context in memory and a separate private process. It does not create a chat history. Protected fields and unsupported editor contexts have stricter restrictions; the key popup is suppressed in password fields.

Android application backup and cleartext traffic are disabled in the manifest. The keyboard does not read clipboard contents or maintain a clipboard history. Copy, Cut and Paste controls delegate Android context-menu commands to the focused editor through InputConnection.performContextMenuAction. The editor performs the operation; a dispatch acknowledgement does not prove that it completed. Rune does not fetch editor text to implement these commands.

The emoji panel uses packaged Unicode/CLDR data and the device font, without a
network request. Up to 32 recent accepted emoji insertions are kept only in the
keyboard view's memory, with no disk persistence. Incognito hides recents and
does not add to them; sensitive, raw-key and numeric fields have no emoji panel.
Emoji insertion finishes composing literally and clears ranking/revision context.

New input sessions do not adopt unknown preceding editor text. When the numeric selection starts after the beginning of the field, Rune commits the adjacent suffix literally until new Rune whitespace establishes a word boundary. This decision uses cursor offsets, not editor-text reads or retained text from another session.

## Diagnostics and exports

Release builds exclude the debug typing recorder and its settings UI. Debug builds offer optional technical diagnostics and a separate text recorder; text recording requires two explicit confirmations. Both are off by default. Debug exports and explicit model/data exports are user-initiated. Review a file before sharing it.

## Delete data

The two learning stores have separate reset controls: Delete personal typing data clears the personal profile and tap calibration; Learning lab → Reset examples and patterns clears the evidence ledger and its active/rollback policies. Neither switch automatically deletes previously saved data. Use the relevant dictionary/learning controls to remove data from those features. In Dictionary and learning → Personalization → Confirmed words, you can filter the local confirmation list and remove one word for one language. This removes only that confirmation: correction-pair rejections, phrase evidence and the separate protected-word list are retained. Removing a non-dictionary confirmation can stop it from validating personal phrase suggestions. Use Reset personal data to clear the rest of that personal profile. If saving a removal fails, the screen reports the failure and offers a retry; an unsaved removal may return after restarting. The model settings screen can remove an installed model. Clearing Rune's Android app storage or uninstalling the app removes its private local data; exported files remain wherever you saved them.

For bugs, use [GitHub Issues](https://github.com/Mesteriis/rune.keyboard/issues) with synthetic text and redacted screenshots. Do not post sensitive typing data.
