package io.github.mesteriis.rune.keyboard.intelligence.inference;

oneway interface ILifecycleSnapshot {
    void onSnapshot(int processId, int uid, int starts, long previousId, long lastId,
        int active, int peakActive, int cancels, int cancelledCompletions,
        int completions, int unloads, int unloadedCompletions, int orderViolations, int timeouts);
}
