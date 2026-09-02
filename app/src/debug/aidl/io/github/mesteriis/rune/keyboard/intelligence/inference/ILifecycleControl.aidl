package io.github.mesteriis.rune.keyboard.intelligence.inference;
import io.github.mesteriis.rune.keyboard.intelligence.inference.ILifecycleSnapshot;

/** Debug-only, same UID, fixed scalar commands and numeric snapshots. */
oneway interface ILifecycleControl {
    void command(int operation, ILifecycleSnapshot callback);
}
