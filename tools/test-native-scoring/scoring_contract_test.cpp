#include "candidate_score_wire.h"
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <stdexcept>

// Deterministic model double. Exercises the real scoring loop and error policy;
// does not claim Qwen tokenization, inference quality or device performance.
struct llama_vocab { bool bos = false; };
struct llama_model { llama_vocab vocab; };
struct llama_context { float logits[64][16]{}; };
namespace {
int tokenize_calls = 0, decode_calls = 0, decoded_tokens = 0, clears = 0, suffix_removes = 0;
int cancel_tokenize_call = 0, fail_decode_call = 0, cancel_decode_call = 0;
bool nonfinite_logits = false;
std::atomic_bool * cancellation = nullptr;
llama_tokenize_status tokenizer_status = LLAMA_TOKENIZE_OK;
llama_token token(char c) { return static_cast<unsigned char>(c) % 14 + 1; }
void check_at(bool ok, int line) { if (!ok) { std::cerr << "contract line " << line << " failed\n"; throw std::runtime_error("contract_failed"); } }
#define check(ok) check_at(ok, __LINE__)
}
extern "C" {
const llama_vocab * llama_model_get_vocab(const llama_model * model) { return &model->vocab; }
llama_context_params llama_context_default_params() { return {}; }
llama_context * llama_init_from_model(llama_model *, llama_context_params p) {
    check(p.n_ctx == 256 && p.n_batch == 64 && p.n_ubatch == 1 &&
        p.n_threads == 4 && p.n_threads_batch == 4 && p.flash_attn_type == LLAMA_FLASH_ATTN_TYPE_DISABLED);
    check(p.abort_callback && p.abort_callback_data && p.no_perf);
    return new llama_context;
}
void llama_free(llama_context * context) { delete context; }
llama_memory_t llama_get_memory(const llama_context *) { return nullptr; }
void llama_memory_clear(llama_memory_t, bool data) { check(data); ++clears; }
bool llama_memory_seq_rm(llama_memory_t, llama_seq_id sequence, llama_pos start, llama_pos end) {
    check(sequence == 0 && start >= 0 && start < 256 && end == -1);
    ++suffix_removes;
    return true;
}
bool llama_vocab_get_add_bos(const llama_vocab * vocab) { return vocab->bos; }
llama_token llama_vocab_bos(const llama_vocab *) { return 15; }
int32_t llama_vocab_n_tokens(const llama_vocab *) { return 16; }
llama_tokenize_status llama_tokenize_with_abort(const llama_vocab *, const char * text, int32_t length,
    llama_token * output, int32_t capacity, bool add_special, bool parse_special,
    llama_tokenize_abort_callback abort, void * data, int32_t * count) {
    check(!add_special && !parse_special && abort && data);
    ++tokenize_calls;
    *count = 0;
    if (tokenizer_status != LLAMA_TOKENIZE_OK) return tokenizer_status;
    if (tokenize_calls == cancel_tokenize_call) cancellation->store(true);
    if (abort(LLAMA_TOKENIZE_STAGE_BPE_MERGE, data)) return LLAMA_TOKENIZE_CANCELLED;
    *count = length;
    if (length > capacity) return LLAMA_TOKENIZE_BUFFER_TOO_SMALL;
    for (int32_t i = 0; i < length; ++i) output[i] = token(text[i]);
    return LLAMA_TOKENIZE_OK;
}
llama_batch llama_batch_init(int32_t n, int32_t embd, int32_t seqs) {
    check(embd == 0 && seqs == 1);
    llama_batch b{};
    b.token = new llama_token[n]; b.pos = new llama_pos[n]; b.n_seq_id = new int32_t[n];
    b.seq_id = new llama_seq_id *[n + 1]{}; b.logits = new int8_t[n];
    for (int32_t i = 0; i < n; ++i) b.seq_id[i] = new llama_seq_id[1];
    return b;
}
void llama_batch_free(llama_batch b) {
    for (int32_t i = 0; b.seq_id[i]; ++i) delete[] b.seq_id[i];
    delete[] b.token; delete[] b.pos; delete[] b.n_seq_id; delete[] b.seq_id; delete[] b.logits;
}
int32_t llama_decode(llama_context * context, llama_batch b) {
    ++decode_calls;
    decoded_tokens += b.n_tokens;
    if (decode_calls == fail_decode_call) return 1;
    if (decode_calls == cancel_decode_call) { cancellation->store(true); return 2; }
    for (int32_t row = 0; row < b.n_tokens; ++row) {
        check(b.n_seq_id[row] == 1 && b.seq_id[row][0] == 0 && b.pos[row] >= 0 && b.pos[row] < 256);
        for (int32_t t = 0; t < 16; ++t) context->logits[row][t] = 0.1f * static_cast<float>((t + b.pos[row]) % 7);
        if (nonfinite_logits) context->logits[row][0] = std::numeric_limits<float>::quiet_NaN();
    }
    return 0;
}
float * llama_get_logits_ith(llama_context * context, int32_t row) { return context->logits[row]; }
}

int main() try {
    using namespace rune::scoring;
    llama_model model;
    std::atomic_bool cancelled{false};
    cancellation = &cancelled;
    Scorer scorer(&model, cancelled);
    Request valid{"ab", {{7, "cd"}, {9, "ef"}}};
    const auto first = scorer.score(valid);
    check(first.error == Error::None && first.scores.size() == 2 && clears == 0 && suffix_removes == 2);
    for (size_t i = 0; i < first.scores.size(); ++i) {
        double oracle = 0;
        for (size_t pos = 2; pos < 4; ++pos) {
            double denominator = 0;
            for (int t = 0; t < 16; ++t) denominator += std::exp(static_cast<double>(0.1f * static_cast<float>((t + pos - 1) % 7)));
            oracle += 0.1f * static_cast<float>((token(valid.candidates[i].continuation[pos - 2]) + pos - 1) % 7) - std::log(denominator);
        }
        check(first.scores[i].scored_token_count == 2 && std::abs(first.scores[i].sum_log_probability - oracle) < 1e-12);
    }
    const auto cold_decoded_tokens = decoded_tokens;
    const auto warm = scorer.score(valid);
    check(warm.error == Error::None && warm.scores[0].sum_log_probability == first.scores[0].sum_log_probability);
    check(decoded_tokens - cold_decoded_tokens < cold_decoded_tokens);
    const auto wire = score_wire(first, valid, 3);
    check(wire.size() == 10 && wire[0] == 1 && wire[1] == 0 && wire[2] == 3 && wire[3] == 2);
    auto malformed = first; malformed.scores[1].scored_token_count = 0;
    check(score_wire(malformed, valid, 1) == failure_wire(15, 1));
    check(runtime_error(Error::InsufficientContext) == 15);
    for (const Request & request : std::vector<Request>{
        {"ab", {{1,"c"}}}, {"ab", {{1,"c"},{2,"c"}}}, {"ab", {{1,"c"},{2,"cd"}}}}) {
        const auto result = scorer.score(request);
        check(result.error == Error::ScoringFailed && result.scores.empty());
    }
    check(scorer.score({"", {{1,"a"},{2,"b"}}}).error == Error::InsufficientContext);
    check(scorer.score({std::string(193,'a'), {{1,"c"},{2,"d"}}}).error == Error::ContextTooLong);
    check(scorer.score({"a", {{1,std::string(65,'c')},{2,"d"}}}).error == Error::ContextTooLong);
    check(scorer.score({std::string(192,'a'), {{1,std::string(64,'c')},{2,std::string(64,'d')}}}).error == Error::None);
    model.vocab.bos = true;
    check(scorer.score({std::string(192,'a'), {{1,std::string(64,'c')},{2,std::string(64,'d')}}}).error == Error::ContextTooLong);
    check(scorer.score({std::string(191,'a'), {{1,std::string(64,'c')},{2,std::string(64,'d')}}}).error == Error::None);
    model.vocab.bos = false;
    fail_decode_call = decode_calls + 2;
    auto failed = scorer.score(valid);
    check(failed.error == Error::ScoringFailed && failed.scores.empty());
    fail_decode_call = 0;
    check(scorer.score(valid).error == Error::None);
    // Abort during the second candidate after a complete first score. Discard
    // every score and clean the context before the same scorer is reused.
    cancel_decode_call = decode_calls + 3;
    const auto before_cancel_clears = clears;
    auto decode_stopped = scorer.score(valid);
    check(decode_stopped.error == Error::Cancelled && decode_stopped.scores.empty());
    check(clears == before_cancel_clears + 1);
    cancelled = false; cancel_decode_call = 0;
    check(scorer.score(valid).error == Error::None);
    nonfinite_logits = true;
    const auto nonfinite = scorer.score(valid);
    check(nonfinite.error == Error::ScoringFailed && nonfinite.scores.empty());
    nonfinite_logits = false;
    check(scorer.score(valid).error == Error::None);
    cancel_tokenize_call = tokenize_calls + 2;
    auto stopped = scorer.score(valid);
    check(stopped.error == Error::Cancelled && stopped.scores.empty());
    cancelled = false; cancel_tokenize_call = 0;
    check(scorer.score(valid).error == Error::None);
    tokenizer_status = LLAMA_TOKENIZE_UNSUPPORTED;
    check(scorer.score(valid).error == Error::TokenizeFailed);
    tokenizer_status = LLAMA_TOKENIZE_INVALID_UTF8;
    check(scorer.score(valid).error == Error::InvalidUtf8);
    tokenizer_status = LLAMA_TOKENIZE_OK;
    auto invalid = valid; invalid.candidates[1].id = 7;
    check(scorer.score(invalid).error == Error::InvalidRequest);
    invalid = valid; invalid.prefix = std::string("\xc0\x80", 2);
    check(scorer.score(invalid).error == Error::InvalidUtf8);
    invalid = valid; invalid.candidates.resize(9);
    check(scorer.score(invalid).error == Error::TooManyCandidates);
    check(scorer.score(valid).scores.size() == 2);
    std::cout << "Native scoring contracts passed (deterministic model double)\n";
    return 0;
} catch (...) {
    std::cerr << "Native scoring contract failed\n";
    return 1;
}
