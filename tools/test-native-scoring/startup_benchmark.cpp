#include "scoring.h"

#include <chrono>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <iostream>
#include <memory>
#include <stdexcept>

namespace {
void require(bool value) { if (!value) throw std::runtime_error("startup_contract"); }
void silent_log(ggml_log_level, const char *, void *) noexcept {}
struct ModelDeleter { void operator()(llama_model * model) const noexcept { llama_model_free(model); } };
struct Backend { Backend() { llama_backend_init(); } ~Backend() { llama_backend_free(); } };

template<class Function> void measure(int cycle, int stage, Function action) {
    const auto cpu_start = std::clock();
    const auto wall_start = std::chrono::steady_clock::now();
    require(cpu_start != static_cast<std::clock_t>(-1));
    action();
    const auto wall_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::steady_clock::now() - wall_start).count();
    const auto cpu_end = std::clock();
    require(cpu_end != static_cast<std::clock_t>(-1) && cpu_end >= cpu_start);
    const auto cpu_us = static_cast<int64_t>(1000000.0 * (cpu_end - cpu_start) / CLOCKS_PER_SEC);
    std::cout << cycle << ',' << stage << ',' << wall_us << ',' << cpu_us << '\n';
}
}

// Fixed synthetic request only. Invoke through the exact-model CMake verifier.
int main(int argc, char ** argv) {
    if (argc != 2) return 2;
    llama_log_set(silent_log, nullptr);
    try {
        std::unique_ptr<Backend> backend;
        measure(-1, 0, [&] { backend = std::make_unique<Backend>(); });
        const rune::scoring::Request request{"Пекарь готовит ",
            {{0, "ттесто"}, {1, "тесто"}, {2, "место"}, {3, "тесть"}}};
        std::vector<rune::scoring::Score> reference;
        for (int cycle = 0; cycle < 3; ++cycle) {
            std::unique_ptr<llama_model, ModelDeleter> model;
            measure(cycle, 1, [&] {
                auto params = llama_model_default_params(); params.n_gpu_layers = 0;
                model.reset(llama_model_load_from_file(argv[1], params));
                require(model != nullptr);
            });
            std::atomic_bool cancelled{false};
            std::unique_ptr<rune::scoring::Scorer> scorer;
            measure(cycle, 2, [&] { scorer = std::make_unique<rune::scoring::Scorer>(model.get(), cancelled); });
            for (int sample = 0; sample < 4; ++sample) {
                rune::scoring::Result result;
                measure(cycle, 3 + sample, [&] { result = scorer->score(request); });
                require(result.error == rune::scoring::Error::None && result.scores.size() == 4);
                if (reference.empty()) reference = result.scores;
                for (size_t i = 0; i < reference.size(); ++i) {
                    require(result.scores[i].id == reference[i].id &&
                        result.scores[i].scored_token_count == reference[i].scored_token_count &&
                        std::isfinite(result.scores[i].sum_log_probability) &&
                        result.scores[i].sum_log_probability == reference[i].sum_log_probability);
                }
            }
            measure(cycle, 7, [&] { scorer.reset(); });
            measure(cycle, 8, [&] { model.reset(); });
        }
        measure(-1, 9, [&] { backend.reset(); });
    } catch (...) {
        // A nonzero exit invalidates every earlier row; never emit exception text or paths.
        return 3;
    }
    return 0;
}
