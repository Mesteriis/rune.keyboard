#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
ndk_root=${ANDROID_NDK_HOME:-${ANDROID_HOME:?ANDROID_HOME is required}/ndk/29.0.14206865}
readelf_bin="$ndk_root/toolchains/llvm/prebuilt/darwin-x86_64/bin/llvm-readelf"
if [[ ! -x "$readelf_bin" ]]; then
  readelf_bin="$ndk_root/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf"
fi
[[ -x "$readelf_bin" ]] || { echo "Pinned NDK llvm-readelf is unavailable" >&2; exit 1; }

native_libraries=()
while IFS= read -r line; do native_libraries+=("$line"); done < <(
  find "$repo_root/runtime-llama/build/intermediates/stripped_native_libs/release" \
    -type f -name 'librune_llama.so' -print | sort -u
)
[[ ${#native_libraries[@]} -eq 2 ]] || {
  echo "Expected exactly two release librune_llama.so outputs, found ${#native_libraries[@]}" >&2
  exit 1
}

for library in "${native_libraries[@]}"; do
  needed=$($readelf_bin -d "$library" | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p' | LC_ALL=C sort)
  expected=$(printf '%s\n' libc.so libc++_shared.so libdl.so libm.so | LC_ALL=C sort)
  [[ "$needed" == "$expected" ]] || {
    echo "Unexpected DT_NEEDED for $library:" >&2
    echo "$needed" >&2
    exit 1
  }
  symbols=$($readelf_bin -Ws "$library")
  rg -q 'JNI_OnLoad' <<<"$symbols" || { echo "JNI_OnLoad is missing from $library" >&2; exit 1; }
  if rg -q 'Java_|__android_log|curl_|\b(socket|connect|sendto|recvfrom)@' <<<"$symbols"; then
    echo "Forbidden JNI/log/network symbol in $library" >&2
    exit 1
  fi
done

if rg -n 'android/log\.h|__android_log|\b(printf|fprintf)\s*\(|std::(cout|cerr)' \
  "$repo_root/runtime-llama/src/main/cpp/rune_llama_jni.cpp"; then
  echo "Rune-owned JNI must not log to Android, stdout, or stderr" >&2
  exit 1
fi

apk=${1:-}
if [[ -n "$apk" ]]; then
  [[ -f "$apk" ]] || { echo "APK does not exist: $apk" >&2; exit 1; }
  abis=$(unzip -Z1 "$apk" | sed -n 's#^lib/\([^/]*\)/librune_llama.so$#\1#p' | sort -u)
  [[ "$abis" == $'arm64-v8a\nx86_64' ]] || {
    echo "APK ABI set is not exactly arm64-v8a + x86_64:" >&2
    echo "$abis" >&2
    exit 1
  }
fi

echo "Native runtime gate passed for arm64-v8a and x86_64."
