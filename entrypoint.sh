#!/bin/bash

MODEL_NAME="${MODEL_NAME:-ki-krugle-jp/llm-jp-4-8b-thinking}"

echo "=== KOTONOHA API starting ==="
echo "Model: ${MODEL_NAME}"
echo "Date: $(date)"

echo "Starting Ollama server..."
ollama serve 2>&1 &
OLLAMA_PID=$!

echo "Waiting for Ollama to be ready (PID: ${OLLAMA_PID})..."
MAX_WAIT=120
WAITED=0
until curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; do
    sleep 1
    WAITED=$((WAITED + 1))
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "ERROR: Ollama failed to start within ${MAX_WAIT} seconds"
        exit 1
    fi
    if [ $((WAITED % 10)) -eq 0 ]; then
        echo "Still waiting... (${WAITED}s)"
    fi
done
echo "Ollama is ready (waited ${WAITED}s)"

# Pull model if not present
echo "Checking model availability..."
ollama list
if ! ollama list 2>/dev/null | grep -q "llm-jp-4"; then
    echo "Model not found, pulling ${MODEL_NAME}..."
    ollama pull "${MODEL_NAME}" || {
        echo "ERROR: Failed to pull model"
        exit 1
    }
fi
echo "Model ready: ${MODEL_NAME}"

echo "Starting RunPod handler..."
exec python /handler.py
