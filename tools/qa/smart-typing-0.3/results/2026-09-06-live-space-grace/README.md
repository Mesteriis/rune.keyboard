# Actual late correction within the unchanged 250 ms Space grace

Basebf7ede8 plus the enclosed two-file test delta. The exact public `a helllo` request is held in the existing remote fake engine. Space is injected through the actual resident key; a real editor text-change event must prove `a helllo ` before the numeric result is released. The controller must certify current Space composition/caret ownership. Both release and the timestamp recorded after the actual coordinator callback must be within [0,250) ms of the production coordinator's real spaceStartedAt; no clock, deadline, scheduler, model policy or InputConnection result is substituted.

Final04 passes on API26 (12.340s) and API37 (11.561s). It requires exact late correction `a hello `, including finish+1, compose+1, region+2, commit+1 and all other command deltas zero. Actual Backspace restores `a helllo` as composition with region+1, compose+1 and selected Original. Payload-read counters remain zero. The execution durations above describe the whole test, not typing latency; the callback assertion only proves it fell within the production grace for these executions.

API26 observer compatibility: its text-change event contains the exact public text but source resource ID is null. Before the gesture, the test independently traverses the bounded current accessibility tree and captures the window/class of the unique focused QA EditText, proving that window has exactly one editable field. Events must match window, class, package, exact before/after text, and source ID when present. The mandatory live controller acknowledgement and selection/composition ownership checks remain in place. Accessibility metadata is a test observer; no product editor read was added.

Preserved development evidence:

- build01: test compilation rejected access to a private driver helper; replaced with the existing public UiDevice lookup.
- run01: API37 passed; API26 timed out because the strict event source-ID predicate rejected its null-ID event.
- run02 diagnostic: API26 records exact text-change payload and null source-ID, with exact public editor text.
- run03: API37 passed; API26 checked the reply queue immediately after remote engine completion and found no callback yet. Engine completion precedes asynchronous Binder delivery. Final code awaits actual callback arrival separately while still requiring its recorded timestamp to be under250ms; the product deadline remains unchanged.

All prior failures, source/APK identities and patches remain archived. This is ordinary-CI fake-numeric-engine evidence through real editor and service Binder. It does not qualify real-model availability, physical latency, next-text invalidation, or overall release completion. The user removed the phone; remaining physical checks are separately blocked on device availability.
