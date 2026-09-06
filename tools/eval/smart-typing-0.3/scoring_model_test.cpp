#include "scoring.h"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <memory>
#include <stdexcept>

namespace {
void require(bool value) { if (!value) throw std::runtime_error("model_contract_failure"); }
void silent_log(ggml_log_level, const char *, void *) noexcept {}
struct ModelDeleter { void operator()(llama_model * model) const { llama_model_free(model); } };
struct ContextDeleter { void operator()(llama_context * context) const { llama_free(context); } };

std::vector<llama_token> full_tokens(const llama_vocab * vocab, const std::string & text) {
    std::vector<llama_token> tokens(256);
    const int count = llama_tokenize(vocab, text.data(), static_cast<int32_t>(text.size()),
        tokens.data(), 256, false, false);
    require(count > 0 && count <= 256);
    tokens.resize(static_cast<size_t>(count));
    if (llama_vocab_get_add_bos(vocab)) tokens.insert(tokens.begin(), llama_vocab_bos(vocab));
    return tokens;
}

// Independent token-at-a-time oracle: no batched logit-index assumptions, no KV
// copying. Deliberately slow; compare it before trusting a whole corpus run.
std::vector<rune::scoring::Score> reference(llama_model * model, const rune::scoring::Request & request) {
    const auto * vocab = llama_model_get_vocab(model);
    std::vector<std::vector<llama_token>> sequences;
    for (const auto & candidate : request.candidates)
        sequences.push_back(full_tokens(vocab, request.prefix + candidate.continuation));
    size_t common = sequences[0].size();
    for (const auto & sequence : sequences) {
        size_t matched = 0;
        while (matched < common && matched < sequence.size() && sequence[matched] == sequences[0][matched]) ++matched;
        common = matched;
    }
    require(common > 0);
    auto params = llama_context_default_params();
    params.n_ctx = 256; params.n_batch = 64; params.n_ubatch = 64;
    params.n_threads = params.n_threads_batch = 4; params.no_perf = true;
    params.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_DISABLED;
    std::unique_ptr<llama_context, ContextDeleter> context(llama_init_from_model(model, params));
    require(context != nullptr);
    std::vector<rune::scoring::Score> results;
    for (size_t index = 0; index < sequences.size(); ++index) {
        llama_memory_clear(llama_get_memory(context.get()), true);
        auto & sequence = sequences[index];
        rune::scoring::Score result{request.candidates[index].id, 0, 0};
        for (size_t position = 0; position + 1 < sequence.size(); ++position) {
            require(llama_decode(context.get(), llama_batch_get_one(&sequence[position], 1)) == 0);
            if (position + 1 < common) continue;
            const auto * logits = llama_get_logits_ith(context.get(), -1);
            const int size = llama_vocab_n_tokens(vocab);
            double maximum = logits[0];
            for (int i = 1; i < size; ++i) maximum = std::max(maximum, static_cast<double>(logits[i]));
            double sum = 0;
            for (int i = 0; i < size; ++i) sum += std::exp(static_cast<double>(logits[i]) - maximum);
            result.sum_log_probability += static_cast<double>(logits[sequence[position + 1]]) - maximum - std::log(sum);
            ++result.scored_token_count;
        }
        results.push_back(result);
    }
    return results;
}
}

int main(int argc, char ** argv) {
    if (argc != 2) return 2;
    llama_log_set(silent_log, nullptr);
    llama_backend_init();
    try {
        auto params = llama_model_default_params(); params.n_gpu_layers = 0;
        std::unique_ptr<llama_model, ModelDeleter> model(llama_model_load_from_file(argv[1], params));
        require(model != nullptr);
        std::atomic_bool cancelled{false};
        rune::scoring::Scorer scorer(model.get(), cancelled);
        std::vector<rune::scoring::Request> requests{
            {"Please check the", {{0, " address"}, {1, " adress"}, {2, " address"}}},
            {"Нужно исправить", {{0, " сообщение"}, {1, " сообшение"}, {2, " сообщения"}}},
            {"Quiero enviar un", {{0, " mensaje"}, {1, " mensage"}, {2, " mensajes"}}},
            {"Una palabra:", {{0, " corrección"}, {1, " correcion"}}},
        };
        const auto * vocab = llama_model_get_vocab(model.get());
        auto prefix_for_tokens = [vocab](size_t count) {
            std::string prefix = "context";
            while (full_tokens(vocab, prefix).size() < count) prefix += " x";
            require(full_tokens(vocab, prefix).size() == count);
            return prefix;
        };
        // First divergent score on the final row of a batch, then the next
        // batch; and a whole first batch with no requested logits.
        requests.push_back({prefix_for_tokens(64), {{0, " a b"}, {1, " c d"}}});
        requests.push_back({prefix_for_tokens(66), {{0, " a b"}, {1, " c d"}}});
        double maximum_delta = 0;
        bool within_tolerance = true;
        for (const auto & request : requests) {
            const auto actual = scorer.score(request);
            if (actual.error != rune::scoring::Error::None)
                std::cerr << "scorer_error=" << rune::scoring::error_name(actual.error) << '\n';
            require(actual.error == rune::scoring::Error::None);
            const auto expected = reference(model.get(), request);
            require(actual.scores.size() == expected.size());
            for (size_t i = 0; i < expected.size(); ++i) {
                require(actual.scores[i].scored_token_count == expected[i].scored_token_count);
                const double delta = std::abs(actual.scores[i].sum_log_probability - expected[i].sum_log_probability);
                maximum_delta = std::max(maximum_delta, delta);
                std::cout << "oracle_candidate=" << i << " scored_tokens=" << expected[i].scored_token_count
                    << " sum_delta=" << delta << '\n';
                // CPU batching may select different floating-point kernels.
                within_tolerance &= delta <= 0.002 * std::max(1, expected[i].scored_token_count);
            }
        }
        require(within_tolerance);
        const auto identical = scorer.score({"Same", {{0, " word"}, {1, " word"}}});
        require(identical.error == rune::scoring::Error::ScoringFailed && identical.scores.empty());
        cancelled = true;
        require(scorer.score(requests[0]).error == rune::scoring::Error::Cancelled);
        cancelled = false;
        const auto repeated = scorer.score(requests[0]);
        require(repeated.error == rune::scoring::Error::None);
        require(repeated.scores[0].sum_log_probability == repeated.scores[2].sum_log_probability);
        std::string continuation;
        for (int i = 0; i < 64; ++i) continuation += " x";
        require(full_tokens(vocab, continuation).size() == 64);
        const auto full_prefix = prefix_for_tokens(192);
        require(full_tokens(vocab, full_prefix + continuation).size() == 256);
        require(scorer.score({full_prefix, {{0, continuation}, {1, " z"}}}).error == rune::scoring::Error::None);
        require(scorer.score({prefix_for_tokens(193), {{0, " a"}, {1, " b"}}}).error == rune::scoring::Error::ContextTooLong);
        require(scorer.score({"context", {{0, continuation + " x"}, {1, " b"}}}).error == rune::scoring::Error::ContextTooLong);
        std::cout << "model scoring oracle passed; maximum_sum_delta=" << maximum_delta << '\n';
    } catch (...) { std::cerr << "model scoring contract failed\n"; return 1; }
    llama_backend_free();
}
