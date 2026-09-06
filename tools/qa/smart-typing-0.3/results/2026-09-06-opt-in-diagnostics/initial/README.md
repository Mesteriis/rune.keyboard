# Initial diagnostics integration — 2026-09-06

API37: six cases PASS, 243.57s. API26: five PASS and one test synchronization failure after SettingsActivity.recreate; it queried settings_scroll before the replacement activity was ready. These initial assertions still lack the subsequently requested metadata-value and real text-only positive checks, so this is not final diagnostic acceptance.

The corrected MechanicalProtectedForms case passes on both APIs using real in-process popup geometry followed by actual MOVE/UP. The remaining five scenarios exercise actual debug settings, consent cancellation, fresh input, fake-model/editor Binder correction and Undo, excluded canaries and managed deletion. Task1 code review separately found pending consent/outcome provenance issues; those are not erased by these passing smoke cases. Exact pre-fix sources and APK input receipt are retained.
