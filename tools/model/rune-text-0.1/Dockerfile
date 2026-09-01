FROM python@sha256:09f7da3bc104798d0afb40bc08d23ab2da20a76130cec1f2ef170848f5d85217

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential=12.12 \
        ca-certificates=20250419 \
        cmake=3.31.6-2 \
        git=1:2.47.3-0+deb13u1 \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    certifi==2026.7.22 \
    charset-normalizer==3.5.1 \
    filelock==3.32.5 \
    fsspec==2026.7.0 \
    hf-xet==1.6.0 \
    huggingface-hub==0.36.2 \
    idna==3.19 \
    jinja2==3.1.6 \
    markupsafe==3.0.3 \
    mpmath==1.3.0 \
    networkx==3.6.1 \
    numpy==1.26.4 \
    packaging==26.3 \
    protobuf==4.25.8 \
    pyyaml==6.0.3 \
    regex==2026.9.3 \
    requests==2.34.2 \
    safetensors==0.8.0 \
    sentencepiece==0.2.0 \
    setuptools==81.0.0 \
    sympy==1.14.0 \
    tokenizers==0.22.2 \
    torch==2.11.0 \
    tqdm==4.70.0 \
    transformers==4.57.6 \
    typing-extensions==4.16.0 \
    urllib3==2.7.0

COPY build-one.sh /usr/local/bin/rune-build-one
ENTRYPOINT ["/usr/local/bin/rune-build-one"]
