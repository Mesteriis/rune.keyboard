#!/system/bin/sh
set -u
EXACT_ROOT=/data/local/tmp/rune-lexicon-exact-pr6
EXACT_BASE=/data/local/tmp/rune-lexicon-pr6/fixtures
EXACT_TAG=${1:-api26-exact}
EXACT_TIMEOUT=${2:-90}
case "$EXACT_TAG" in ''|*[!a-zA-Z0-9_-]*) echo 'FAIL invalid_tag'; exit 2;; esac
case "$EXACT_TIMEOUT" in ''|*[!0-9]*) echo 'FAIL invalid_timeout'; exit 2;; esac
if [ "$EXACT_TIMEOUT" -lt 30 ] || [ "$EXACT_TIMEOUT" -gt 600 ]; then echo 'FAIL invalid_timeout'; exit 2; fi
EXACT_RESULTS="$EXACT_ROOT/results-$EXACT_TAG"
if [ -e "$EXACT_RESULTS" ]; then echo 'FAIL results_exist'; exit 2; fi
mkdir "$EXACT_RESULTS" || exit 2
export CLASSPATH="$EXACT_ROOT/benchmark-dex.jar"
if /system/bin/app_process -Xms32m -Xmx512m /system/bin ExactVerifyMain "$EXACT_BASE" "$EXACT_ROOT/fixtures" "$EXACT_ROOT/benchmark-dex.jar" > "$EXACT_RESULTS/verify.tsv" 2>/dev/null; then :; else echo 'FAIL preflight'; exit 2; fi
EXACT_STATUS=0
for EXACT_LANG in en es ru; do
 case "$EXACT_LANG" in en) EXACT_ORDER='front trie delete';; es) EXACT_ORDER='trie delete front';; ru) EXACT_ORDER='delete front trie';; esac
 for EXACT_FORMAT in $EXACT_ORDER; do
  if /system/bin/app_process -Xms32m -Xmx512m /system/bin ExactAndroidMain "$EXACT_BASE" "$EXACT_ROOT/fixtures" "$EXACT_LANG" "$EXACT_FORMAT" "$EXACT_TIMEOUT" > "$EXACT_RESULTS/$EXACT_LANG.$EXACT_FORMAT.tsv" 2>/dev/null; then
   echo "PROCESS $EXACT_LANG $EXACT_FORMAT PASS"
  else
   EXACT_STATUS=1;echo "PROCESS $EXACT_LANG $EXACT_FORMAT FAIL"
  fi
 done
done
exit "$EXACT_STATUS"
