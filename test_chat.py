#!/usr/bin/env python3
"""
KOTONOHA テストシェル
RunPodエンドポイントと対話するインタラクティブシェル
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
    """Load .env file."""
    if Path(path).exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


def api_request(url, headers, data=None, timeout=300):
    """Make HTTP request using urllib."""
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=headers)
    else:
        req = urllib.request.Request(url, headers=headers)
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode("utf-8"))


def main():
    load_env()

    api_key = os.environ.get("RUNPOD_API_KEY", "")
    endpoint_id = os.environ.get("RUNPOD_ENDPOINT_ID", "")

    if not api_key or not endpoint_id:
        print("エラー: RUNPOD_API_KEY と RUNPOD_ENDPOINT_ID を設定してください")
        print()
        print("方法1: .env ファイルを作成")
        print("  cp .env.example .env && vi .env")
        print()
        print("方法2: 環境変数で指定")
        print("  RUNPOD_API_KEY=xxx RUNPOD_ENDPOINT_ID=yyy python3 test_chat.py")
        sys.exit(1)

    base_url = f"https://api.runpod.ai/v2/{endpoint_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print("==========================================")
    print("  KOTONOHA テストシェル")
    print("  LLM-jp-4 on RunPod")
    print("==========================================")
    print()
    print(f"エンドポイント: {endpoint_id}")
    print()
    print("コマンド:")
    print("  /quit     終了")
    print("  /status   エンドポイントの状態確認")
    print("  /system   システムプロンプトを設定")
    print("  /clear    会話履歴をクリア")
    print("  /history  会話履歴を表示")
    print()

    system_prompt = ""
    messages = []

    while True:
        try:
            user_input = input("あなた> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n終了します")
            break

        if not user_input:
            continue

        # コマンド処理
        if user_input in ("/quit", "/exit"):
            print("終了します")
            break

        if user_input == "/status":
            try:
                data = api_request(f"{base_url}/health", headers, timeout=10)
                print(json.dumps(data, indent=2, ensure_ascii=False))
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

        # メッセージ追加
        messages.append({"role": "user", "content": user_input})

        # ペイロード構築
        chat_messages = list(messages)
        if system_prompt:
            chat_messages = [{"role": "system", "content": system_prompt}] + chat_messages

        payload = {
            "input": {
                "messages": chat_messages,
                "stream": True,
            }
        }

        try:
            print()
            # runsync で同期的に結果を取得
            data = api_request(f"{base_url}/runsync", headers, payload, timeout=300)

            status = data.get("status", "")
            if status == "COMPLETED":
                output = data.get("output", {})
                if "error" in output:
                    print(f"KOTONOHA> エラー: {output['error']}")
                else:
                    response_text = output.get("response", "(空の応答)")
                    print(f"KOTONOHA> {response_text}")
                    usage = output.get("usage", {})
                    if usage:
                        print(f"\n[tokens: prompt={usage.get('prompt_tokens', 0)}, completion={usage.get('completion_tokens', 0)}]")
                    messages.append({"role": "assistant", "content": response_text})

            elif status == "IN_PROGRESS":
                # runsync がタイムアウトした場合、ポーリングにフォールバック
                job_id = data.get("id", "")
                if not job_id:
                    print("KOTONOHA> ジョブID取得失敗")
                else:
                    max_wait = 300
                    waited = 0
                    while waited < max_wait:
                        status_data = api_request(
                            f"{base_url}/status/{job_id}", headers, timeout=10
                        )
                        s = status_data.get("status", "")
                        if s == "COMPLETED":
                            output = status_data.get("output", {})
                            if "error" in output:
                                print(f"KOTONOHA> エラー: {output['error']}")
                            else:
                                response_text = output.get("response", "(空の応答)")
                                print(f"KOTONOHA> {response_text}")
                                usage = output.get("usage", {})
                                if usage:
                                    print(f"\n[tokens: prompt={usage.get('prompt_tokens', 0)}, completion={usage.get('completion_tokens', 0)}]")
                                messages.append({"role": "assistant", "content": response_text})
                            break
                        elif s == "FAILED":
                            print(f"KOTONOHA> ジョブ失敗: {status_data.get('error', '不明')}")
                            break
                        else:
                            sys.stdout.write(f"\r待機中... ({waited}s)")
                            sys.stdout.flush()
                            time.sleep(2)
                            waited += 2
                    else:
                        print(f"\nタイムアウト ({max_wait}s)")

            elif status == "FAILED":
                print(f"KOTONOHA> ジョブ失敗: {data.get('error', '不明なエラー')}")

            else:
                print(f"KOTONOHA> 予期しないステータス: {status}")
                print(json.dumps(data, indent=2, ensure_ascii=False))

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"HTTPエラー {e.code}: {body}")
        except urllib.error.URLError as e:
            print(f"接続エラー: {e.reason}")
        except Exception as e:
            print(f"エラー: {e}")

        print()


if __name__ == "__main__":
    main()
