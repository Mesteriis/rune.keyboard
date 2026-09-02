#include "scoring.h"
#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {
void require(bool condition) { if (!condition) throw std::runtime_error("test_failed"); }
}

int main() {
    using namespace rune::scoring;
    try {
        const float logits[]{10000, 10001, 9999};
        const double high = token_log_probability(logits, 3, 1);
        require(std::isfinite(high) && high < 0);
        require(high > token_log_probability(logits, 3, 0));
        require(std::abs(std::exp(high) + std::exp(token_log_probability(logits, 3, 0)) +
            std::exp(token_log_probability(logits, 3, 2)) - 1) < 1e-10);
        const float shifted[]{0, 1, -1};
        require(std::abs(high - token_log_probability(shifted, 3, 1)) < 1e-10);
        require(valid_utf8("причём corrección ñ 😀"));
        for (const auto & invalid : {std::string("\xc0\x80", 2), std::string("\xed\xa0\x80", 3),
            std::string("\xf4\x90\x80\x80", 4), std::string("\xe2\x82", 2), std::string("\x80", 1)})
            require(!valid_utf8(invalid));
        Request request{"hello", {{0, " there"}, {1, " there"}}};
        require(validate_request(request) == Error::None);
        request.candidates[1].id = 0;
        require(validate_request(request) == Error::InvalidRequest);
        request.candidates.clear();
        require(validate_request(request) == Error::InvalidRequest);
        for (int i = 0; i < 9; ++i) request.candidates.push_back({i, " word"});
        require(validate_request(request) == Error::TooManyCandidates);
        request.candidates.resize(1);
        request.prefix.assign(4097, 'a');
        require(validate_request(request) == Error::ContextTooLong);
        request.prefix = "";
        request.candidates[0].continuation = std::string("\xff", 1);
        require(validate_request(request) == Error::InvalidUtf8);
        std::atomic_bool cancelled{true};
        Scorer scorer(nullptr, cancelled);
        require(scorer.score({"hello", {{0, " word"}}}).error == Error::Cancelled);
        cancelled = false;
        require(scorer.score({"hello", {{0, " word"}}}).error == Error::ContextCreateFailed);
        std::cout << "scoring math/UTF-8/limits checks passed\n";
    } catch (...) { std::cerr << "scoring tests failed\n"; return 1; }
}
