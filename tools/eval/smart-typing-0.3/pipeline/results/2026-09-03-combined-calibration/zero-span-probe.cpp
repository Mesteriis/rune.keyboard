#include "llama.h"
#include "nlohmann/json.hpp"
#include <algorithm>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>
struct Deleter { void operator()(llama_model *p) const { llama_model_free(p); } };
void quiet(ggml_log_level, const char *, void *) noexcept {}
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    llama_log_set(quiet, nullptr);
    try {
        auto params = llama_model_default_params(); params.vocab_only = true;
        std::unique_ptr<llama_model, Deleter> model(llama_model_load_from_file(argv[1], params));
        if (!model) return 3;
        const auto *vocab = llama_model_get_vocab(model.get());
        std::string line;
        while (std::getline(std::cin, line)) {
            auto row = nlohmann::json::parse(line);
            std::vector<std::vector<llama_token>> sets;
            for (const auto &candidate : row.at("candidates")) {
                const auto text = row.at("prefix").get<std::string>() + candidate.get<std::string>();
                std::vector<llama_token> tokens(257);
                const int n = llama_tokenize(vocab, text.data(), static_cast<int32_t>(text.size()), tokens.data(), 257, false, false);
                if (n < 0 || n > 256) return 4;
                tokens.resize(static_cast<size_t>(n));
                if (llama_vocab_get_add_bos(vocab)) tokens.insert(tokens.begin(), llama_vocab_bos(vocab));
                sets.push_back(std::move(tokens));
            }
            if (sets.empty()) return 5;
            size_t common = sets[0].size();
            for (const auto &tokens : sets) {
                size_t matched = 0;
                while (matched < common && matched < tokens.size() && tokens[matched] == sets[0][matched]) ++matched;
                common = matched;
            }
            nlohmann::json spans = nlohmann::json::array();
            for (const auto &tokens : sets) spans.push_back(tokens.size() - common);
            std::cout << nlohmann::json{{"id", row.at("id")}, {"commonTokens", common}, {"divergentTokens", spans}}.dump() << '\n';
        }
    } catch (...) { return 6; }
}
