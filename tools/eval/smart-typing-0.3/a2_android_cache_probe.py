#!/usr/bin/env python3
"""Build an isolated Android scorer copy with the existing A2 cache counter.

This does not change the app or run adb. Supply the arm64 Android CMake build
created by the runtime Gradle task. The resulting executable is diagnostic,
not the production JNI library and not a release or quality qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import struct

import a2_cache_probe as host

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
UPSTREAM='36b10154383b60eb15baac2c7a40d2a5f784faa7'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_executable(data):
    if (len(data)<20 or data[:6]!=b'\x7fELF\x02\x01' or
            struct.unpack_from('<H',data,16)[0] not in (2,3) or struct.unpack_from('<H',data,18)[0]!=183):
        raise ValueError('A2_ANDROID_ELF_IDENTITY')


def build(native,compiler,output):
    native=native.resolve(strict=True);compiler=compiler.absolute();output=output.resolve()
    variants = {'Debug': 'Debug', 'RelWithDebInfo': 'RelWithDebInfo'}
    variants_root = ROOT / 'runtime-llama/.cxx'
    relative = native.relative_to(variants_root) if native.is_relative_to(variants_root) else None
    if relative is None or len(relative.parts) != 3 or relative.parts[0] not in variants or relative.parts[2] != 'arm64-v8a':
        raise ValueError('A2_ANDROID_NATIVE_SCOPE')
    build_type = variants[relative.parts[0]]
    if output.exists() or not output.is_relative_to(ROOT/'build'):raise ValueError('A2_ANDROID_OUTPUT')
    if compiler.name!='aarch64-linux-android26-clang++':raise ValueError('A2_ANDROID_COMPILER')
    cache=(native/'CMakeCache.txt').read_text().splitlines()
    expected=['CMAKE_BUILD_TYPE:STRING='+build_type,'ANDROID_ABI:UNINITIALIZED=arm64-v8a',
              'ANDROID_PLATFORM:UNINITIALIZED=android-26',
              'CMAKE_HOME_DIRECTORY:INTERNAL='+str(ROOT/'runtime-llama/src/main/cpp')]
    if any(line not in cache for line in expected):raise ValueError('A2_ANDROID_BUILD_IDENTITY')
    provenance=json.loads((native/'rune-llama-provenance.json').read_bytes())
    patch=ROOT/'runtime-llama/src/main/cpp/patches/tokenizer-abort.patch'
    if provenance!={'upstream':UPSTREAM,'tokenizer_patch_sha256':sha(patch)}:
        raise ValueError('A2_ANDROID_SOURCE_IDENTITY')
    llama=ROOT/'runtime-llama/src/main/cpp/llama.cpp'
    revision=subprocess.run(['git','-C',str(llama),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
    dirty=subprocess.run(['git','-C',str(llama),'status','--porcelain','--untracked-files=all'],check=True,capture_output=True,text=True).stdout
    if revision!=UPSTREAM or dirty:raise ValueError('A2_ANDROID_LLAMA_IDENTITY')
    patched=native/'rune-llama-patched-source'
    libs=[native/name for name in ('llama/src/libllama.a','llama/ggml/src/libggml.a',
                                  'llama/ggml/src/libggml-cpu.a','llama/ggml/src/libggml-base.a')]
    paths=[Path(__file__).resolve(),HERE/'a2_cache_probe.py',HERE/'a2_cache_probe.cpp',HERE/'scoring.cpp',HERE/'scoring.h',
           ROOT/'runtime-llama/src/main/cpp/CMakeLists.txt',patch,native/'CMakeCache.txt',native/'rune-llama-provenance.json',
           patched/'include/llama.h',patched/'ggml/include/ggml.h',*libs,compiler]
    if not all(path.is_file() for path in paths):raise ValueError('A2_ANDROID_INPUT_MISSING')
    before={str(path):sha(path) for path in paths}
    observed=host.instrument((HERE/'scoring.cpp').read_text())
    output.mkdir(parents=True,mode=0o700)
    source=output/'scoring-observed.cpp';source.write_text(observed)
    executable=output/'a2-cache-probe'
    command=[str(compiler),'-std=c++17','-O2','-DGGML_USE_CPU','-DRUNE_TOKENIZER_ABORT=1',
        '-I'+str(HERE),'-I'+str(patched/'include'),'-I'+str(patched/'ggml/include'),
        str(source),str(HERE/'a2_cache_probe.cpp'),*map(str,libs),'-llog','-landroid','-lm','-static-libstdc++','-o',str(executable)]
    with (output/'compile.log').open('xb') as log:
        subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
    validate_executable(executable.read_bytes())
    if before!={str(path):sha(path) for path in paths} or source.read_text()!=observed:
        raise ValueError('A2_ANDROID_INPUT_DRIFT')
    result=dict(scope='android-arm64-instrumented-native-copy-not-jni',upstream=revision,buildType=build_type,
        inputSha256={str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else 'android-compiler':before[str(path)] for path in paths},
        observedSourceSha256=sha(source),executableSha256=sha(executable),independentQualification=False)
    (output/'receipt.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'executableSha256':result['executableSha256'],'scope':result['scope']}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native','compiler','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();build(args.native,args.compiler,args.output)


if __name__=='__main__':main()
