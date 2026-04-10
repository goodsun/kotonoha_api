# KOTONOHA API

RunPod Serverless で LLM-jp-4 を Ollama 経由で提供する API。

## ブランチ構成

| ブランチ | モデル | サイズ |
|---------|--------|--------|
| `llm-jp-4-8b` | LLM-jp-4 8B thinking Q4_K_M | ~5.3GB |
| `llm-jp-4-32b-a3b` | LLM-jp-4 32B-A3B thinking Q4_K_M | ~21GB |

## デプロイ

1. RunPod でカスタムテンプレートを作成
2. Docker イメージをビルド・プッシュ
3. サーバレスエンドポイントを作成

```bash
docker build -t kotonoha-api:8b .
```

## テスト

```bash
cp .env.example .env
# .env に RUNPOD_API_KEY と RUNPOD_ENDPOINT_ID を設定

chmod +x test_chat.sh
./test_chat.sh
```

## API

### リクエスト

```json
{
  "input": {
    "messages": [
      {"role": "user", "content": "こんにちは"}
    ],
    "temperature": 0.7,
    "max_tokens": 2048
  }
}
```

または簡易モード:

```json
{
  "input": {
    "prompt": "日本の首都は？",
    "system": "簡潔に答えてください"
  }
}
```

### レスポンス

```json
{
  "response": "こんにちは！何かお手伝いできることはありますか？",
  "model": "mmnga-o/llm-jp-4-8b-thinking-gguf:Q4_K_M",
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 18,
    "total_tokens": 30
  }
}
```
