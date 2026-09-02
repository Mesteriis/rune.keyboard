package io.github.mesteriis.rune.keyboard.intelligence.ipc;
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoreReplyParcel;
oneway interface IModelScoringCallback {
    void onResult(in ScoreReplyParcel reply);
}
