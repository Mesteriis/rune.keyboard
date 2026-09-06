package io.github.mesteriis.rune.keyboard.intelligence.ipc;
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoreRequestParcel;
import io.github.mesteriis.rune.keyboard.intelligence.ipc.IModelScoringCallback;
oneway interface IModelScoringService {
    void score(in ScoreRequestParcel request, IModelScoringCallback callback);
    void cancel(long sessionId, long requestId);
}
