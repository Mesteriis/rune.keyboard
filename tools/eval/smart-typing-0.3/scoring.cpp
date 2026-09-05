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
#if defined(RUNE_TOKENIZER_ABORT)
struct TokenizeCancellation { std::atomic_bool & cancelled; };
bool abort_tokenize(llama_tokenize_stage, void * data) noexcept {
    return static_cast<TokenizeCancellation *>(data)->cancelled.load(std::memory_order_relaxed);
}
#endif
struct Batch {
    llama_batch value = llama_batch_init(64, 0, 1);
    ~Batch() { llama_batch_free(value); }
    Batch(const Batch &) = delete;
    Batch & operator=(const Batch &) = delete;
    Batch() = default;
};
struct MemoryRetention {
    llama_context * context;
    std::vector<llama_token> & cached;
    bool keep = false;
    ~MemoryRetention() {
        if (!keep) {
            llama_memory_clear(llama_get_memory(context), true);
            cached.clear();
        }
    }
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
    // Scalar microbatches preserve the calibrated token-at-a-time score contract.
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
    std::vector<llama_token> tokens(limit + 1);
#if defined(RUNE_TOKENIZER_ABORT)
    // The additive API checks BPE/QWEN2/gpt2 metadata and whitespace policy.
    // The adapter and callback userdata are local to this tokenization call.
    TokenizeCancellation cancellation{cancelled_};
    int32_t count = 0;
    const auto status = llama_tokenize_with_abort(vocab_, text.data(), static_cast<int32_t>(text.size()),
        tokens.data(), static_cast<int32_t>(tokens.size()), false, false,
        abort_tokenize, &cancellation, &count);
    switch (status) {
    case LLAMA_TOKENIZE_OK: break;
    case LLAMA_TOKENIZE_CANCELLED: throw Error::Cancelled;
    case LLAMA_TOKENIZE_INVALID_UTF8: throw Error::InvalidUtf8;
    case LLAMA_TOKENIZE_BUFFER_TOO_SMALL:
    case LLAMA_TOKENIZE_OVERFLOW: throw Error::ContextTooLong;
    case LLAMA_TOKENIZE_INVALID_ARGUMENT: throw Error::InvalidRequest;
    case LLAMA_TOKENIZE_UNSUPPORTED:
    case LLAMA_TOKENIZE_FAILED: throw Error::TokenizeFailed;
    default: throw Error::TokenizeFailed;
    }
#else
    // The evaluator can still build against the pristine pinned upstream API.
    const auto count = llama_tokenize(vocab_, text.data(), static_cast<int32_t>(text.size()),
        tokens.data(), static_cast<int32_t>(tokens.size()), false, false);
#endif
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
    MemoryRetention memory{context_.get(), cached_common_tokens_};
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
        // Equal token sequences, one candidate, or one sequence ending at the
        // LCP cannot form a complete comparable set. Never rank a zero span.
        if (std::any_of(alternatives.begin(), alternatives.end(), [common](const auto & tokens) {
            return tokens.size() <= common;
        })) return {Error::ScoringFailed, {}};
        const auto vocabulary_size = static_cast<size_t>(llama_vocab_n_tokens(vocab_));
        Batch batch;
        if (!batch.value.token || !batch.value.pos || !batch.value.n_seq_id ||
            !batch.value.seq_id || !batch.value.logits) return {Error::ScoringFailed, {}};
        // Reuse the common token prefix retained by the preceding successful
        // request. Always replay its final token so current logits are available;
        // extensions and Backspace rewinds only decode the changed suffix.
        const auto & reference = alternatives.front();
        size_t matched = 0;
        while (matched < cached_common_tokens_.size() && matched < common &&
            cached_common_tokens_[matched] == reference[matched]) ++matched;
        size_t reusable = std::min(matched, common - 1);
        if (reusable < cached_common_tokens_.size()) {
            if (!llama_memory_seq_rm(llama_get_memory(context_.get()), 0,
                    static_cast<llama_pos>(reusable), -1)) {
                llama_memory_clear(llama_get_memory(context_.get()), true);
                reusable = 0;
            }
            cached_common_tokens_.resize(reusable);
        }

        // Decode the remaining longest common token prefix once. The final common token's
        // logits score each candidate's first divergent token; subsequent work
        // starts at the divergent span and is removed before the next candidate.
        const float * common_logits = nullptr;
        for (size_t start = reusable; start < common; start += 64) {
            const auto count = std::min<size_t>(64, common - start);
            batch.value.n_tokens = static_cast<int32_t>(count);
            for (size_t i = 0; i < count; ++i) {
                const auto position = start + i;
                batch.value.token[i] = reference[position];
                batch.value.pos[i] = static_cast<llama_pos>(position);
                batch.value.n_seq_id[i] = 1;
                batch.value.seq_id[i][0] = 0;
                batch.value.logits[i] = position + 1 == common;
            }
            if (cancelled_) return {Error::Cancelled, {}};
            if (llama_decode(context_.get(), batch.value) != 0)
                return {cancelled_ ? Error::Cancelled : Error::ScoringFailed, {}};
            if (start + count == common) {
                common_logits = llama_get_logits_ith(context_.get(), static_cast<int32_t>(count - 1));
            }
        }
        if (!common_logits) return {Error::ScoringFailed, {}};
        std::vector<double> first_log_probabilities;
        first_log_probabilities.reserve(alternatives.size());
        for (const auto & tokens : alternatives) {
            first_log_probabilities.push_back(token_log_probability(
                common_logits, vocabulary_size, static_cast<size_t>(tokens[common])));
        }

        Result result;
        for (size_t candidate_index = 0; candidate_index < alternatives.size(); ++candidate_index) {
            if (cancelled_) return {Error::Cancelled, {}};
            const auto & tokens = alternatives[candidate_index];
            Score score{request.candidates[candidate_index].id,
                first_log_probabilities[candidate_index], 1};
            // Each row at position p scores token p+1. Token `common` was scored
            // from the shared row, so only positions common..size-2 remain.
            for (size_t start = common; start + 1 < tokens.size(); start += 64) {
                const auto count = std::min<size_t>(64, tokens.size() - 1 - start);
                batch.value.n_tokens = static_cast<int32_t>(count);
                for (size_t i = 0; i < count; ++i) {
                    const auto position = start + i;
                    batch.value.token[i] = tokens[position];
                    batch.value.pos[i] = static_cast<llama_pos>(position);
                    batch.value.n_seq_id[i] = 1;
                    batch.value.seq_id[i][0] = 0;
                    batch.value.logits[i] = true;
                }
                if (cancelled_) return {Error::Cancelled, {}};
                if (llama_decode(context_.get(), batch.value) != 0)
                    return {cancelled_ ? Error::Cancelled : Error::ScoringFailed, {}};
                for (size_t i = 0; i < count; ++i) {
                    if (cancelled_) return {Error::Cancelled, {}};
                    score.sum_log_probability += token_log_probability(
                        llama_get_logits_ith(context_.get(), static_cast<int32_t>(i)), vocabulary_size,
                        static_cast<size_t>(tokens[start + i + 1]));
                    ++score.scored_token_count;
                }
            }
            result.scores.push_back(score);
            if (!llama_memory_seq_rm(llama_get_memory(context_.get()), 0,
                    static_cast<llama_pos>(common), -1)) return {Error::ScoringFailed, {}};
        }
        if (cancelled_) return {Error::Cancelled, {}};
        cached_common_tokens_.assign(reference.begin(), reference.begin() + static_cast<std::ptrdiff_t>(common));
        memory.keep = true;
        return result;
    } catch (Error error) {
        return {error, {}};
    } catch (...) {
        return {Error::ScoringFailed, {}};
    }
}

} // namespace rune::scoring
