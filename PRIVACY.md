# Privacy

Rune Keyboard processes typing locally on your Android device.

## Network access

The app declares `android.permission.INTERNET` for a model download that you explicitly start in settings. The download provider receives ordinary connection metadata such as your IP address. Rune does not send typed text with the request. There are no analytics or advertising SDKs.

The optional Rune Text package is downloaded from an immutable Hugging Face URL and checked against its expected size and SHA-256. Importing an existing model file is also supported. Local dictionaries and ordinary keyboard input work without a model download.

## Local data

Settings, user-added words, abbreviations, protected words and data from enabled learning/personalization features can be stored in app-private storage. The home screen's sample text is temporary and does not enter learning.

Model scoring uses bounded input context in memory and a separate private process. It does not create a chat history. Protected fields and unsupported editor contexts have stricter restrictions; the key popup is suppressed in password fields.

Android application backup and cleartext traffic are disabled in the manifest. Rune does not provide clipboard reading or a clipboard history.

## Diagnostics and exports

Release builds exclude the debug typing recorder and its settings UI. Debug builds offer optional technical diagnostics and a separate text recorder; text recording requires two explicit confirmations. Both are off by default. Debug exports and explicit model/data exports are user-initiated. Review a file before sharing it.

## Delete data

Use the relevant dictionary/learning controls to remove data from those features. The model settings screen can remove an installed model. Clearing Rune's Android app storage or uninstalling the app removes its private local data; exported files remain wherever you saved them.

For bugs, use [GitHub Issues](https://github.com/Mesteriis/rune.keyboard/issues) with synthetic text and redacted screenshots. Do not post sensitive typing data.
