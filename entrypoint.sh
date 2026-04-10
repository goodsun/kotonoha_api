#!/bin/bash
set -e

MODEL_NAME="${MODEL_NAME:-mmnga-o/llm-jp-4-8b-thinking-gguf:Q4_K_M}"

echo "Starting Ollama server..."
ollama serve &

echo "Waiting for Ollama to be ready..."
MAX_WAIT=120
WAITED=0
until curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; do
    sleep 1
    WAITED=$((WAITED + 1))
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "ERROR: Ollama failed to start within ${MAX_WAIT} seconds"
        exit 1
    fi
done
echo "Ollama is ready (waited ${WAITED}s)"

# Ensure model is available (should be baked in, but pull if missing)
if ! ollama list | grep -q "${MODEL_NAME}"; then
    echo "Model not found, pulling ${MODEL_NAME}..."
    ollama pull "${MODEL_NAME}"
fi
echo "Model ready: ${MODEL_NAME}"

echo "Starting RunPod handler..."
exec python /handler.py
