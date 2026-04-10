# アーキテクチャ

## 概要

KOTONOHAはRunPod Pods APIを使い、ユーザー専用のGPU Podをオンデマンドで起動・停止する。LLM-jp-4が使えるクローズドな専有GPUの時間貸しサービス。

## サービスの本質

- ユーザーが起動ボタンを押す → 専用Pod作成
- 自分だけのGPUでLLM-jp-4を使える（チャットUI、SSH）
- 終わったら停止 → Pod消滅、データも鍵も消える（使い捨て）
- 使った時間分だけ課金

## CIELとの違い

| | CIEL（画像生成） | KOTONOHA（LLMチャット） |
|---|---|---|
| ワーカー | 共有型（複数ユーザーが同一ワーカー） | 専有型（1ユーザー1 Pod） |
| 料金 | 使用秒数で按分 | 全額負担 |
| SSH | なし | あり |
| Pod管理 | 常駐 | オンデマンド起動・終了時にterminate |

## RunPod Pods API（Serverlessではない）

ServerlessではなくPods APIを使う理由：
- SSH接続にはパブリックIPとポート公開が必要 → Serverlessでは不可
- セッション単位の長時間利用 → Serverlessはリクエスト単位向き
- ユーザー専有のPod → Podsなら1ユーザー1 Pod

## モデルストレージ

RunPod Network Volumeにモデルを配置する。

- Dockerイメージにモデルを焼き込まない → イメージが軽い、Pod起動が速い
- Network Volume: $0.07/GB/月（8Bモデル5.3GBで月額約$0.37）
- 複数Podから同じvolumeをマウント可能

## Pod ライフサイクル

```
1. ユーザーが起動ボタンを押す
2. クライアント/PHPがRunPod Pods APIでPod作成
   - テンプレートID指定（Dockerイメージ + GPU設定）
   - Network Volumeマウント
   - 環境変数にPUBLIC_KEY（ユーザーの公開鍵）を注入
3. Pod起動
   - entrypoint.sh: SSH鍵設定 → sshd起動 → Ollama起動 → モデルロード
4. ユーザーがチャットUI / SSH で利用
5. ユーザーが停止ボタンを押す or 残高ゼロ
6. クライアント/PHPがRunPod Pods APIでPod terminate
   - データ、鍵、すべて消滅
```

## スケール

- テンプレートを1つ用意すれば、APIでPodを複製できる
- 10人が同時に使えば10 Pod、100人なら100 Pod
- Pod数の上限はアカウントクォータ（サポートに連絡で増枠可能）

## コンポーネント構成

```
[クライアント（PHP / test_chat.py / ブラウザJS）]
  ├── RunPod Pods APIでPod起動・停止
  ├── Pod のIPアドレスでOllama APIに直接アクセス
  ├── チャット履歴はクライアント側で保持
  └── SSH接続（PodのパブリックIP + ポート22）

[RunPod Pod（ユーザー専有）]
  ├── Ollama（LLM-jp-4）  ← LLM推論、ポート11434
  ├── sshd                  ← SSH接続、ポート22
  └── Network Volume        ← モデルファイル（/models/）
```

## ステートレス設計

- Pod側に会話状態を持たない
- チャット履歴はクライアントが保持し、毎回全メッセージを送信
- Podをterminateすればデータは全て消える（使い捨て）
