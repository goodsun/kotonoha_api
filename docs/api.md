# API仕様

## エンドポイント

RunPod Serverless APIを使用する。

- `POST /v2/{endpoint_id}/runsync` — 同期実行（レスポンスを待つ）
- `POST /v2/{endpoint_id}/run` — 非同期実行（ジョブIDを返す）
- `GET /v2/{endpoint_id}/status/{job_id}` — ジョブステータス確認
- `GET /v2/{endpoint_id}/health` — エンドポイント状態確認

認証: `Authorization: Bearer {RUNPOD_API_KEY}`

## アクション

handler.pyは`input`の内容でアクションを判別する。

### チャット（messages形式）

```json
{
  "input": {
    "messages": [
      {"role": "system", "content": "あなたは日本語AIです"},
      {"role": "user", "content": "こんにちは"}
    ],
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 2048,
    "stream": true
  }
}
```

### チャット（prompt形式）

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
  "output": {
    "response": "こんにちは！何かお手伝いできることはありますか？",
    "model": "kotonoha",
    "usage": {
      "prompt_tokens": 12,
      "completion_tokens": 18,
      "total_tokens": 30
    }
  }
}
```

### SSH公開鍵設定

`input`に`pubkey`のみを含め、`prompt`/`messages`を含めない。

```json
{
  "input": {
    "pubkey": "ssh-ed25519 AAAA... user@host"
  }
}
```

レスポンス:

```json
{
  "output": {
    "status": "ok",
    "message": "Public key set, SSH ready"
  }
}
```

注意: pubkey設定は同じワーカーに対して行う必要がある。ワーカーIDでルーティングすること。

## パラメータ

| パラメータ | 型 | デフォルト | 範囲 | 説明 |
|---|---|---|---|---|
| messages | array | — | — | チャットメッセージ配列 |
| prompt | string | — | — | 簡易プロンプト（messages未指定時） |
| system | string | "" | — | システムプロンプト（prompt形式時） |
| model | string | "kotonoha" | — | Ollamaモデル名 |
| temperature | float | 0.7 | 0.0-2.0 | 生成のランダム性 |
| top_p | float | 0.9 | 0.0-1.0 | トークン選択の確率閾値 |
| max_tokens | int | 2048 | 1-65536 | 最大生成トークン数 |
| stream | bool | false | — | Ollama側ストリーミング（RunPodレスポンスは一括） |
| pubkey | string | — | — | SSH公開鍵（チャットパラメータと排他） |

## エラーレスポンス

```json
{
  "output": {
    "error": "エラーメッセージ"
  }
}
```
