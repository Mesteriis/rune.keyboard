# U14: expanded candidate selection core

The controller can prepare a snapshot of the current hidden correction items
for an explicit expanded view. A selection requires the same single-use snapshot,
current session, revision and candidate epoch, an ID in that snapshot, and an
unchanged validated hidden order. Ordinary `selectCandidate` still rejects
hidden IDs. The snapshot is cleared on close, text input, ordinary selection,
candidate invalidation, new candidate replies and successful reranking.
Selection uses the existing guarded editor transaction and manual feedback;
the automatic Space path does not consume a hidden candidate.

Regression coverage exercises visible/hidden isolation, explicit selection,
replay of a consumed snapshot, a replaced or closed snapshot, foreign IDs,
input and candidate invalidation, and Space after explicit selection. All 1,357
JVM tests passed without skips. The scoring-boundary verifier passed. Two fresh
12,000-row current-product replays matched each other and the prior default-on
projection `fab02fa792f3a8ebc0721dff33e30f05d14cc30615b85e89963e7a13d6b4c1ec`;
no native model calls were made. The adjacent evidence binds the changed sources
and local replay receipt. Raw replay files stay in ignored build output.

This is an internal core step, not a user-facing expanded strip. Before wiring
it, the coordinator must enforce its editor/privacy/settings visibility policy,
and the view must close or invalidate an in-flight touch on changed candidates.
Expanded UI, accessibility, Fold layout and the full U14 acceptance remain open.
