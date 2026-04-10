# セッション管理

## 概要

KOTONOHAはRunPod Pods APIでユーザー専有のPodをオンデマンド起動する。Podは使い捨てで、terminateすると全データが消滅する。

## セッションフロー

```
クライアント                          RunPod
    |                                   |
    |-- create_pod(template, volume) -->|
    |                                   |-- Pod起動（イメージpull）
    |                                   |-- entrypoint.sh実行
    |                                   |-- SSH鍵設定、sshd起動
    |                                   |-- Ollama起動、Network Volumeからモデルロード
    |<-- Pod情報（ID, IP, ポート）------|
    |                                   |
    |-- Ollama API直接アクセス -------->| (PodのIP:11434)
    |<-- レスポンス -------------------|
    |                                   |
    |-- SSH接続 ---------------------->| (PodのIP:22)
    |                                   |
    |   ... 利用中 ...                  |
    |                                   |
    |-- terminate_pod(pod_id) -------->|
    |                                   |-- Pod消滅（全データ削除）
```

## Serverlessとの違い

| | Serverless（旧設計） | Pods（現設計） |
|---|---|---|
| 起動単位 | リクエスト単位 | セッション単位 |
| SSH | 不可（パブリックIPなし） | 可能 |
| 通信 | RunPod APIを介する | PodのIPに直接アクセス |
| 停止 | アイドルタイムアウトで自動 | API呼び出しでterminate |
| handler.py | 必要（RunPodハンドラ） | 不要（Ollamaが直接応答） |

## チャット

- PodのOllama API（`http://{pod_ip}:11434/api/chat`）に直接リクエスト
- handler.pyを介さない
- チャット履歴はクライアント側で保持し、毎回全メッセージを送信

## SSH接続

- Pod作成時に環境変数`PUBLIC_KEY`でユーザーの公開鍵を注入
- entrypoint.shが`authorized_keys`に書き込み、sshd起動
- PodのパブリックIP + ポート22で接続
- 1 Pod = 1ユーザーの鍵のみ

## 課金と停止

- Pod起動時から時間課金（RunPodの課金 + マージン）
- PHP側のcronで残高を定期的に減算
- 残高わずか → 警告通知
- 残高ゼロ → 自動terminate
- ユーザーが自分で停止ボタンを押すことも可能

## Network Volume

- モデルファイルはNetwork Volumeに永続化
- Podはvolumeをマウントして起動 → モデルのダウンロード不要
- 複数Podから同時マウント可能（読み取り専用）
- コスト: $0.07/GB/月（8Bモデルで月額約$0.37）
