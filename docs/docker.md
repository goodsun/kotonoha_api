# Dockerイメージ仕様

## ベースイメージ

`runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`

## インストール済みコンポーネント

| コンポーネント | 用途 |
|---|---|
| Ollama | LLM推論エンジン |
| openssh-server | SSH接続受付 |
| runpod (Python) | RunPod Serverlessハンドラ |
| requests (Python) | Ollama API通信 |

## ファイル構成

| ファイル | 説明 |
|---|---|
| /handler.py | RunPodサーバレスハンドラ（チャット / pubkey設定） |
| /entrypoint.sh | コンテナ起動スクリプト |
| /Modelfile | Ollamaモデル定義（テンプレート、パラメータ、システムプロンプト） |
| /models/*.gguf | LLMモデルファイル（ビルド時にHuggingFaceからダウンロード） |

## モデル

ビルド時にHuggingFaceからGGUFをダウンロードし、Ollamaに`kotonoha`として登録する。

- ソース: `mmnga-o/llm-jp-4-8b-thinking-gguf`
- 量子化: Q4_K_M (~5.3GB)
- コンテキスト長: 65,536トークン

## ブランチごとのモデル切り替え

image_model_deployerと同様、ブランチごとにモデルを変える。

| ブランチ | モデル | GGUFサイズ |
|---------|--------|-----------|
| llm-jp-4-8b | LLM-jp-4 8B Q4_K_M | ~5.3GB |
| llm-jp-4-32b-a3b | LLM-jp-4 32B-A3B Q4_K_M | ~21GB |

ブランチ間の差分:
- Dockerfile: ダウンロードするGGUFのURL
- Modelfile: モデルパス

handler.py、entrypoint.shは全ブランチ共通。

## 起動シーケンス（entrypoint.sh）

1. 環境変数`PUBLIC_KEY`があればauthorized_keysに書き込み、sshd起動
2. `ollama serve` をバックグラウンド起動
3. Ollamaのヘルスチェック（最大120秒待機）
4. モデルの存在確認（なければModelfileから作成）
5. `handler.py` を起動（RunPodハンドラとして待ち受け）

## sshd設定

- パスワード認証: 無効
- 公開鍵認証: 有効
- rootログイン: 公開鍵のみ許可
- ポート: 22
