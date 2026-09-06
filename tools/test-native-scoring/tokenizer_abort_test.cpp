#include "llama.h"
#include "llama-vocab.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <cstring>
#include <iostream>
#include <memory>
#include <random>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {
void require(bool condition, const char * message) {
    if (!condition) { throw std::runtime_error(message); }
}
void silent_log(ggml_log_level, const char *, void *) noexcept {}
struct ModelDeleter { void operator()(llama_model * model) const { llama_model_free(model); } };
using Model = std::unique_ptr<llama_model, ModelDeleter>;
struct Callback {
    std::array<size_t, 8> visits{};
    int cancel_stage = -1;
    size_t cancel_visit = 1;
};
bool observe(llama_tokenize_stage stage, void * data) {
    auto & state = *static_cast<Callback *>(data);
    const auto visits = ++state.visits[stage];
    return state.cancel_stage == stage && visits >= state.cancel_visit;
}
Model load(const char * file, const char * pre = nullptr) {
    auto params = llama_model_default_params();
    params.vocab_only = true;
    params.n_gpu_layers = 0;
    llama_model_kv_override overrides[2] = {};
    if (pre) {
        overrides[0].tag = LLAMA_KV_OVERRIDE_TYPE_STR;
        std::strcpy(overrides[0].key, "tokenizer.ggml.pre");
        std::strcpy(overrides[0].val_str, pre);
        params.kv_overrides = overrides;
    }
    Model model(llama_model_load_from_file(file, params));
    require(model != nullptr, "load_model");
    return model;
}
std::vector<llama_token> old_tokens(const llama_vocab * vocab, const std::string & text, bool special) {
    std::vector<llama_token> result(text.size() + 4);
    const auto count = llama_tokenize(vocab, text.data(), static_cast<int32_t>(text.size()),
        result.data(), static_cast<int32_t>(result.size()), special, false);
    require(count >= 0, "old_tokenize_failed");
    result.resize(static_cast<size_t>(count));
    return result;
}
std::vector<llama_token> new_tokens(const llama_vocab * vocab, const std::string & text, bool special, Callback * state) {
    std::vector<llama_token> result(text.size() + 4);
    int32_t count = -9;
    const auto status = llama_tokenize_with_abort(vocab, text.data(), static_cast<int32_t>(text.size()),
        result.data(), static_cast<int32_t>(result.size()), special, false,
        state ? observe : nullptr, state, &count);
    require(status == LLAMA_TOKENIZE_OK, "new_tokenize_failed");
    require(count >= 0 && static_cast<size_t>(count) <= result.size(), "invalid_success_count");
    result.resize(static_cast<size_t>(count));
    return result;
}
void equivalent(const llama_vocab * vocab, const std::string & text) {
    for (bool special : {false, true}) {
        const auto expected = old_tokens(vocab, text, special);
        Callback state;
        require(expected == new_tokens(vocab, text, special, &state), "callback_equivalence");
        require(expected == new_tokens(vocab, text, special, nullptr), "null_callback_equivalence");
    }
}
void cancelled_then_success(const llama_vocab * vocab, const std::string & input, int stage, size_t visit) {
    std::array<llama_token, 16> output;
    output.fill(-12345);
    Callback state;
    state.cancel_stage = stage;
    state.cancel_visit = visit;
    int32_t count = -9;
    const auto status = llama_tokenize_with_abort(vocab, input.data(), static_cast<int32_t>(input.size()),
        output.data(), static_cast<int32_t>(output.size()), false, false, observe, &state, &count);
    require(status == LLAMA_TOKENIZE_CANCELLED, "cancel_status");
    require(count == 0, "cancel_count");
    require(state.visits[stage] == visit, "cancel_inside_stage");
    require(std::all_of(output.begin(), output.end(), [](auto token) { return token == -12345; }), "cancel_partial_output");
    equivalent(vocab, "After cancellation: next request succeeds. Следующий запрос.");
    std::cout << "cancel stage=" << stage << " visit=" << visit << " bytes=" << input.size() << " PASS\n";
}
void buffer_contract(const llama_vocab * vocab) {
    const std::string input = "hello world";
    auto expected = old_tokens(vocab, input, false);
    require(expected.size() > 1, "buffer_fixture");
    llama_token output = -12345;
    int32_t count = -9;
    auto status = llama_tokenize_with_abort(vocab, input.data(), input.size(), &output, 1, false, false, nullptr, nullptr, &count);
    require(status == LLAMA_TOKENIZE_BUFFER_TOO_SMALL && count == static_cast<int32_t>(expected.size()), "buffer_count");
    require(output == -12345, "buffer_partial_write");
    require(llama_tokenize(vocab, input.data(), input.size(), &output, 1, false, false) == -count, "legacy_negative_count");
    status = llama_tokenize_with_abort(vocab, input.data(), input.size(), nullptr, 0, false, false, nullptr, nullptr, &count);
    require(status == LLAMA_TOKENIZE_BUFFER_TOO_SMALL && count == static_cast<int32_t>(expected.size()), "query_count");
    status = llama_tokenize_with_abort(vocab, nullptr, 0, nullptr, 0, false, false, nullptr, nullptr, &count);
    require(status == LLAMA_TOKENIZE_OK && count == 0, "empty_input");
    for (int kind = 0; kind < 6; ++kind) {
        count = -9;
        status = llama_tokenize_with_abort(kind == 0 ? nullptr : vocab,
            kind == 1 ? nullptr : input.data(), kind == 2 ? -1 : static_cast<int32_t>(input.size()),
            kind == 3 ? nullptr : &output, kind == 4 ? -1 : 1, false, kind == 5, nullptr, nullptr, &count);
        require(status == LLAMA_TOKENIZE_INVALID_ARGUMENT && count == 0, "invalid_argument");
    }
    require(llama_tokenize_with_abort(vocab, input.data(), input.size(), &output, 1, false, false, nullptr, nullptr, nullptr)
        == LLAMA_TOKENIZE_INVALID_ARGUMENT, "null_out_count");
    const std::vector<std::string> malformed = {"\x80", "\xc0\xaf", "\xe0\x80\xaf", "\xed\xa0\x80", "\xf4\x90\x80\x80", "\xf5\x80\x80\x80", "\xe2\x82", "\xc2x"};
    for (const auto & text : malformed) {
        count = -9;
        status = llama_tokenize_with_abort(vocab, text.data(), text.size(), &output, 1, false, false, nullptr, nullptr, &count);
        require(status == LLAMA_TOKENIZE_INVALID_UTF8 && count == 0 && output == -12345, "invalid_utf8");
    }
    std::cout << "buffer/argument/strict_utf8 contracts PASS\n";
}
void unsupported(const llama_vocab * vocab) {
    int32_t count = -9;
    llama_token token = -12345;
    Callback state;
    const auto status = llama_tokenize_with_abort(vocab, "hello", 5, &token, 1, false, false, observe, &state, &count);
    require(status == LLAMA_TOKENIZE_UNSUPPORTED && count == 0 && token == -12345, "unsupported_status");
    require(state.visits == std::array<size_t, 8>{}, "unsupported_callback");
}
}
int main(int argc, char ** argv) {
    if (argc != 2 && !(argc == 3 && std::string(argv[2]) == "--synthetic")) { return 2; }
    llama_log_set(silent_log, nullptr);
    llama_backend_init();
    try {
        auto model = load(argv[1]);
        const auto * vocab = llama_model_get_vocab(model.get());
        require(vocab->get_type() == LLAMA_VOCAB_TYPE_BPE && vocab->get_pre_type() == LLAMA_VOCAB_PRE_TYPE_QWEN2,
            "verified_tokenizer_type");
        std::cout << "metadata type=BPE preset=QWEN2 model=" << vocab->get_tokenizer_model() << '\n';
        if (argc == 3) {
            require(llama_vocab_n_tokens(vocab) == 259, "synthetic_vocab_size");
            require(old_tokens(vocab, "aaaa", false) == std::vector<llama_token>{256, 256}, "synthetic_merge_reachable");
            require(old_tokens(vocab, "a", true) == std::vector<llama_token>{257, 97}, "synthetic_bos_reachable");
        }
        std::vector<std::string> cases = {"", "Hello, world!", "Нужно исправить сообщение.", "Quiero enviar una corrección.",
            "I'm I'M we'd WE'D it's It'll", "a\r\n\t  b\n\n", "1234567890", "👨‍👩‍👧‍👦 café é русский 中文 العربية", "<|im_start|>user\n<|im_end|>",
            std::string("a\0b\0", 4), std::string(4096, 'a'), std::string(512, '!'), std::string(65536, 'a'),
            std::string(65536, ' '), std::string(65536, '!'), std::string(65536, '\n')};
        for (const auto & text : cases) { equivalent(vocab, text); }
        std::mt19937 random(3102026);
        const std::array<std::string, 18> alphabet = {"a", "B", " ", "\n", "\t", "'", "1", ".", "!", "ё", "Ж", "é", "ñ", "é", "中", "🙂", "\r", std::string(1, '\0')};
        for (int sample = 0; sample < 300; ++sample) {
            std::string text;
            const auto length = random() % 200;
            for (size_t i = 0; i < length; ++i) { text += alphabet[random() % alphabet.size()]; }
            equivalent(vocab, text);
        }
        std::cout << "equivalence fixed=16 randomized=300 add_special=false/true callback=null/observer PASS\n";
        buffer_contract(vocab);
        std::string long_letters(262144, 'a');
        for (int stage = 0; stage < 8; ++stage) {
            // Partition work is bounded by the model's special-token table here.
            cancelled_then_success(vocab, long_letters, stage, stage == LLAMA_TOKENIZE_STAGE_PARTITION ? 1 : 3);
        }
        for (char c : {' ', '!', '\n'}) {
            cancelled_then_success(vocab, std::string(262144, c), LLAMA_TOKENIZE_STAGE_PRE_SPLIT, 3);
        }
        std::atomic_bool parallel_ok{true};
        std::vector<std::thread> threads;
        for (int worker = 0; worker < 4; ++worker) {
            threads.emplace_back([&, worker] {
                try {
                    for (int iteration = 0; iteration < 20; ++iteration) {
                        Callback state;
                        state.cancel_stage = worker % 2 == 0 ? LLAMA_TOKENIZE_STAGE_UNICODE : -1;
                        const std::string text = "Concurrent calls: независимые данные отмены.";
                        std::vector<llama_token> output(128, -12345);
                        int32_t count = -9;
                        const auto status = llama_tokenize_with_abort(vocab, text.data(), text.size(), output.data(), output.size(),
                            false, false, observe, &state, &count);
                        require(status == (worker % 2 == 0 ? LLAMA_TOKENIZE_CANCELLED : LLAMA_TOKENIZE_OK), "parallel_status");
                        if (status == LLAMA_TOKENIZE_OK) {
                            output.resize(count);
                            require(output == old_tokens(vocab, text, false), "parallel_equivalence");
                        } else {
                            require(count == 0, "parallel_count");
                            require(std::all_of(output.begin(), output.end(), [](auto token) { return token == -12345; }),
                                "parallel_no_partial_output");
                        }
                    }
                } catch (...) { parallel_ok.store(false); }
            });
        }
        for (auto & thread : threads) { thread.join(); }
        require(parallel_ok.load(), "parallel_isolation");
        std::cout << "parallel per-call isolation threads=4 requests=80 PASS\n";
        llama_vocab empty;
        unsupported(&empty);
        for (const char * pre : {"gpt-2", "qwen35"}) {
            auto other = load(argv[1], pre);
            const auto * other_vocab = llama_model_get_vocab(other.get());
            require(other_vocab->get_pre_type() != LLAMA_VOCAB_PRE_TYPE_QWEN2, "override_fixture");
            unsupported(other_vocab);
            std::cout << "unsupported preset=" << pre << " PASS\n";
        }
        std::cout << "ALL PASS\n";
    } catch (const std::exception & error) {
        std::cerr << "FAIL " << error.what() << '\n';
        llama_backend_free();
        return 1;
    }
    llama_backend_free();
    return 0;
}
