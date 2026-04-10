# KOTONOHA API

RunPod Pods でユーザー専有の LLM-jp-4 環境をオンデマンド提供する。

## 概要

- ユーザーが起動 → 専用Pod作成 → LLM-jp-4でチャット + SSH接続
- 終了 → Pod terminate → 全データ消滅（使い捨て）
- モデルは Network Volume に配置（Dockerイメージに含めない）

## ブランチ構成

| ブランチ | モデル | サイズ |
|---------|--------|--------|
| `llm-jp-4-8b` | LLM-jp-4 8B thinking Q4_K_M | ~5.3GB |
| `llm-jp-4-32b-a3b` | LLM-jp-4 32B-A3B thinking Q4_K_M | ~21GB |

## セットアップ

### 1. Network Volume

RunPod で Network Volume を作成し、モデルファイルを配置:

```
/runpod-volume/models/llm-jp-4-8b-thinking-Q4_K_M.gguf
```

### 2. Docker イメージ

```bash
docker build -t kotonoha-api:8b .
# RunPod のレジストリにプッシュ
```

### 3. テスト

```bash
cp .env.example .env
# .env を編集
python3 test_chat.py
```

## API

起動中の Pod の Ollama API に直接アクセス:

```bash
curl http://{pod_ip}:11434/api/chat -d '{
  "model": "kotonoha",
  "messages": [{"role": "user", "content": "こんにちは"}],
  "stream": false
}'
```

## SSH

Pod 作成時に PUBLIC_KEY 環境変数で公開鍵を注入:

```bash
ssh root@{pod_ip} -p {port}
```

## 詳細仕様

docs/ ディレクトリを参照。
