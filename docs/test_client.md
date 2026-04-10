# テストクライアント（test_chat.py）

## 概要

KOTONOHAのテスト用クライアント。標準ライブラリのみで動作。

## 現状

現在のtest_chat.pyはRunPod Serverless向けに実装されている。Pods方式への移行に伴い、以下の変更が必要。

## TODO: Pods方式への対応

1. RunPod Pods APIでPodを起動（`create_pod`）
2. Pod起動完了を待つ（ヘルスチェック）
3. PodのIPアドレスを取得
4. Ollama API（`http://{pod_ip}:11434/api/chat`）に直接リクエスト
5. 終了時にPodをterminate

## 使い方（予定）

```bash
cp .env.example .env
# .env に RUNPOD_API_KEY, RUNPOD_TEMPLATE_ID, RUNPOD_VOLUME_ID を設定
python3 test_chat.py
```

## コマンド（予定）

| コマンド | 説明 |
|---|---|
| /quit, /exit | Pod停止して終了 |
| /status | Pod状態確認 |
| /system | システムプロンプトを設定 |
| /clear | 会話履歴をクリア |
| /history | 会話履歴を表示 |
| /ssh | SSH接続情報を表示 |
