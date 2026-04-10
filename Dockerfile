FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl zstd && \
    rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install handler dependencies
RUN pip install runpod requests

# Copy files
COPY handler.py /handler.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV MODEL_NAME=mmnga-o/llm-jp-4-8b-thinking-gguf:Q4_K_M
ENV OLLAMA_HOST=127.0.0.1:11434

ENTRYPOINT ["/entrypoint.sh"]
