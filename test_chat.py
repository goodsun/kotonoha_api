#!/usr/bin/env python3
"""
KOTONOHA テストクライアント
RunPod Pods APIでPodを起動し、Ollama APIに直接アクセスしてチャットする。
終了時にPodをterminateする。
依存ライブラリなし（標準ライブラリのみ）
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path


def load_env(path=".env"):
    if Path(path).exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


def api_request(url, headers, data=None, method=None, timeout=60):
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=headers, method=method or "POST")
    else:
        req = urllib.request.Request(url, headers=headers, method=method or "GET")
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode("utf-8"))


def runpod_request(path, api_key, data=None, method=None, timeout=60):
    url = f"https://api.runpod.io/graphql"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    return api_request(url, headers, data, method, timeout)


def create_pod(api_key, gpu_type, volume_id, public_key, image_name):
    """Create a pod via RunPod GraphQL API."""
    query = """
    mutation {{
        podFindAndDeployOnDemand(input: {{
            name: "kotonoha-session"
            imageName: "{image}"
            gpuTypeId: "{gpu}"
            volumeId: "{volume}"
            containerDiskInGb: 20
            volumeMountPath: "/runpod-volume"
            ports: "22/tcp,11434/http"
            env: [
                {{ key: "PUBLIC_KEY", value: "{pubkey}" }},
                {{ key: "MODEL_NAME", value: "kotonoha" }},
                {{ key: "OLLAMA_HOST", value: "0.0.0.0:11434" }}
            ]
        }}) {{
            id
            desiredStatus
            imageName
            runtime {{
                ports {{
                    ip
                    isIpPublic
                    privatePort
                    publicPort
                }}
            }}
        }}
    }}
    """.format(
        image=image_name,
        gpu=gpu_type,
        volume=volume_id,
        pubkey=public_key.replace('"', '\\"'),
    )
    return runpod_request("", api_key, {"query": query})


def get_pod(api_key, pod_id):
    """Get pod status."""
    query = """
    query {{
        pod(input: {{ podId: "{pod_id}" }}) {{
            id
            desiredStatus
            runtime {{
                uptimeInSeconds
                ports {{
                    ip
                    isIpPublic
                    privatePort
                    publicPort
                }}
            }}
        }}
    }}
    """.format(pod_id=pod_id)
    return runpod_request("", api_key, {"query": query})


def terminate_pod(api_key, pod_id):
    """Terminate (delete) a pod."""
    query = """
    mutation {{
        podTerminate(input: {{ podId: "{pod_id}" }})
    }}
    """.format(pod_id=pod_id)
    return runpod_request("", api_key, {"query": query})


def wait_for_pod(api_key, pod_id, max_wait=300):
    """Wait for pod to be running and Ollama to be ready."""
    print("Pod起動中...")
    waited = 0
    ollama_url = None

    while waited < max_wait:
        try:
            result = get_pod(api_key, pod_id)
            pod = result.get("data", {}).get("pod", {})
            runtime = pod.get("runtime")

            if runtime and runtime.get("ports"):
                ports = runtime["ports"]
                for p in ports:
                    if p.get("privatePort") == 11434 and p.get("isIpPublic"):
                        ollama_url = f"http://{p['ip']}:{p['publicPort']}"
                    if p.get("privatePort") == 22 and p.get("isIpPublic"):
                        ssh_info = f"{p['ip']}:{p['publicPort']}"

                if ollama_url:
                    # Check if Ollama is actually ready
                    try:
                        req = urllib.request.Request(f"{ollama_url}/api/tags")
                        urllib.request.urlopen(req, timeout=5)
                        print(f"\rPod起動完了 ({waited}s)")
                        return ollama_url, ssh_info if 'ssh_info' in dir() else None
                    except Exception:
                        pass
        except Exception:
            pass

        sys.stdout.write(f"\r起動中... ({waited}s)")
        sys.stdout.flush()
        time.sleep(5)
        waited += 5

    raise TimeoutError(f"Pod起動タイムアウト ({max_wait}s)")


def ollama_chat(ollama_url, messages, stream=False):
    """Send chat request to Ollama."""
    payload = {
        "model": "kotonoha",
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 2048,
        },
    }
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{ollama_url}/api/chat", data=data, headers=headers)
    resp = urllib.request.urlopen(req, timeout=300)
    return json.loads(resp.read().decode("utf-8"))


def main():
    load_env()

    api_key = os.environ.get("RUNPOD_API_KEY", "")
    gpu_type = os.environ.get("RUNPOD_GPU_TYPE", "NVIDIA RTX 4090")
    volume_id = os.environ.get("RUNPOD_VOLUME_ID", "")
    public_key = os.environ.get("PUBLIC_KEY", "")
    image_name = os.environ.get("DOCKER_IMAGE", "")

    if not api_key:
        print("エラー: RUNPOD_API_KEY を設定してください")
        sys.exit(1)
    if not volume_id:
        print("エラー: RUNPOD_VOLUME_ID を設定してください")
        sys.exit(1)
    if not image_name:
        print("エラー: DOCKER_IMAGE を設定してください（例: registry.runpod.net/xxx）")
        sys.exit(1)

    print("==========================================")
    print("  KOTONOHA テストクライアント")
    print("  LLM-jp-4 on RunPod")
    print("==========================================")
    print()

    # Pod作成
    print("Podを作成中...")
    try:
        result = create_pod(api_key, gpu_type, volume_id, public_key, image_name)
        pod_data = result.get("data", {}).get("podFindAndDeployOnDemand", {})
        pod_id = pod_data.get("id")
        if not pod_id:
            print(f"Pod作成失敗: {result}")
            sys.exit(1)
        print(f"Pod ID: {pod_id}")
    except Exception as e:
        print(f"Pod作成失敗: {e}")
        sys.exit(1)

    # Pod起動待ち
    ollama_url = None
    ssh_info = None
    try:
        ollama_url, ssh_info = wait_for_pod(api_key, pod_id)
        print(f"Ollama: {ollama_url}")
        if ssh_info:
            print(f"SSH: ssh root@{ssh_info.split(':')[0]} -p {ssh_info.split(':')[1]}")
    except TimeoutError as e:
        print(f"\n{e}")
        print("Podをterminateします...")
        terminate_pod(api_key, pod_id)
        sys.exit(1)

    print()
    print("コマンド:")
    print("  /quit     Pod停止して終了")
    print("  /status   Pod状態確認")
    print("  /system   システムプロンプトを設定")
    print("  /clear    会話履歴をクリア")
    print("  /history  会話履歴を表示")
    print("  /ssh      SSH接続情報を表示")
    print()

    system_prompt = ""
    messages = []

    try:
        while True:
            try:
                user_input = input("あなた> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue

            if user_input in ("/quit", "/exit"):
                break

            if user_input == "/status":
                try:
                    result = get_pod(api_key, pod_id)
                    pod = result.get("data", {}).get("pod", {})
                    print(json.dumps(pod, indent=2, ensure_ascii=False))
                except Exception as e:
                    print(f"取得失敗: {e}")
                print()
                continue

            if user_input == "/system":
                try:
                    system_prompt = input("システムプロンプト> ").strip()
                except (EOFError, KeyboardInterrupt):
                    pass
                print("システムプロンプトを設定しました")
                print()
                continue

            if user_input.startswith("/system "):
                system_prompt = user_input[8:]
                print(f"システムプロンプトを設定しました: {system_prompt}")
                print()
                continue

            if user_input == "/clear":
                messages = []
                print("会話履歴をクリアしました")
                print()
                continue

            if user_input == "/history":
                print(json.dumps(messages, indent=2, ensure_ascii=False))
                print()
                continue

            if user_input == "/ssh":
                if ssh_info:
                    ip, port = ssh_info.split(":")
                    print(f"ssh root@{ip} -p {port}")
                else:
                    print("SSH情報なし（PUBLIC_KEY未設定）")
                print()
                continue

            # メッセージ追加
            messages.append({"role": "user", "content": user_input})

            chat_messages = list(messages)
            if system_prompt:
                chat_messages = [{"role": "system", "content": system_prompt}] + chat_messages

            try:
                print()
                sys.stdout.write("KOTONOHA> ")
                sys.stdout.flush()

                result = ollama_chat(ollama_url, chat_messages)
                response_text = result.get("message", {}).get("content", "(空の応答)")
                print(response_text)

                eval_count = result.get("eval_count", 0)
                prompt_eval_count = result.get("prompt_eval_count", 0)
                if eval_count or prompt_eval_count:
                    print(f"\n[tokens: prompt={prompt_eval_count}, completion={eval_count}]")

                messages.append({"role": "assistant", "content": response_text})

            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")
                print(f"HTTPエラー {e.code}: {body}")
            except urllib.error.URLError as e:
                print(f"接続エラー: {e.reason}")
                print("Podが停止した可能性があります")
            except Exception as e:
                print(f"エラー: {e}")

            print()

    finally:
        print()
        print("Podをterminateします...")
        try:
            terminate_pod(api_key, pod_id)
            print(f"Pod {pod_id} を削除しました")
        except Exception as e:
            print(f"terminate失敗: {e}")
            print(f"手動で削除してください: Pod ID = {pod_id}")


if __name__ == "__main__":
    main()
