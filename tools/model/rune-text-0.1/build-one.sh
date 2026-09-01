#!/bin/sh
set -eu

readonly LLAMA_COMMIT=36b10154383b60eb15baac2c7a40d2a5f784faa7
readonly SOURCE_COMMIT=da87bfb608c14b7cf20ba1ce41287e8de496c0cd
readonly ASSET_NAME=rune-text-v1-0.1.0-q4_k_m.gguf

test -f /source/model.safetensors
test -f /recipe/source.sha256
(
  cd /source
  sha256sum --check /recipe/source.sha256
)

git clone --quiet --filter=blob:none --no-checkout https://github.com/ggml-org/llama.cpp /work/llama.cpp
git -C /work/llama.cpp fetch --quiet --depth 1 origin "$LLAMA_COMMIT"
git -C /work/llama.cpp checkout --quiet --detach "$LLAMA_COMMIT"
test "$(git -C /work/llama.cpp rev-parse HEAD)" = "$LLAMA_COMMIT"

cmake -S /work/llama.cpp -B /work/llama.cpp/build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DGGML_NATIVE=OFF \
  -DGGML_OPENMP=OFF \
  -DGGML_BACKEND_DL=OFF \
  -DGGML_CPU_ALL_VARIANTS=OFF \
  -DGGML_CPU_KLEIDIAI=OFF \
  -DGGML_LLAMAFILE=OFF \
  -DLLAMA_BUILD_COMMON=ON \
  -DLLAMA_BUILD_TOOLS=ON \
  -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_EXAMPLES=OFF \
  -DLLAMA_BUILD_SERVER=ON
cmake --build /work/llama.cpp/build --target llama-quantize llama-cli --parallel 2

python /work/llama.cpp/convert_hf_to_gguf.py \
  /source \
  --outfile /work/rune-text-v1-0.1.0-f16.gguf \
  --outtype f16
/work/llama.cpp/build/bin/llama-quantize \
  /work/rune-text-v1-0.1.0-f16.gguf \
  "/output/$ASSET_NAME" \
  Q4_K_M

sha256sum "/output/$ASSET_NAME" > "/output/$ASSET_NAME.sha256"
stat --printf='%s\n' "/output/$ASSET_NAME" > "/output/$ASSET_NAME.size"
/work/llama.cpp/build/bin/llama-cli --version > /output/llama-cli-version.txt
python /recipe/read_gguf_metadata.py "/output/$ASSET_NAME" > /output/gguf-metadata.json

cat > /output/build-provenance.txt <<EOF
source=Qwen/Qwen3-0.6B-Base
source_revision=$SOURCE_COMMIT
converter=ggml-org/llama.cpp/convert_hf_to_gguf.py
converter_revision=$LLAMA_COMMIT
quantizer=ggml-org/llama.cpp/llama-quantize
quantizer_revision=$LLAMA_COMMIT
quantization=Q4_K_M
container_image=python@sha256:09f7da3bc104798d0afb40bc08d23ab2da20a76130cec1f2ef170848f5d85217
EOF

python -m pip freeze --all > /output/python-sbom.txt
dpkg-query -W -f='${Package}\t${Version}\n' | sort > /output/debian-sbom.txt
cp /source/LICENSE /output/QWEN3-BASE-APACHE-2.0.txt
cp /work/llama.cpp/LICENSE /output/LLAMA-CPP-MIT.txt
cp /recipe/THIRD_PARTY_NOTICES.md /output/THIRD_PARTY_NOTICES.md
