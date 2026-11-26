import unittest
import shutil
import subprocess
import tempfile
from pathlib import Path
from a2_cache_probe import instrument


class CacheProbeTest(unittest.TestCase):
    def test_instruments_only_expected_source_markers(self):
        source = '#include "scoring.h"\n        // Decode the remaining longest common token prefix once.\n'
        result = instrument(source)
        self.assertEqual(1, result.count('rune_probe_reused = reusable;'))
        self.assertEqual(1, result.count('size_t rune_probe_reused = 0;'))
        for bad in ('', source + source, source.replace('Decode', 'Other')):
            with self.assertRaisesRegex(ValueError, 'A2_PROBE_SOURCE_SHAPE'): instrument(bad)


    def test_probe_reports_bounded_stages_and_model_failure(self):
        compiler = shutil.which('c++')
        if compiler is None:
            self.skipTest('C++ compiler unavailable')
        source_dir = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'llama.h').write_text("""
#pragma once
#include <cstddef>
struct llama_model {}; struct llama_context {}; struct llama_vocab {};
using llama_token = int; using ggml_log_level = int;
struct llama_model_params { int n_gpu_layers; };
void llama_log_set(void (*)(ggml_log_level, const char *, void *) noexcept, void *);
void llama_backend_init(); void llama_backend_free();
llama_model_params llama_model_default_params();
llama_model * llama_model_load_from_file(const char *, llama_model_params);
void llama_model_free(llama_model *);
""")
            (root / 'stub.cpp').write_text("""
#include "scoring.h"
#include <cstring>
extern "C" { size_t rune_probe_reused = 0; }
void llama_log_set(void (*)(ggml_log_level, const char *, void *) noexcept, void *) {}
void llama_backend_init() {} void llama_backend_free() {}
llama_model_params llama_model_default_params() { return {}; }
llama_model * llama_model_load_from_file(const char * p, llama_model_params) {
    return std::strcmp(p, "fail") == 0 ? nullptr : new llama_model;
}
void llama_model_free(llama_model * p) { delete p; }
namespace rune::scoring {
void Scorer::ContextDeleter::operator()(llama_context * p) const noexcept { delete p; }
Scorer::Scorer(llama_model *, std::atomic_bool & c) : vocab_(nullptr), cancelled_(c), context_(nullptr) {}
Scorer::~Scorer() = default;
Result Scorer::score(const Request & r) {
    static int call = 0; const size_t counts[] = {0, 0, 69, 0, 1, 0};
    rune_probe_reused = counts[call++];
    return {Error::None, {{r.candidates[0].id, -1., 1}, {r.candidates[1].id, -2., 1}}};
}
}
""")
            exe = root / 'probe'
            subprocess.run([compiler, '-std=c++17', '-I', str(root), '-I', str(source_dir),
                            str(source_dir / 'a2_cache_probe.cpp'), str(root / 'stub.cpp'), '-o', str(exe)],
                           check=True, capture_output=True, timeout=30)
            result = subprocess.run([str(exe), 'ok'], capture_output=True, text=True, timeout=5)
            self.assertEqual(0, result.returncode)
            self.assertEqual(['A2_PROBE model_load_start', 'A2_PROBE model_load_complete'] +
                [f'A2_PROBE {phase} {i}' for i in range(3) for phase in
                 ('warm_start', 'warm_complete', 'cold_start', 'cold_complete')], result.stderr.splitlines())
            self.assertIn('extended_reused=69', result.stdout)
            failed = subprocess.run([str(exe), 'fail'], capture_output=True, text=True, timeout=5)
            self.assertEqual(1, failed.returncode)
            self.assertEqual(['A2_PROBE model_load_start', 'cache_probe_failure'], failed.stderr.splitlines())


if __name__ == '__main__': unittest.main()
