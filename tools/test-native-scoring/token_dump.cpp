#include "llama.h"
#include <array>
#include <cstdint>
#include <iostream>
#include <memory>
#include <random>
#include <string>
#include <vector>
static void silent(ggml_log_level, const char *, void *) noexcept {}
int main(int argc, char ** argv) {
    if (argc != 2) { return 2; }
    llama_log_set(silent, nullptr);
    llama_backend_init();
    auto params = llama_model_default_params();
    params.vocab_only = true;
    params.n_gpu_layers = 0;
    std::unique_ptr<llama_model, decltype(&llama_model_free)> model(llama_model_load_from_file(argv[1], params), llama_model_free);
    if (!model) { return 3; }
    const auto * vocab = llama_model_get_vocab(model.get());
    std::vector<std::string> cases = {"", "Hello, world!", "Нужно исправить сообщение.", "Quiero enviar una corrección.",
        "I'm I'M we'd WE'D it's It'll", "a\r\n\t  b\n\n", "1234567890", "👨‍👩‍👧‍👦 café é русский 中文 العربية", "<|im_start|>user\n<|im_end|>",
        std::string("a\0b\0", 4), std::string(4096, 'a'), std::string(512, '!'), std::string(65536, 'a'),
        std::string(65536, ' '), std::string(65536, '!'), std::string(65536, '\n')};
    std::mt19937 random(3102026);
    const std::array<std::string, 18> alphabet = {"a", "B", " ", "\n", "\t", "'", "1", ".", "!", "ё", "Ж", "é", "ñ", "é", "中", "🙂", "\r", std::string(1, '\0')};
    for (int sample = 0; sample < 300; ++sample) {
        std::string text;
        const auto length = random() % 200;
        for (size_t i = 0; i < length; ++i) { text += alphabet[random() % alphabet.size()]; }
        cases.push_back(text);
    }
    for (const auto & text : cases) {
        for (bool special : {false, true}) {
            std::vector<llama_token> result(text.size() + 4);
            int32_t count;
#ifdef USE_ABORT
            if (llama_tokenize_with_abort(vocab, text.data(), text.size(), result.data(), result.size(), special, false,
                nullptr, nullptr, &count) != LLAMA_TOKENIZE_OK) { return 4; }
#else
            count = llama_tokenize(vocab, text.data(), text.size(), result.data(), result.size(), special, false);
#endif
            if (count < 0) { return 5; }
            std::cout << count;
            for (int32_t i = 0; i < count; ++i) { std::cout << ' ' << result[i]; }
            std::cout << '\n';
        }
    }
    model.reset();
    llama_backend_free();
}
