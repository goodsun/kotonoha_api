#!/bin/bash

MODEL_NAME="${MODEL_NAME:-kotonoha}"
VOLUME_PATH="${VOLUME_PATH:-/runpod-volume}"

echo "=== KOTONOHA starting ==="
echo "Model: ${MODEL_NAME}"
echo "Volume: ${VOLUME_PATH}"
echo "Date: $(date)"

# --- SSH setup ---
if [ -n "${PUBLIC_KEY:-}" ]; then
    echo "Setting up SSH..."
    mkdir -p /root/.ssh
    echo "$PUBLIC_KEY" > /root/.ssh/authorized_keys
    chmod 700 /root/.ssh
    chmod 600 /root/.ssh/authorized_keys
    /usr/sbin/sshd
    echo "SSH ready on port 22"
else
    echo "No PUBLIC_KEY provided, SSH disabled"
fi

# --- Ollama startup ---
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

# --- Model registration ---
echo "Checking model availability..."
if ! ollama list 2>/dev/null | grep -q "${MODEL_NAME}"; then
    if [ -f /Modelfile ]; then
        echo "Registering model from Modelfile..."
        ollama create "${MODEL_NAME}" -f /Modelfile || {
            echo "ERROR: Failed to create model"
            exit 1
        }
    else
        echo "ERROR: No Modelfile found"
        exit 1
    fi
fi
echo "Model ready: ${MODEL_NAME}"
ollama list

echo "=== KOTONOHA ready ==="
echo "Ollama API: http://0.0.0.0:11434"
echo "SSH: port 22"

# Keep container alive
wait $OLLAMA_PID
