package io.github.mesteriis.rune.keyboard.intelligence.inference;

/** Debug public-fixture observation only: opaque tokens, fixed modes and numeric counts. */
oneway interface ILifecyclePublicSnapshot {
    void onSnapshot(int mode, int armed, int starts, int completions, int active,
        long sessionId, long revision, long requestId, int admittedMode,
        long completedSessionId, long completedRevision, long completedRequestId,
        int completedMode, int invalidRequests);
}
