# Dockerイメージ仕様

## ベースイメージ

`runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`

## 設計方針

- モデルファイルはDockerイメージに含めない → Network Volumeからマウント
- イメージは軽量に保つ（Ollama + sshd + 設定ファイルのみ）
- handler.pyは不要（Pods方式ではOllamaが直接応答）

## インストール済みコンポーネント

| コンポーネント | 用途 |
|---|---|
| Ollama | LLM推論エンジン |
| openssh-server | SSH接続受付 |

## ファイル構成

| ファイル | 説明 |
|---|---|
| /entrypoint.sh | コンテナ起動スクリプト |
| /Modelfile | Ollamaモデル定義（テンプレート、パラメータ、システムプロンプト） |

## モデル

Network Volume（`/models/`にマウント）にGGUFファイルを配置。

- ソース: `mmnga-o/llm-jp-4-8b-thinking-gguf`
- 量子化: Q4_K_M (~5.3GB)
- コンテキスト長: 65,536トークン

Modelfileは `/models/` のGGUFを参照し、起動時に`ollama create`でモデルを登録する。

## ブランチごとのモデル切り替え

| ブランチ | モデル | GGUFサイズ |
|---------|--------|-----------|
| llm-jp-4-8b | LLM-jp-4 8B Q4_K_M | ~5.3GB |
| llm-jp-4-32b-a3b | LLM-jp-4 32B-A3B Q4_K_M | ~21GB |

ブランチ間の差分:
- Modelfile: モデルパスとパラメータ
- Dockerfile: 不要パッケージの差異（あれば）

entrypoint.shは全ブランチ共通。

## 起動シーケンス（entrypoint.sh）

1. 環境変数`PUBLIC_KEY`があれば`authorized_keys`に書き込み、sshd起動
2. `ollama serve`をバックグラウンド起動
3. Ollamaのヘルスチェック（最大120秒待機）
4. Modelfileからモデル登録（`ollama create kotonoha`）
5. 待ち受け状態（Ollamaがポート11434でリクエスト受付）

## sshd設定

- パスワード認証: 無効
- 公開鍵認証: 有効
- rootログイン: 公開鍵のみ許可
- ポート: 22

## ポート公開

| ポート | 用途 |
|--------|------|
| 11434 | Ollama API |
| 22 | SSH |
