FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

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
RUN ollama serve & sleep 5 && \
    ollama pull mmnga-o/llm-jp-4-8b-thinking-gguf:Q4_K_M && \
    kill %1 || true

ENV MODEL_NAME=mmnga-o/llm-jp-4-8b-thinking-gguf:Q4_K_M
ENV OLLAMA_HOST=127.0.0.1:11434

ENTRYPOINT ["/entrypoint.sh"]
