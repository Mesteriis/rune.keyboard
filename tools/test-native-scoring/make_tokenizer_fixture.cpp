#include "gguf.h"
#include "llama.h"
#include "unicode.h"

#include <cstdint>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

// Metadata only: no weights, network, Python packages or private/user text.
// The writer and GPT2 byte alphabet come from the verified pinned llama build.
int main(int argc, char ** argv) {
    if (argc != 2) return 2;
    std::unique_ptr<gguf_context, decltype(&gguf_free)> fixture(gguf_init_empty(), gguf_free);
    if (!fixture) return 1;
    gguf_set_val_str(fixture.get(), "general.architecture", "qwen2");
    gguf_set_val_str(fixture.get(), "general.name", "Rune synthetic tokenizer contract fixture");
    gguf_set_val_str(fixture.get(), "tokenizer.ggml.model", "gpt2");
    gguf_set_val_str(fixture.get(), "tokenizer.ggml.pre", "qwen2");
    std::vector<std::string> tokens;
    for (int byte = 0; byte < 256; ++byte) tokens.push_back(unicode_byte_to_utf8(static_cast<uint8_t>(byte)));
    // aa ensures long letter runs really execute the BPE merge queue.
    tokens.insert(tokens.end(), {"aa", "<|synthetic_bos|>", "<|synthetic_eos|>"});
    std::vector<const char *> strings;
    for (const auto & token : tokens) strings.push_back(token.c_str());
    gguf_set_arr_str(fixture.get(), "tokenizer.ggml.tokens", strings.data(), strings.size());
    const char * merges[] = {"a a"};
    gguf_set_arr_str(fixture.get(), "tokenizer.ggml.merges", merges, 1);
    std::vector<int32_t> types(tokens.size(), LLAMA_TOKEN_TYPE_NORMAL);
    types[257] = types[258] = LLAMA_TOKEN_TYPE_CONTROL;
    gguf_set_arr_data(fixture.get(), "tokenizer.ggml.token_type", GGUF_TYPE_INT32, types.data(), types.size());
    gguf_set_val_u32(fixture.get(), "tokenizer.ggml.bos_token_id", 257);
    gguf_set_val_u32(fixture.get(), "tokenizer.ggml.eos_token_id", 258);
    gguf_set_val_bool(fixture.get(), "tokenizer.ggml.add_bos_token", true);
    gguf_set_val_bool(fixture.get(), "tokenizer.ggml.add_eos_token", false);
    if (!gguf_write_to_file(fixture.get(), argv[1], true)) return 1;
    std::cout << "Wrote synthetic QWEN2 vocabulary: 259 tokens, 1 merge, no weights\n";
    return 0;
}
