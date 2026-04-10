FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends git curl zstd && \
    rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install handler dependencies
RUN pip install runpod requests

# Copy files
COPY handler.py /handler.py
COPY entrypoint.sh /entrypoint.sh
COPY Modelfile /Modelfile
RUN chmod +x /entrypoint.sh

# Pre-pull model at build time to bake into image
# LLM-jp-4 8B thinking (Q4_K_M, ~5.3GB)
RUN ollama serve & \
    for i in $(seq 1 30); do curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1 && break; sleep 1; done && \
    ollama pull mmnga-o/llm-jp-4-8b-thinking-gguf:Q4_K_M && \
    kill %1 || true

ENV MODEL_NAME=mmnga-o/llm-jp-4-8b-thinking-gguf:Q4_K_M
ENV OLLAMA_HOST=127.0.0.1:11434

ENTRYPOINT ["/entrypoint.sh"]
