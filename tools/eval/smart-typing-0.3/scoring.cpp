#include "scoring.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>

namespace rune::scoring {

const char * error_name(Error error) noexcept {
    switch (error) {
    case Error::None: return "OK";
    case Error::InvalidRequest: return "INVALID_REQUEST";
    case Error::InvalidUtf8: return "INVALID_UTF8";
    case Error::TooManyCandidates: return "TOO_MANY_CANDIDATES";
    case Error::ContextTooLong: return "CONTEXT_TOO_LONG";
    case Error::Cancelled: return "CANCELLED";
    case Error::TokenizeFailed: return "TOKENIZE_FAILED";
    case Error::ContextCreateFailed: return "CONTEXT_CREATE_FAILED";
    case Error::ScoringFailed: return "SCORING_FAILED";
    case Error::InsufficientContext: return "INSUFFICIENT_CONTEXT";
    }
    return "SCORING_FAILED";
}

bool valid_utf8(const std::string & text) noexcept {
    for (size_t i = 0; i < text.size();) {
        const auto first = static_cast<uint8_t>(text[i++]);
        if (first < 0x80) continue;
        unsigned remaining;
        uint32_t codepoint;
        uint32_t minimum;
        if (first >= 0xc2 && first <= 0xdf) { remaining = 1; codepoint = first & 31; minimum = 0x80; }
        else if (first >= 0xe0 && first <= 0xef) { remaining = 2; codepoint = first & 15; minimum = 0x800; }
        else if (first >= 0xf0 && first <= 0xf4) { remaining = 3; codepoint = first & 7; minimum = 0x10000; }
        else return false;
        if (text.size() - i < remaining) return false;
        while (remaining--) {
            const auto next = static_cast<uint8_t>(text[i++]);
            if ((next & 0xc0) != 0x80) return false;
            codepoint = (codepoint << 6) | (next & 63);
        }
        if (codepoint < minimum || codepoint > 0x10ffff || (codepoint >= 0xd800 && codepoint <= 0xdfff)) return false;
    }
    return true;
}

double token_log_probability(const float * logits, size_t count, size_t token) {
    if (!logits || !count || token >= count) throw std::invalid_argument("invalid_logits");
    double maximum = -INFINITY;
    for (size_t i = 0; i < count; ++i) {
        if (!std::isfinite(logits[i])) throw std::invalid_argument("non_finite_logits");
        maximum = std::max(maximum, static_cast<double>(logits[i]));
    }
    double sum = 0;
    for (size_t i = 0; i < count; ++i) sum += std::exp(static_cast<double>(logits[i]) - maximum);
    return static_cast<double>(logits[token]) - maximum - std::log(sum);
}

Error validate_request(const Request & request) noexcept {
    if (request.candidates.empty()) return Error::InvalidRequest;
    if (request.candidates.size() > 8) return Error::TooManyCandidates;
    if (request.prefix.size() > 4096) return Error::ContextTooLong;
    if (!valid_utf8(request.prefix)) return Error::InvalidUtf8;
    for (size_t i = 0; i < request.candidates.size(); ++i) {
        const auto & candidate = request.candidates[i];
        if (candidate.id < 0 || candidate.continuation.empty()) return Error::InvalidRequest;
        if (candidate.continuation.size() > 512) return Error::ContextTooLong;
        if (!valid_utf8(candidate.continuation)) return Error::InvalidUtf8;
        for (size_t j = 0; j < i; ++j) if (request.candidates[j].id == candidate.id) return Error::InvalidRequest;
    }
    return Error::None;
}

namespace {
bool abort_decode(void * data) { return static_cast<std::atomic_bool *>(data)->load(std::memory_order_relaxed); }
struct Batch {
    llama_batch value = llama_batch_init(64, 0, 1);
    ~Batch() { llama_batch_free(value); }
    Batch(const Batch &) = delete;
    Batch & operator=(const Batch &) = delete;
    Batch() = default;
};
struct ClearMemory {
    llama_context * context;
    ~ClearMemory() { llama_memory_clear(llama_get_memory(context), true); }
};
}

void Scorer::ContextDeleter::operator()(llama_context * context) const noexcept { llama_free(context); }
Scorer::~Scorer() = default;
Scorer::Scorer(llama_model * model, std::atomic_bool & cancelled)
    : vocab_(model ? llama_model_get_vocab(model) : nullptr), cancelled_(cancelled) {
    if (!model) return;
    auto params = llama_context_default_params();
    params.n_ctx = 256;
    params.n_batch = 64;
    // Reference evaluation uses one-token microbatches. On the pinned CPU
    // backend, wider microbatches did not match the scalar logit oracle.
    params.n_ubatch = 1;
    params.n_threads = params.n_threads_batch = 4;
    params.no_perf = true;
    params.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_DISABLED;
    params.abort_callback = abort_decode;
    params.abort_callback_data = &cancelled_;
    context_.reset(llama_init_from_model(model, params));
}

std::vector<llama_token> Scorer::tokenize(const std::string & text, size_t limit, bool bos) {
    if (cancelled_) throw Error::Cancelled;
    // PR1 uses upstream tokenizer. PR2 adds *internal* cancellation checkpoints;
    // do not misrepresent this bounded before/after cancellation as that gate.
    std::vector<llama_token> tokens(limit + 1);
    const auto count = llama_tokenize(vocab_, text.data(), static_cast<int32_t>(text.size()),
        tokens.data(), static_cast<int32_t>(tokens.size()), false, false);
    if (cancelled_) throw Error::Cancelled;
    if (count < 0 || static_cast<size_t>(count) > limit) throw Error::ContextTooLong;
    tokens.resize(static_cast<size_t>(count));
    // Respect only a model-configured BOS, never synthesize arbitrary context.
    if (bos && llama_vocab_get_add_bos(vocab_)) {
        const auto token = llama_vocab_bos(vocab_);
        if (token == LLAMA_TOKEN_NULL) throw Error::TokenizeFailed;
        tokens.insert(tokens.begin(), token);
        if (tokens.size() > limit) throw Error::ContextTooLong;
    }
    return tokens;
}

Result Scorer::score(const Request & request) {
    const auto invalid = validate_request(request);
    if (invalid != Error::None) return {invalid, {}};
    if (cancelled_) return {Error::Cancelled, {}};
    if (!context_) return {Error::ContextCreateFailed, {}};
    ClearMemory clear{context_.get()};
    try {
        tokenize(request.prefix, 192, false);
        std::vector<std::vector<llama_token>> alternatives;
        for (const auto & candidate : request.candidates) {
            tokenize(candidate.continuation, 64, false);
            alternatives.push_back(tokenize(request.prefix + candidate.continuation, 256, true));
        }
        size_t common = alternatives.front().size();
        for (const auto & tokens : alternatives) {
            common = std::min(common, tokens.size());
            size_t i = 0;
            while (i < common && tokens[i] == alternatives.front()[i]) ++i;
            common = i;
        }
        if (common == 0) return {Error::InsufficientContext, {}};
        const auto vocabulary_size = static_cast<size_t>(llama_vocab_n_tokens(vocab_));
        Batch batch;
        if (!batch.value.token || !batch.value.pos || !batch.value.n_seq_id ||
            !batch.value.seq_id || !batch.value.logits) return {Error::ScoringFailed, {}};
        Result result;
        for (size_t candidate_index = 0; candidate_index < alternatives.size(); ++candidate_index) {
            if (cancelled_) return {Error::Cancelled, {}};
            const auto & tokens = alternatives[candidate_index];
            Score score{request.candidates[candidate_index].id, 0, 0};
            llama_memory_clear(llama_get_memory(context_.get()), true);
            if (tokens.size() > common) {
                // Each logit row at position p scores token p+1. Only divergent
                // tokens contribute; prefix logits are neither read nor summed.
                for (size_t start = 0; start + 1 < tokens.size(); start += 64) {
                    const auto count = std::min<size_t>(64, tokens.size() - 1 - start);
                    batch.value.n_tokens = static_cast<int32_t>(count);
                    for (size_t i = 0; i < count; ++i) {
                        const auto position = start + i;
                        batch.value.token[i] = tokens[position];
                        batch.value.pos[i] = static_cast<llama_pos>(position);
                        batch.value.n_seq_id[i] = 1;
                        batch.value.seq_id[i][0] = 0;
                        batch.value.logits[i] = position + 1 >= common;
                    }
                    if (cancelled_) return {Error::Cancelled, {}};
                    if (llama_decode(context_.get(), batch.value) != 0)
                        return {cancelled_ ? Error::Cancelled : Error::ScoringFailed, {}};
                    for (size_t i = 0; i < count; ++i) {
                        if (cancelled_) return {Error::Cancelled, {}};
                        if (!batch.value.logits[i]) continue;
                        const auto next = tokens[start + i + 1];
                        score.sum_log_probability += token_log_probability(
                            llama_get_logits_ith(context_.get(), static_cast<int32_t>(i)),
                            vocabulary_size, static_cast<size_t>(next));
                        ++score.scored_token_count;
                    }
                }
            }
            result.scores.push_back(score);
        }
        if (cancelled_) return {Error::Cancelled, {}};
        return result;
    } catch (Error error) {
        return {error, {}};
    } catch (...) {
        return {Error::ScoringFailed, {}};
    }
}

} // namespace rune::scoring
