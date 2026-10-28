# Q3 — resource-refusal follow-up installed on Fold

The locally verified Q3 fix at `ff40adf` is now installed on the owner's Samsung
SM-F966B (API 37) through explicit-transport ADB. AURA and Android MCP confirmed
an exclusive slot and received release messages after collection. No Android MCP
phone commands were used; Rune has no pending phone commands.

The installed main/test APK pair is byte-identical to the pair that passed six
current API 26 diagnostics UI scenarios and four personal-admission methods.
Installation preserves the signing certificate and all 69 assets/four native
libraries, backs up owner state privately, uses install -r without data clear or
uninstall, and verifies the installed main APK's complete bytes afterward.
Version remains 0.4.2/code 8.

Four actual physical Fold methods pass, with 15 exact scripted public cases and
no failures or skips: fresh reviewed phrases at two paces, excess empty-field
Backspace, preview/Undo with the following word, and rapid short words at three
paces. These are regression cases, not a natural-use accuracy estimate.

All four journal snapshots were retrieved privately and accepted by the current
analyzer; new schema 9 text/metadata has bounded numeric editor types. Historical
rows remain supported and snapshots overlap. No captured owner text, secure IME
settings, device serial, private store contents or model files are committed.
Keyboard preferences and the three inspected secure IME settings are restored;
inspected personal/control/learning state (one file present) and optional model
files retain their exact contents/hashes.

A clean checkout of committed `ff40adf` passes privacyGateRelease and apkFootprint
(exit 0); its unsigned release APK is 180,096,157 bytes. This is local release
validation, not independent F-Droid build-server or distribution acceptance.
The verified task-owned API 26 emulator has been stopped and its AVD deleted.
All 13 original owner dirty files and 98 original untracked paths are preserved.

The adjacent evidence binds APKs and real outputs. Q3's local acceptance remains
verified by the resource-refusals audit; the full review and remaining cards stay
open. No push, public release, new model or admission threshold change occurred.
