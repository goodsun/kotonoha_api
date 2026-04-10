# API仕様

## 二層構造

KOTONOHAのAPIは2つのレイヤーで構成される。

### 1. Pod管理API（RunPod Pods API）

クライアント/PHPがPodの起動・停止を制御する。

- Pod作成: `POST https://api.runpod.io/v2/pods`
- Pod停止: `POST https://api.runpod.io/v2/pods/{pod_id}/stop`
- Pod削除: `DELETE https://api.runpod.io/v2/pods/{pod_id}`（terminate）
- Pod情報取得: `GET https://api.runpod.io/v2/pods/{pod_id}`

認証: `Authorization: Bearer {RUNPOD_API_KEY}`

Pod作成時のパラメータ:
- テンプレートID
- GPU種別
- Network Volume ID
- 環境変数（`PUBLIC_KEY`等）

### 2. Ollama API（Pod直接アクセス）

起動中のPodのOllamaに直接HTTPリクエストを送る。

ベースURL: `http://{pod_ip}:11434`

#### チャット

```
POST /api/chat
```

```json
{
  "model": "kotonoha",
  "messages": [
    {"role": "system", "content": "あなたは日本語AIです"},
    {"role": "user", "content": "こんにちは"}
  ],
  "stream": false,
  "options": {
    "temperature": 0.7,
    "top_p": 0.9,
    "num_predict": 2048
  }
}
```

レスポンス:

```json
{
  "model": "kotonoha",
  "message": {
    "role": "assistant",
    "content": "こんにちは！何かお手伝いできることはありますか？"
  },
  "done": true,
  "eval_count": 18,
  "prompt_eval_count": 12
}
```

#### ストリーミング

`"stream": true` にすると、Server-Sent Events形式でトークンが逐次返る。ブラウザJSから直接SSE接続可能。

#### モデル一覧

```
GET /api/tags
```

#### モデル情報

```
GET /api/show
```

## handler.pyの位置付け

Pods方式ではhandler.py（RunPod Serverlessハンドラ）は不要。Ollamaが直接APIを公開する。

handler.pyはServerless版のPoC用として残すが、本番運用ではOllama APIに直接アクセスする。

## パラメータ一覧（Ollama API）

| パラメータ | 型 | デフォルト | 範囲 | 説明 |
|---|---|---|---|---|
| model | string | "kotonoha" | — | Ollamaモデル名 |
| messages | array | — | — | チャットメッセージ配列 |
| stream | bool | true | — | ストリーミング有無 |
| options.temperature | float | 0.7 | 0.0-2.0 | 生成のランダム性 |
| options.top_p | float | 0.9 | 0.0-1.0 | トークン選択の確率閾値 |
| options.num_predict | int | 2048 | -1〜65536 | 最大生成トークン数 |
| options.num_ctx | int | 65536 | — | コンテキストウィンドウサイズ |

## SSH

Pod作成時に環境変数`PUBLIC_KEY`にユーザーの公開鍵を設定する。APIでの公開鍵設定は不要（Pod作成時に完結）。

```bash
ssh root@{pod_ip} -p 22 -i ~/.ssh/id_ed25519
```
