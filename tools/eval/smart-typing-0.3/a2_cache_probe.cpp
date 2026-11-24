#include "scoring.h"
#include <algorithm>
#include <atomic>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>

extern "C" size_t rune_probe_reused;
namespace {
void silent_log(ggml_log_level, const char *, void *) noexcept {}
void require(bool ok) { if (!ok) throw std::runtime_error("cache_probe_failure"); }
struct ModelDeleter { void operator()(llama_model * value) const { llama_model_free(value); } };
std::string words(int first, int last) {
    std::ostringstream output;
    for (int i = first; i <= last; ++i) output << "word" << std::setw(2) << std::setfill('0') << i << ' ';
    return output.str();
}
}
int main(int argc, char ** argv) {
    if (argc != 2) return 2;
    llama_log_set(silent_log, nullptr); llama_backend_init();
    try {
        std::cerr << "A2_PROBE model_load_start\n";
        auto params = llama_model_default_params(); params.n_gpu_layers = 0;
        std::unique_ptr<llama_model, ModelDeleter> model(llama_model_load_from_file(argv[1], params));
        require(model != nullptr);
        std::cerr << "A2_PROBE model_load_complete\n";
        std::atomic_bool cancelled{false};
        rune::scoring::Scorer warm(model.get(), cancelled);
        const std::string prefixes[] = {words(17, 39), words(17, 40), words(34, 56)};
        size_t reused[3] = {};
        double max_delta = 0;
        for (int i = 0; i < 3; ++i) {
            const rune::scoring::Request request{prefixes[i], {{0, "hello"}, {1, "helllo"}}};
            std::cerr << "A2_PROBE warm_start " << i << "\n";
            const auto hot = warm.score(request); reused[i] = rune_probe_reused;
            std::cerr << "A2_PROBE warm_complete " << i << "\n";
            rune::scoring::Scorer fresh(model.get(), cancelled);
            std::cerr << "A2_PROBE cold_start " << i << "\n";
            const auto cold = fresh.score(request);
            std::cerr << "A2_PROBE cold_complete " << i << "\n";
            require(hot.error == rune::scoring::Error::None && cold.error == rune::scoring::Error::None);
            require(hot.scores.size() == request.candidates.size() && hot.scores.size() == cold.scores.size());
            for (size_t n = 0; n < hot.scores.size(); ++n) {
                require(hot.scores[n].id == cold.scores[n].id && hot.scores[n].scored_token_count == cold.scores[n].scored_token_count);
                const double delta = std::abs(hot.scores[n].sum_log_probability - cold.scores[n].sum_log_probability);
                require(std::isfinite(delta));
                max_delta = std::max(max_delta, delta);
                require(delta <= 0.002 * std::max(1, hot.scores[n].scored_token_count));
            }
        }
        require(reused[0] == 0 && reused[1] > 1 && reused[2] < reused[1]);
        std::cout << "initial_reused=" << reused[0] << " extended_reused=" << reused[1]
                  << " shifted_reused=" << reused[2] << " max_score_delta=" << max_delta << '\n';
    } catch (...) { std::cerr << "cache_probe_failure\n"; return 1; }
    llama_backend_free();
}
