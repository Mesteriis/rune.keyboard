#pragma once

#include "llama.h"
#include <atomic>
#include <cstddef>
#include <memory>
#include <string>
#include <vector>

namespace rune::scoring {

enum class Error {
    None, InvalidRequest, InvalidUtf8, TooManyCandidates, ContextTooLong,
    Cancelled, TokenizeFailed, ContextCreateFailed, ScoringFailed, InsufficientContext,
};
const char * error_name(Error error) noexcept;
bool valid_utf8(const std::string & text) noexcept;
double token_log_probability(const float * logits, size_t count, size_t token);

struct Candidate { int id; std::string continuation; };
struct Request { std::string prefix; std::vector<Candidate> candidates; };
struct Score { int id; double sum_log_probability; int scored_token_count; };
struct Result { Error error = Error::None; std::vector<Score> scores; };

Error validate_request(const Request & request) noexcept;

// Non-owning model; its owner must outlive the scorer. A bounded common token
// prefix and KV remain in this object between serialized calls; failures clear both.
class Scorer {
public:
    Scorer(llama_model * model, std::atomic_bool & cancelled);
    ~Scorer();
    Scorer(const Scorer &) = delete;
    Scorer & operator=(const Scorer &) = delete;
    Result score(const Request & request);
private:
    struct ContextDeleter { void operator()(llama_context * context) const noexcept; };
    const llama_vocab * vocab_;
    std::atomic_bool & cancelled_;
    std::unique_ptr<llama_context, ContextDeleter> context_;
    std::vector<llama_token> cached_common_tokens_;
    std::vector<llama_token> tokenize(const std::string & text, size_t limit, bool bos);
};

} // namespace rune::scoring
