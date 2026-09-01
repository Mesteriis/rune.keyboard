#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "usage: $0 SOURCE_DIRECTORY OUTPUT_DIRECTORY" >&2
  exit 64
fi

readonly SOURCE_DIR=$(cd "$1" && pwd -P)
readonly OUTPUT_DIR=$2
readonly RECIPE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
readonly IMAGE=rune-text-builder:0.1
readonly ASSET=rune-text-v1-0.1.0-q4_k_m.gguf

mkdir -p "$OUTPUT_DIR/run-1" "$OUTPUT_DIR/run-2"
docker build --pull=false --tag "$IMAGE" "$RECIPE_DIR"

for run in run-1 run-2; do
  docker run --rm --network=default \
    --mount "type=bind,src=$SOURCE_DIR,dst=/source,readonly" \
    --mount "type=bind,src=$RECIPE_DIR,dst=/recipe,readonly" \
    --mount "type=bind,src=$(cd "$OUTPUT_DIR/$run" && pwd -P),dst=/output" \
    "$IMAGE"
done

first=$(awk '{print $1}' "$OUTPUT_DIR/run-1/$ASSET.sha256")
second=$(awk '{print $1}' "$OUTPUT_DIR/run-2/$ASSET.sha256")
test "$first" = "$second"
cmp "$OUTPUT_DIR/run-1/$ASSET" "$OUTPUT_DIR/run-2/$ASSET"
printf 'reproducible_sha256=%s\n' "$first"
