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
  grep -Eq 'JNI_OnLoad' <<<"$symbols" || { echo "JNI_OnLoad is missing from $library" >&2; exit 1; }
  if grep -Eq 'Java_|__android_log|curl_|[[:space:]](socket|connect|sendto|recvfrom)(@[^[:space:]]*)?$' <<<"$symbols"; then
    echo "Forbidden JNI/log/network symbol in $library" >&2
    exit 1
  fi
done

if grep -En 'android/log\.h|__android_log|(^|[^[:alnum:]_])(printf|fprintf)[[:space:]]*\(|std::(cout|cerr)' \
  "$repo_root/runtime-llama/src/main/cpp/rune_llama_jni.cpp"; then
  echo "Rune-owned JNI must not log to Android, stdout, or stderr" >&2
  exit 1
fi

apk=${1:-}
if [[ -n "$apk" ]]; then
  [[ -f "$apk" ]] || { echo "APK does not exist: $apk" >&2; exit 1; }
  apk_entries=$(unzip -Z1 "$apk")
  abis=$(sed -n 's#^lib/\([^/]*\)/.*#\1#p' <<<"$apk_entries" | sort -u)
  [[ "$abis" == $'arm64-v8a\nx86_64' ]] || {
    echo "APK ABI set is not exactly arm64-v8a + x86_64:" >&2
    echo "$abis" >&2
    exit 1
  }
  for abi in arm64-v8a x86_64; do
    grep -Fxq "lib/$abi/librune_llama.so" <<<"$apk_entries" || {
      echo "APK is missing librune_llama.so for $abi" >&2
      exit 1
    }
  done
  license_entry=assets/third_party_notices/llama.cpp-LICENSE.txt
  grep -Fxq "$license_entry" <<<"$apk_entries" || {
    echo "APK is missing the llama.cpp license notice" >&2
    exit 1
  }
  cmp -s <(unzip -p "$apk" "$license_entry") \
    "$repo_root/runtime-llama/src/main/cpp/llama.cpp/LICENSE" || {
    echo "Packaged llama.cpp license does not match the pinned submodule" >&2
    exit 1
  }
fi

echo "Native runtime gate passed for arm64-v8a and x86_64."
