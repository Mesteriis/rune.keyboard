#!/system/bin/sh
# Parent executes this after staging only the public fixtures + DEX in this dedicated directory.
set -u
BENCH_ROOT=${1:-/data/local/tmp/rune-lexicon-pr6}
BENCH_PROFILE=${2:-smoke}
BENCH_TAG=${3:-api26-smoke}
BENCH_TIMEOUT=${4:-900}
case "$BENCH_ROOT" in /data/local/tmp/rune-lexicon-pr6) ;; *) echo 'FAIL invalid_root'; exit 2;; esac
case "$BENCH_PROFILE" in smoke|development|cold) ;; *) echo 'FAIL invalid_profile'; exit 2;; esac
case "$BENCH_TAG" in ''|*[!a-zA-Z0-9_-]*) echo 'FAIL invalid_tag'; exit 2;; esac
case "$BENCH_TIMEOUT" in ''|*[!0-9]*) echo 'FAIL invalid_timeout'; exit 2;; esac
if [ "$BENCH_TIMEOUT" -lt 30 ] || [ "$BENCH_TIMEOUT" -gt 1800 ]; then echo 'FAIL invalid_timeout'; exit 2; fi
BENCH_RESULTS="$BENCH_ROOT/results-$BENCH_TAG"
if [ -e "$BENCH_RESULTS" ]; then echo 'FAIL results_already_exist_use_new_tag'; exit 2; fi
mkdir "$BENCH_RESULTS" || exit 2
export CLASSPATH="$BENCH_ROOT/benchmark-dex.jar"
if /system/bin/app_process -Xms32m -Xmx512m /system/bin LexiconVerifyMain "$BENCH_ROOT/fixtures" "$BENCH_ROOT/benchmark-dex.jar" > "$BENCH_RESULTS/verify.tsv" 2> "$BENCH_RESULTS/verify.stderr"; then :; else echo 'FAIL fixture_verification'; exit 2; fi
BENCH_STATUS=0
BENCH_REPEATS=1
if [ "$BENCH_PROFILE" = cold ]; then BENCH_REPEATS=3; BENCH_DATA=development; BENCH_MODE=cold; else BENCH_DATA=$BENCH_PROFILE; BENCH_MODE=full; fi
BENCH_REPEAT=0
while [ "$BENCH_REPEAT" -lt "$BENCH_REPEATS" ]; do
 BENCH_LANGUAGE_INDEX=0
 for BENCH_LANGUAGE in en es ru; do
  BENCH_ROTATION=$(((BENCH_LANGUAGE_INDEX + BENCH_REPEAT) % 3))
  case "$BENCH_ROTATION" in 0) BENCH_ORDER='front trie delete';; 1) BENCH_ORDER='trie delete front';; 2) BENCH_ORDER='delete front trie';; esac
  for BENCH_FORMAT in $BENCH_ORDER; do
   BENCH_FILE="$BENCH_RESULTS/$BENCH_LANGUAGE.$BENCH_FORMAT.$BENCH_DATA.$BENCH_MODE.$BENCH_REPEAT"
   if /system/bin/app_process -Xms32m -Xmx512m /system/bin LexiconAndroidMain "$BENCH_ROOT/fixtures" "$BENCH_LANGUAGE" "$BENCH_FORMAT" "$BENCH_DATA" "$BENCH_MODE" "$BENCH_TIMEOUT" > "$BENCH_FILE.tsv" 2> "$BENCH_FILE.stderr"; then
    echo "PROCESS $BENCH_LANGUAGE $BENCH_FORMAT $BENCH_MODE $BENCH_REPEAT PASS"
   else
    BENCH_CODE=$?;BENCH_STATUS=1
    echo "PROCESS $BENCH_LANGUAGE $BENCH_FORMAT $BENCH_MODE $BENCH_REPEAT FAIL $BENCH_CODE"
   fi
  done
  BENCH_LANGUAGE_INDEX=$((BENCH_LANGUAGE_INDEX + 1))
 done
 BENCH_REPEAT=$((BENCH_REPEAT + 1))
done
exit "$BENCH_STATUS"
