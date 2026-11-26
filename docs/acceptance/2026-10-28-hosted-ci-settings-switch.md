# Hosted CI: settings driver and accessible switches

Multiple API 26 hosted tests failed because the instrumentation driver could not
find a settings row. Three independent scenarios reproduced the failure on a
local API 26 emulator. The U6 accessibility implementation intentionally hides
the row's text nodes and exposes a native Switch whose content description
contains its title and summary. The driver searched exclusively for TextView
labels, so scrolling could never find those toggle rows. A diagnostic hierarchy
also showed that search navigation can leave the scroll container partway down.

The test driver now recognizes the actual accessible Switch using its
label-delimited description, returns that clickable node, and searches the
scroll container from its beginning for either ordinary titles or switches.
It still interacts with the real settings UI and verifies saved preferences; no
production code or accessibility behavior is changed.

The previously failing key-flick toggle, smart-typing controls and mechanical
punctuation scenarios passed together on disposable ARM64 API 26 and API 37
emulators (3/3 per API). Before-change and after-change instrumentation output
is retained under `build/review-hosted-editor/settings-api26.log`,
`settings-switch-api26.log`, and `settings-switch-api37.log`. The intermediate
attempt to reset scroll position without recognizing Switch nodes still failed
and is retained as `settings-fix-api26.log`. The Android test APK build passed;
its SHA-256 was
`6d8440c5d4e09348ba8d301004a56ce6d467b90ce779fdc6e1fcc7b4f9686`.

These targeted checks do not establish full hosted CI or close the Q7 card.
