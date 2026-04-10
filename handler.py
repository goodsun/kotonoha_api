"""
RunPod Serverless Handler for KOTONOHA (LLM-jp-4)
Text chat -> LLM response (streaming or full)
"""

import runpod
import requests
import os
import sys
import json
import time
import traceback
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
OLLAMA_URL = f"http://{OLLAMA_BASE}"
MODEL_NAME = os.environ.get("MODEL_NAME", "kotonoha")


def wait_for_ollama():
    """Wait for Ollama HTTP server to be ready."""
    url = f"{OLLAMA_URL}/api/tags"
    for attempt in range(180):
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                logger.info(f"Ollama ready after {attempt + 1} attempts")
                return True
        except Exception:
            pass
        if (attempt + 1) % 30 == 0:
            logger.info(f"Waiting for Ollama... ({attempt + 1}/180)")
        time.sleep(1)
    raise RuntimeError("Ollama failed to start within 180 seconds")


AUTHORIZED_KEYS_PATH = "/root/.ssh/authorized_keys"


def handle_ssh(input_data):
    """Handle SSH public key management."""
    action = input_data.get("ssh_action", "")

    if action == "set_pubkey":
        pubkey = input_data.get("pubkey", "").strip()
        if not pubkey:
            return {"error": "pubkey is required"}
        if not pubkey.startswith(("ssh-rsa", "ssh-ed25519", "ecdsa-sha2", "ssh-dss")):
            return {"error": "Invalid public key format"}

        os.makedirs("/root/.ssh", exist_ok=True)

        # Append if not already present
        existing = ""
        if os.path.exists(AUTHORIZED_KEYS_PATH):
            with open(AUTHORIZED_KEYS_PATH, "r") as f:
                existing = f.read()

        if pubkey in existing:
            return {"status": "already_registered", "message": "Public key is already registered"}

        with open(AUTHORIZED_KEYS_PATH, "a") as f:
            f.write(pubkey + "\n")
        os.chmod(AUTHORIZED_KEYS_PATH, 0o600)

        logger.info("SSH public key added")
        return {"status": "ok", "message": "Public key registered"}

    elif action == "list_pubkeys":
        if not os.path.exists(AUTHORIZED_KEYS_PATH):
            return {"keys": []}
        with open(AUTHORIZED_KEYS_PATH, "r") as f:
            keys = [line.strip() for line in f if line.strip()]
        return {"keys": keys}

    elif action == "remove_pubkey":
        pubkey = input_data.get("pubkey", "").strip()
        if not pubkey:
            return {"error": "pubkey is required"}
        if not os.path.exists(AUTHORIZED_KEYS_PATH):
            return {"error": "No keys registered"}

        with open(AUTHORIZED_KEYS_PATH, "r") as f:
            keys = [line.strip() for line in f if line.strip()]

        new_keys = [k for k in keys if k != pubkey]
        if len(new_keys) == len(keys):
            return {"error": "Key not found"}

        with open(AUTHORIZED_KEYS_PATH, "w") as f:
            f.write("\n".join(new_keys) + "\n" if new_keys else "")
        os.chmod(AUTHORIZED_KEYS_PATH, 0o600)

        logger.info("SSH public key removed")
        return {"status": "ok", "message": "Public key removed"}

    else:
        return {"error": f"Unknown ssh_action: {action}. Use: set_pubkey, list_pubkeys, remove_pubkey"}


def handler(job):
    """RunPod serverless handler."""
    job_id = job.get("id", "unknown")
    input_data = job.get("input", {})

    logger.info(f"Job started: {job_id}")

    try:
        # SSH management
        if "ssh_action" in input_data:
            return handle_ssh(input_data)

        # Chat completion
        messages = input_data.get("messages")
        prompt = input_data.get("prompt")

        if not messages and not prompt:
            return {"error": "Either 'messages' (array) or 'prompt' (string) is required"}

        # Build messages array
        if messages:
            if not isinstance(messages, list):
                return {"error": "'messages' must be an array of {role, content} objects"}
            for i, msg in enumerate(messages):
                if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                    return {"error": f"messages[{i}] must have 'role' and 'content' fields"}
        else:
            # Simple prompt mode: wrap in user message
            system_prompt = input_data.get("system", "")
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        # Parameters
        model = input_data.get("model", MODEL_NAME)
        temperature = input_data.get("temperature", 0.7)
        top_p = input_data.get("top_p", 0.9)
        max_tokens = input_data.get("max_tokens", 2048)
        stream = input_data.get("stream", False)

        # Validate
        try:
            temperature = float(temperature)
            top_p = float(top_p)
            max_tokens = int(max_tokens)
        except (TypeError, ValueError) as e:
            return {"error": f"Invalid parameter type: {e}"}

        if not (0.0 <= temperature <= 2.0):
            return {"error": f"temperature must be between 0.0 and 2.0, got: {temperature}"}
        if not (0.0 <= top_p <= 1.0):
            return {"error": f"top_p must be between 0.0 and 1.0, got: {top_p}"}
        if not (1 <= max_tokens <= 65536):
            return {"error": f"max_tokens must be between 1 and 65536, got: {max_tokens}"}

        logger.info(f"Chat: {len(messages)} messages, model={model}, temp={temperature}")

        wait_for_ollama()

        # Call Ollama /api/chat
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_tokens,
            },
        }

        if stream:
            # Streaming mode: collect chunks and return full response
            # (RunPod serverless doesn't support true streaming,
            #  but we stream from Ollama to avoid timeout)
            resp = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json=payload,
                stream=True,
                timeout=300,
            )
            resp.raise_for_status()

            full_content = []
            model_name = model
            total_tokens = 0

            for line in resp.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if "error" in chunk:
                    return {"error": chunk["error"]}
                msg = chunk.get("message", {})
                content = msg.get("content", "")
                if content:
                    full_content.append(content)
                if chunk.get("done", False):
                    model_name = chunk.get("model", model)
                    total_tokens = chunk.get("eval_count", 0)
                    prompt_tokens = chunk.get("prompt_eval_count", 0)

            response_text = "".join(full_content)

            logger.info(f"Job completed: {job_id} ({total_tokens} tokens)")
            return {
                "response": response_text,
                "model": model_name,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": total_tokens,
                    "total_tokens": prompt_tokens + total_tokens,
                },
            }
        else:
            # Non-streaming mode
            resp = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json=payload,
                timeout=300,
            )
            resp.raise_for_status()
            result = resp.json()

            if "error" in result:
                return {"error": result["error"]}

            response_text = result.get("message", {}).get("content", "")
            eval_count = result.get("eval_count", 0)
            prompt_eval_count = result.get("prompt_eval_count", 0)

            logger.info(f"Job completed: {job_id} ({eval_count} tokens)")
            return {
                "response": response_text,
                "model": result.get("model", model),
                "usage": {
                    "prompt_tokens": prompt_eval_count,
                    "completion_tokens": eval_count,
                    "total_tokens": prompt_eval_count + eval_count,
                },
            }

    except requests.exceptions.Timeout:
        logger.error(f"Job timed out: {job_id}")
        return {"error": "Request timed out (300s limit)"}
    except Exception as e:
        logger.error(f"Job failed: {job_id} - {e}")
        traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
