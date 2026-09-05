#include <jni.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "llama.h"
#include "candidate_score_wire.h"

namespace {

enum class ErrorCode : int64_t {
    Ok = 0,
    ModelNotFound = 1,
    ModelLoadFailed = 2,
    NotLoaded = 3,
    ContextCreateFailed = 4,
    TokenizeFailed = 5,
    DecodeFailed = 6,
    EmptyOutput = 7,
    InvalidUtf8 = 8,
    Cancelled = 9,
    InternalError = 10,
    NativeLibraryUnavailable = 11,
    InvalidRequest = 12,
    ContextTooLong = 13,
    TooManyCandidates = 14,
    ScoringFailed = 15,
};

struct ModelDeleter {
    void operator()(llama_model * model) const noexcept { llama_model_free(model); }
};

struct ContextDeleter {
    void operator()(llama_context * context) const noexcept { llama_free(context); }
};

struct SamplerDeleter {
    void operator()(llama_sampler * sampler) const noexcept { llama_sampler_free(sampler); }
};

using ModelPtr = std::unique_ptr<llama_model, ModelDeleter>;
using ContextPtr = std::unique_ptr<llama_context, ContextDeleter>;
using SamplerPtr = std::unique_ptr<llama_sampler, SamplerDeleter>;

struct Runtime {
    std::atomic_bool cancelled{false};
    ModelPtr model;
    // Declared after the model so it is destroyed first. The scoring context is
    // reused until unload instead of being rebuilt for every word.
    std::unique_ptr<rune::scoring::Scorer> scorer;
};

std::once_flag backend_once;

void silent_log(ggml_log_level, const char *, void *) noexcept {}

void initialize_backend() {
    std::call_once(backend_once, [] {
        llama_log_set(silent_log, nullptr);
        llama_backend_init();
    });
}

bool continue_loading(float, void * data) {
    return !static_cast<Runtime *>(data)->cancelled.load(std::memory_order_relaxed);
}

bool abort_decode(void * data) {
    return static_cast<Runtime *>(data)->cancelled.load(std::memory_order_relaxed);
}

int64_t milliseconds_since(const std::chrono::steady_clock::time_point start) {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start).count();
}

bool valid_utf8(const std::string & text) {
    size_t index = 0;
    while (index < text.size()) {
        const auto first = static_cast<unsigned char>(text[index]);
        size_t remaining = 0;
        uint32_t codepoint = 0;
        if (first <= 0x7f) {
            index++;
            continue;
        } else if ((first & 0xe0) == 0xc0) {
            remaining = 1;
            codepoint = first & 0x1f;
            if (codepoint == 0) return false;
        } else if ((first & 0xf0) == 0xe0) {
            remaining = 2;
            codepoint = first & 0x0f;
        } else if ((first & 0xf8) == 0xf0) {
            remaining = 3;
            codepoint = first & 0x07;
        } else {
            return false;
        }
        if (index + remaining >= text.size()) return false;
        for (size_t offset = 1; offset <= remaining; ++offset) {
            const auto next = static_cast<unsigned char>(text[index + offset]);
            if ((next & 0xc0) != 0x80) return false;
            codepoint = (codepoint << 6) | (next & 0x3f);
        }
        if ((remaining == 1 && codepoint < 0x80) ||
            (remaining == 2 && codepoint < 0x800) ||
            (remaining == 3 && codepoint < 0x10000) ||
            (codepoint >= 0xd800 && codepoint <= 0xdfff) || codepoint > 0x10ffff) {
            return false;
        }
        index += remaining + 1;
    }
    return true;
}

jlongArray result(JNIEnv * env, ErrorCode code, int64_t first = 0, int64_t second = 0) {
    const jlong values[] = {static_cast<jlong>(code), first, second};
    jlongArray array = env->NewLongArray(3);
    if (array != nullptr) env->SetLongArrayRegion(array, 0, 3, values);
    return array;
}

// JNI references never outlive one call, including C++ exception paths.
struct UtfChars {
    JNIEnv * env;
    jstring value;
    const char * chars;
    ~UtfChars() { if (chars) env->ReleaseStringUTFChars(value, chars); }
};
struct LocalRef {
    JNIEnv * env;
    jobject value;
    ~LocalRef() { if (value) env->DeleteLocalRef(value); }
};

// Catch handlers must not allocate a C++ vector while reporting allocation failure.
jlongArray scoring_failure(JNIEnv * env, int64_t error) noexcept {
    if (env->ExceptionCheck()) return nullptr;
    const jlong values[] = {1, error, 0, 0};
    auto array = env->NewLongArray(4);
    if (array) env->SetLongArrayRegion(array, 0, 4, values);
    return array;
}

jlongArray scoring_result(JNIEnv * env, const std::vector<int64_t> & wire) {
    if (env->ExceptionCheck()) return nullptr;
    if (wire.size() > 28) return nullptr;
    jlong values[28];
    std::copy(wire.begin(), wire.end(), values);
    auto array = env->NewLongArray(static_cast<jsize>(wire.size()));
    if (array) env->SetLongArrayRegion(array, 0, static_cast<jsize>(wire.size()), values);
    return array;
}

std::string bounded_bytes(JNIEnv * env, jbyteArray array, jsize limit) {
    if (!array) throw rune::scoring::Error::InvalidRequest;
    const auto size = env->GetArrayLength(array);
    if (env->ExceptionCheck()) throw rune::scoring::Error::ScoringFailed;
    if (size > limit) throw rune::scoring::Error::ContextTooLong;
    std::string text(static_cast<size_t>(size), '\0');
    if (size) env->GetByteArrayRegion(array, 0, size, reinterpret_cast<jbyte *>(text.data()));
    if (env->ExceptionCheck()) throw rune::scoring::Error::ScoringFailed;
    return text;
}

rune::scoring::Request scoring_request(JNIEnv * env, jbyteArray prefix, jintArray ids,
                                     jobjectArray continuations) {
    if (!ids || !continuations) throw rune::scoring::Error::InvalidRequest;
    const auto count = env->GetArrayLength(ids);
    if (env->ExceptionCheck()) throw rune::scoring::Error::ScoringFailed;
    if (count > 8) throw rune::scoring::Error::TooManyCandidates;
    if (count < 1 || env->GetArrayLength(continuations) != count) throw rune::scoring::Error::InvalidRequest;
    if (env->ExceptionCheck()) throw rune::scoring::Error::ScoringFailed;
    jint identifiers[8];
    env->GetIntArrayRegion(ids, 0, count, identifiers);
    if (env->ExceptionCheck()) throw rune::scoring::Error::ScoringFailed;
    rune::scoring::Request request{bounded_bytes(env, prefix, 4096), {}};
    request.candidates.reserve(static_cast<size_t>(count));
    for (jsize i = 0; i < count; ++i) {
        LocalRef item{env, env->GetObjectArrayElement(continuations, i)};
        if (env->ExceptionCheck()) throw rune::scoring::Error::ScoringFailed;
        request.candidates.push_back({identifiers[i], bounded_bytes(env, static_cast<jbyteArray>(item.value), 512)});
    }
    const auto error = rune::scoring::validate_request(request);
    if (error != rune::scoring::Error::None) throw error;
    return request;
}

Runtime * from_handle(jlong handle) {
    return reinterpret_cast<Runtime *>(static_cast<intptr_t>(handle));
}

jlong native_create(JNIEnv *, jobject) {
    try {
        initialize_backend();
        return static_cast<jlong>(reinterpret_cast<intptr_t>(new Runtime()));
    } catch (...) {
        return 0;
    }
}

void native_destroy(JNIEnv *, jobject, jlong handle) try {
    delete from_handle(handle);
} catch (...) {  }

jlongArray native_load(JNIEnv * env, jobject, jlong handle, jstring path) try {
    Runtime * runtime = from_handle(handle);
    if (runtime == nullptr || path == nullptr) return result(env, ErrorCode::InternalError);
    UtfChars raw_path{env, path, env->GetStringUTFChars(path, nullptr)};
    if (!raw_path.chars) return nullptr;
    std::string local_path(raw_path.chars);
    runtime->scorer.reset();
    runtime->model.reset();
    if (runtime->cancelled.load(std::memory_order_relaxed)) return result(env, ErrorCode::Cancelled);
    llama_model_params params = llama_model_default_params();
    params.n_gpu_layers = 0;
    params.progress_callback = continue_loading;
    params.progress_callback_user_data = runtime;
    const auto start = std::chrono::steady_clock::now();
    try {
        runtime->model.reset(llama_model_load_from_file(local_path.c_str(), params));
    } catch (...) {
        runtime->model.reset();
        return result(env, ErrorCode::InternalError);
    }
    if (runtime->cancelled.load(std::memory_order_relaxed)) {
        runtime->model.reset();
        return result(env, ErrorCode::Cancelled);
    }
    if (!runtime->model) return result(env, ErrorCode::ModelLoadFailed);
    try {
        runtime->scorer = std::make_unique<rune::scoring::Scorer>(runtime->model.get(), runtime->cancelled);
    } catch (...) {
        runtime->model.reset();
        return result(env, ErrorCode::InternalError);
    }
    return result(env, ErrorCode::Ok, milliseconds_since(start));
} catch (...) { return result(env, ErrorCode::InternalError); }

jlongArray native_self_test(JNIEnv * env, jobject, jlong handle) try {
    Runtime * runtime = from_handle(handle);
    if (runtime == nullptr) return result(env, ErrorCode::InternalError);
    if (!runtime->model) return result(env, ErrorCode::NotLoaded);
    if (runtime->cancelled.load(std::memory_order_relaxed)) return result(env, ErrorCode::Cancelled);

    llama_context_params params = llama_context_default_params();
    params.n_ctx = 256;
    params.n_batch = 64;
    params.n_ubatch = 64;
    params.n_threads = static_cast<int32_t>(std::max(1u, std::min(4u, std::thread::hardware_concurrency())));
    params.n_threads_batch = params.n_threads;
    params.no_perf = true;
    params.abort_callback = abort_decode;
    params.abort_callback_data = runtime;
    ContextPtr context(llama_init_from_model(runtime->model.get(), params));
    if (!context) return result(env, ErrorCode::ContextCreateFailed);
    llama_set_abort_callback(context.get(), abort_decode, runtime);

    constexpr char prompt[] = "Rune local runtime self test.";
    const llama_vocab * vocab = llama_model_get_vocab(runtime->model.get());
    int32_t token_count = -llama_tokenize(vocab, prompt, sizeof(prompt) - 1, nullptr, 0, true, true);
    if (token_count <= 0 || token_count > 64) return result(env, ErrorCode::TokenizeFailed);
    std::vector<llama_token> tokens(static_cast<size_t>(token_count));
    if (llama_tokenize(vocab, prompt, sizeof(prompt) - 1, tokens.data(), token_count, true, true) != token_count) {
        return result(env, ErrorCode::TokenizeFailed);
    }

    llama_token warmup_token = tokens.front();
    if (llama_decode(context.get(), llama_batch_get_one(&warmup_token, 1)) != 0) {
        return result(env, runtime->cancelled ? ErrorCode::Cancelled : ErrorCode::DecodeFailed);
    }
    llama_synchronize(context.get());
    llama_memory_clear(llama_get_memory(context.get()), true);

    const auto prompt_start = std::chrono::steady_clock::now();
    if (llama_decode(context.get(), llama_batch_get_one(tokens.data(), token_count)) != 0) {
        return result(env, runtime->cancelled ? ErrorCode::Cancelled : ErrorCode::DecodeFailed);
    }
    const int64_t prompt_millis = milliseconds_since(prompt_start);
    SamplerPtr sampler(llama_sampler_init_greedy());
    if (!sampler) return result(env, ErrorCode::InternalError);
    std::string output;
    int64_t first_token_millis = 0;
    for (int generated = 0; generated < 4; ++generated) {
        if (runtime->cancelled.load(std::memory_order_relaxed)) return result(env, ErrorCode::Cancelled);
        const llama_token token = llama_sampler_sample(sampler.get(), context.get(), -1);
        if (generated == 0) first_token_millis = milliseconds_since(prompt_start);
        if (llama_vocab_is_eog(vocab, token)) break;
        char piece[256];
        const int32_t piece_size = llama_token_to_piece(vocab, token, piece, sizeof(piece), 0, true);
        if (piece_size < 0 || piece_size > static_cast<int32_t>(sizeof(piece))) {
            return result(env, ErrorCode::InvalidUtf8);
        }
        output.append(piece, static_cast<size_t>(piece_size));
        llama_token next = token;
        if (llama_decode(context.get(), llama_batch_get_one(&next, 1)) != 0) {
            return result(env, runtime->cancelled ? ErrorCode::Cancelled : ErrorCode::DecodeFailed);
        }
    }
    if (output.empty()) return result(env, ErrorCode::EmptyOutput);
    if (!valid_utf8(output)) return result(env, ErrorCode::InvalidUtf8);
    return result(env, ErrorCode::Ok, prompt_millis, first_token_millis);
} catch (...) { return result(env, ErrorCode::InternalError); }

// Admission and model lifetime stay owned by NativeHandleLifecycle's serial
// executor. Cancellation runs directly on its monitor and never waits on score.
jlongArray native_score_candidates(JNIEnv * env, jobject, jlong handle, jbyteArray prefix,
                                   jintArray ids, jobjectArray continuations) try {
    Runtime * runtime = from_handle(handle);
    if (!runtime) return scoring_result(env, rune::scoring::failure_wire(10));
    auto request = scoring_request(env, prefix, ids, continuations);
    if (runtime->cancelled.load(std::memory_order_relaxed))
        return scoring_result(env, rune::scoring::failure_wire(9));
    if (!runtime->model || !runtime->scorer) return scoring_result(env, rune::scoring::failure_wire(3));
    const auto start = std::chrono::steady_clock::now();
    const auto score = runtime->scorer->score(request);
    if (runtime->cancelled.load(std::memory_order_relaxed))
        return scoring_result(env, rune::scoring::failure_wire(9, milliseconds_since(start)));
    return scoring_result(env, rune::scoring::score_wire(score, request, milliseconds_since(start)));
} catch (rune::scoring::Error error) {
    return scoring_failure(env, rune::scoring::runtime_error(error));
} catch (...) {
    return scoring_failure(env, 15);
}

void native_cancel(JNIEnv *, jobject, jlong handle) try {
    if (Runtime * runtime = from_handle(handle)) runtime->cancelled.store(true, std::memory_order_relaxed);
} catch (...) {  }

void native_reset_cancellation(JNIEnv *, jobject, jlong handle) try {
    if (Runtime * runtime = from_handle(handle)) runtime->cancelled.store(false, std::memory_order_relaxed);
} catch (...) {  }

void native_unload(JNIEnv *, jobject, jlong handle) try {
    if (Runtime * runtime = from_handle(handle)) {
        runtime->cancelled.store(true, std::memory_order_relaxed);
        runtime->scorer.reset();
        runtime->model.reset();
    }
} catch (...) {  }

JNINativeMethod methods[] = {
    {const_cast<char *>("nativeCreate"), const_cast<char *>("()J"), reinterpret_cast<void *>(native_create)},
    {const_cast<char *>("nativeDestroy"), const_cast<char *>("(J)V"), reinterpret_cast<void *>(native_destroy)},
    {const_cast<char *>("nativeLoad"), const_cast<char *>("(JLjava/lang/String;)[J"), reinterpret_cast<void *>(native_load)},
    {const_cast<char *>("nativeScoreCandidates"), const_cast<char *>("(J[B[I[[B)[J"), reinterpret_cast<void *>(native_score_candidates)},
    {const_cast<char *>("nativeSelfTest"), const_cast<char *>("(J)[J"), reinterpret_cast<void *>(native_self_test)},
    {const_cast<char *>("nativeResetCancellation"), const_cast<char *>("(J)V"), reinterpret_cast<void *>(native_reset_cancellation)},
    {const_cast<char *>("nativeCancel"), const_cast<char *>("(J)V"), reinterpret_cast<void *>(native_cancel)},
    {const_cast<char *>("nativeUnload"), const_cast<char *>("(J)V"), reinterpret_cast<void *>(native_unload)},
};

}  // namespace

JNIEXPORT jint JNI_OnLoad(JavaVM * vm, void *) try {
    JNIEnv * env = nullptr;
    if (vm->GetEnv(reinterpret_cast<void **>(&env), JNI_VERSION_1_6) != JNI_OK) return JNI_ERR;
    jclass runtime_class = env->FindClass("io/github/mesteriis/rune/runtime/llama/LlamaLocalModelRuntime");
    if (runtime_class == nullptr) return JNI_ERR;
    LocalRef runtime_ref{env, runtime_class};
    if (env->RegisterNatives(runtime_class, methods, sizeof(methods) / sizeof(methods[0])) != JNI_OK) return JNI_ERR;
    return JNI_VERSION_1_6;
} catch (...) { return JNI_ERR; }
