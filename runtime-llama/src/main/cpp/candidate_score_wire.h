#pragma once

#include "scoring.h"

#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

namespace rune::scoring {

// Appended runtime codes; existing 0..11 keep their published meanings.
inline int64_t runtime_error(Error error) noexcept {
    switch (error) {
    case Error::None: return 0;
    case Error::InvalidRequest: return 12;
    case Error::InvalidUtf8: return 8;
    case Error::TooManyCandidates: return 14;
    case Error::ContextTooLong: return 13;
    case Error::Cancelled: return 9;
    case Error::TokenizeFailed: return 5;
    case Error::ContextCreateFailed: return 4;
    case Error::ScoringFailed:
    case Error::InsufficientContext: return 15;
    }
    return 15;
}

inline std::vector<int64_t> failure_wire(int64_t error, int64_t duration = 0) {
    return {1, error, duration, 0};
}

inline std::vector<int64_t> score_wire(const Result & result, const Request & request, int64_t duration) {
    if (result.error != Error::None) return failure_wire(runtime_error(result.error), duration);
    if (duration < 0 || request.candidates.empty() || request.candidates.size() > 8 ||
        result.scores.size() != request.candidates.size()) return failure_wire(15);
    std::vector<int64_t> wire{1, 0, duration, static_cast<int64_t>(result.scores.size())};
    wire.reserve(28);
    for (size_t i = 0; i < result.scores.size(); ++i) {
        const auto & score = result.scores[i];
        if (score.id != request.candidates[i].id || !std::isfinite(score.sum_log_probability) ||
            score.sum_log_probability > 0 || score.scored_token_count < 1 || score.scored_token_count > 255) {
            return failure_wire(15, duration);
        }
        int64_t bits;
        static_assert(sizeof(bits) == sizeof(score.sum_log_probability));
        std::memcpy(&bits, &score.sum_log_probability, sizeof(bits));
        wire.insert(wire.end(), {score.id, bits, score.scored_token_count});
    }
    return wire;
}

} // namespace rune::scoring
