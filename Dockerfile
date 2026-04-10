FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl zstd && \
    rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install handler dependencies
RUN pip install runpod requests

# Download GGUF model from HuggingFace (~5.3GB)
RUN mkdir -p /models && \
    curl -L -o /models/llm-jp-4-8b-thinking-Q4_K_M.gguf \
    "https://huggingface.co/mmnga-o/llm-jp-4-8b-thinking-gguf/resolve/main/llm-jp-4-8b-thinking-Q4_K_M.gguf"

# Copy files
COPY handler.py /handler.py
COPY entrypoint.sh /entrypoint.sh
COPY Modelfile /Modelfile
RUN chmod +x /entrypoint.sh

# Register model with Ollama at build time
RUN ollama serve & \
    sleep 5 && \
    ollama create kotonoha -f /Modelfile && \
    kill %1 || true

ENV MODEL_NAME=kotonoha
ENV OLLAMA_HOST=127.0.0.1:11434

ENTRYPOINT ["/entrypoint.sh"]
