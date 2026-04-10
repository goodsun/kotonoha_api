# テストクライアント（test_chat.py）

## 概要

RunPodエンドポイントと対話するインタラクティブシェル。標準ライブラリのみで動作し、外部依存なし。

## 使い方

```bash
cp .env.example .env
# .env に RUNPOD_API_KEY と RUNPOD_ENDPOINT_ID を設定
python3 test_chat.py
```

または環境変数で直接指定:

```bash
RUNPOD_API_KEY=xxx RUNPOD_ENDPOINT_ID=yyy python3 test_chat.py
```

## コマンド

| コマンド | 説明 |
|---|---|
| /quit, /exit | 終了 |
| /status | エンドポイントの状態確認 |
| /system | システムプロンプトを設定（対話式） |
| /system {text} | システムプロンプトを設定（インライン） |
| /clear | 会話履歴をクリア |
| /history | 会話履歴を表示 |
| /pubkey | SSH公開鍵を登録（対話式） |
| /pubkey {key} | SSH公開鍵を登録（インライン） |

## 動作

- デフォルトで`runsync`（同期モード）を使用
- `runsync`がタイムアウトした場合、自動的にポーリングにフォールバック
- チャット履歴はクライアント側（メモリ上）で保持
- 毎回全メッセージを`messages`配列で送信

## 制限事項

- ワーカーIDのルーティングは未実装（TODO）
- SSH接続情報（ワーカーのIP）の取得は未実装（TODO）
