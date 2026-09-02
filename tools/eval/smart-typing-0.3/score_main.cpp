#include "scoring.h"
#include "nlohmann/json.hpp"

#include <chrono>
#include <iostream>
#include <memory>

namespace {
void silent_log(ggml_log_level, const char *, void *) noexcept {}
struct ModelDeleter { void operator()(llama_model * model) const noexcept { llama_model_free(model); } };
bool read_line(std::string & line, bool & oversized) {
    line.clear();
    oversized = false;
    char character;
    bool any = false;
    while (std::cin.get(character)) {
        any = true;
        if (character == '\n') break;
        if (line.size() < 65536) line.push_back(character);
        else oversized = true;
    }
    return any;
}
bool valid_id(const std::string & id) {
    if (id.empty() || id.size() > 128) return false;
    for (const auto c : id) {
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
              (c >= '0' && c <= '9') || c == '-' || c == '_' || c == '.')) return false;
    }
    return true;
}
}

int main(int argc, char ** argv) {
    if (argc != 2) { std::cerr << "usage: rune-score MODEL_FILE\n"; return 2; }
    llama_log_set(silent_log, nullptr);
    llama_backend_init();
    try {
        auto params = llama_model_default_params();
        params.n_gpu_layers = 0;
        std::unique_ptr<llama_model, ModelDeleter> model(llama_model_load_from_file(argv[1], params));
        if (!model) { std::cerr << "MODEL_LOAD_FAILED\n"; return 3; }
        std::atomic_bool cancelled{false};
        rune::scoring::Scorer scorer(model.get(), cancelled);
        std::string line;
        bool oversized;
        while (read_line(line, oversized)) {
            nlohmann::json response = {{"id", ""}, {"error", "INVALID_REQUEST"}};
            try {
                if (oversized) throw std::invalid_argument("request_size");
                const auto input = nlohmann::json::parse(line);
                const auto id = input.at("id").get<std::string>();
                if (!valid_id(id)) throw std::invalid_argument("request_id");
                response["id"] = id;
                if (input.size() != 3 || !input.at("candidates").is_array()) throw std::invalid_argument("shape");
                rune::scoring::Request request{input.at("prefix").get<std::string>(), {}};
                const auto & candidates = input.at("candidates");
                if (candidates.size() > 8) {
                    response["error"] = "TOO_MANY_CANDIDATES";
                } else {
                    for (size_t i = 0; i < candidates.size(); ++i)
                        request.candidates.push_back({static_cast<int>(i), candidates[i].get<std::string>()});
                    const auto start = std::chrono::steady_clock::now();
                    const auto result = scorer.score(request);
                    if (result.error != rune::scoring::Error::None) {
                        response["error"] = rune::scoring::error_name(result.error);
                    } else {
                        response.erase("error");
                        response["scores"] = nlohmann::json::array();
                        for (const auto & score : result.scores)
                            response["scores"].push_back({{"id", score.id},
                                {"sumLogProbability", score.sum_log_probability},
                                {"scoredTokenCount", score.scored_token_count}});
                        response["durationMillis"] = std::chrono::duration_cast<std::chrono::milliseconds>(
                            std::chrono::steady_clock::now() - start).count();
                    }
                }
            } catch (...) { /* Stable error only: never emit source text or exception payload. */ }
            std::cout << response.dump() << '\n' << std::flush;
        }
    } catch (...) { std::cerr << "SCORING_FAILED\n"; return 4; }
    llama_backend_free();
    return 0;
}
