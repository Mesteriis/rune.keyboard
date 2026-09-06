# Late reply across two real editors

Base634cd1e plus the enclosed two-file Android-test delta. A successful normal model correction is positively established first. The fixture then holds another exact public request for `a helllo`, launches a separate real QA editor using NEW_TASK|MULTIPLE_TASK, explicitly focuses it, verifies a newer typing session and types the known public word `a`. Releasing the old remote request must preserve the new editor's exact text, composing span/caret and command counters, preserve candidate contents/IDs/selection, and never deliver the old token to the accepted coordinator listener. Returning through Android Back to the retained original editor must reveal unchanged `a helllo` with no compose/region/commit/raw-key writes since the switch. Connection and finish lifecycle calls are allowed; payload reads remain zero.

Final04: API26 PASS in23.663s; API37 PASS in22.304s. Exact source/APK hashes and complete patches/logs are retained. The same helper's expired-Space and language cases are separately rerun against04 because its comparison changed.

Preserved development failures:

- 01: plain Activity launch did not establish the required new typing session on either API. The test failed before it could evaluate a stale response. Final launch explicitly creates a new task and retains the original.
- 02: API26 lacked the observed editor node at snapshot time; API37's `z` triggered additional candidate work because the fixed public lexicon contains `a` at edit distance1. Final test explicitly focuses the new editor and uses known `a`, isolating release of the old request without unrelated inference.
- 03: both APIs reached the candidate comparison but compared SmartTypingViewState object identity. That class has no structural equals and its nonempty view is rebuilt by the getter. The helper now compares all meaningful state: enabled, selected ID and the complete structural candidate list (kind, opaque ID and text). This preserves the stale-candidate assertion while allowing equivalent snapshots to be separate objects.

No production, deadline, model, qualification or test timeout change. These are real editor/service Binder tests with a fixed fake numeric engine. They cover a different editor/task/session and eventual suppression; not already-dispatched stale callbacks, same-Activity field switching, arbitrary editors, physical performance or exact-GGUF quality. Failed variants are evidence of fixture setup/assertion problems, not demonstrated product defects.

Helper regression: both existing cases PASS on API26 (41.472s) and API37 (39.173s). Full prescribed gates PASS,240tasks in7s.
