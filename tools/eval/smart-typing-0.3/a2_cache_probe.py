#!/usr/bin/env python3
"""Build a host-only observed scorer copy; never modify the production scorer."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
MODEL_SHA = '7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4'
LLAMA_COMMIT = '36b10154383b60eb15baac2c7a40d2a5f784faa7'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def instrument(text):
    include = '#include "scoring.h"'; marker = '        // Decode the remaining longest common token prefix once.'
    if text.count(include) != 1 or text.count(marker) != 1: raise ValueError('A2_PROBE_SOURCE_SHAPE')
    observed = text.replace(include, include + '\nextern "C" { size_t rune_probe_reused = 0; }', 1)
    return observed.replace(marker, '        rune_probe_reused = reusable;\n' + marker, 1)


def run(model, output, native):
    if sys.platform != 'darwin': raise ValueError('A2_PROBE_HOST_UNSUPPORTED')
    model = model.resolve(strict=True); native = native.resolve(strict=True); output = output.resolve()
    if not output.is_relative_to(ROOT / 'build') or output.exists(): raise ValueError('A2_PROBE_OUTPUT')
    if sha(model) != MODEL_SHA: raise ValueError('A2_MODEL_IDENTITY')
    source = HERE / 'scoring.cpp'; header = HERE / 'scoring.h'
    observed = instrument(source.read_text())
    llama = ROOT / 'runtime-llama/src/main/cpp/llama.cpp'
    revision = subprocess.run(['git', '-C', str(llama), 'rev-parse', 'HEAD'], text=True, capture_output=True, check=True).stdout.strip()
    dirty = subprocess.run(['git', '-C', str(llama), 'status', '--porcelain', '--untracked-files=all'],
                           text=True, capture_output=True, check=True).stdout
    if revision != LLAMA_COMMIT or dirty: raise ValueError('A2_LLAMA_IDENTITY')
    cache = (native / 'CMakeCache.txt').read_text()
    if 'CMAKE_HOME_DIRECTORY:INTERNAL=' + str(HERE) not in cache.splitlines(): raise ValueError('A2_NATIVE_SOURCE_ROOT')
    sources = (source, header, HERE / 'a2_cache_probe.cpp', Path(__file__),
        ROOT / 'app/src/main/java/io/github/mesteriis/rune/keyboard/smarttyping/session/ModelPrefixWindow.kt',
        ROOT / 'app/src/test/java/io/github/mesteriis/rune/keyboard/smarttyping/session/ModelPrefixWindowTest.kt')
    bindings = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    output.mkdir(parents=True, mode=0o700)
    (output / 'scoring.h').write_bytes(header.read_bytes())
    (output / 'scoring-observed.cpp').write_text(observed)
    with (output / 'native-build.log').open('xb') as log:
        subprocess.run(['cmake', '--build', str(native), '--target', 'rune_scoring'], cwd=ROOT,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
    libs = [native / p for p in ('llama/src/libllama.a', 'llama/ggml/src/libggml.a',
        'llama/ggml/src/libggml-cpu.a', 'llama/ggml/src/ggml-blas/libggml-blas.a', 'llama/ggml/src/libggml-base.a')]
    if not all(p.is_file() for p in libs): raise ValueError('A2_NATIVE_LIBRARIES')
    executable = output / 'a2-cache-probe'
    command = ['/usr/bin/c++', '-std=c++17', '-O3', '-DNDEBUG', '-Wall', '-Wextra', '-Werror',
        '-I' + str(output), '-I' + str(llama / 'include'), '-I' + str(llama / 'ggml/include'),
        str(output / 'scoring-observed.cpp'), str(HERE / 'a2_cache_probe.cpp'), '-o', str(executable),
        *map(str, libs), '-lm', '-framework', 'Accelerate']
    with (output / 'compile.log').open('xb') as log:
        subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    with (output / 'probe.log').open('xb') as log:
        subprocess.run([str(executable), str(model)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
    if bindings != {str(p.relative_to(ROOT)): sha(p) for p in sources} or sha(model) != MODEL_SHA:
        raise ValueError('A2_PROBE_INPUT_DRIFT')
    result = dict(status='PASS', modelSha256=MODEL_SHA, sourceBindings=bindings,
                  observedCopySha256=sha(output / 'scoring-observed.cpp'), executableSha256=sha(executable),
                  librarySha256={str(p.relative_to(ROOT)): sha(p) for p in libs}, llamaCommit=revision,
                  output=(output / 'probe.log').read_text().strip(), runtime='host-only-instrumented-copy')
    (output / 'receipt.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(result['output'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('model', 'output', 'native'): parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(); run(args.model, args.output, args.native)


if __name__ == '__main__': main()
