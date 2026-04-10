#!/bin/bash
#
# KOTONOHA テストシェル
# RunPodエンドポイントと対話するインタラクティブシェル
#
# 使い方:
#   ./test_chat.sh
#   ./test_chat.sh --env .env
#   RUNPOD_API_KEY=xxx RUNPOD_ENDPOINT_ID=yyy ./test_chat.sh
#

set -euo pipefail

# --- 設定読み込み ---

ENV_FILE="${1:-.env}"
if [ "${1:-}" = "--env" ]; then
    ENV_FILE="${2:-.env}"
fi

if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

if [ -z "${RUNPOD_API_KEY:-}" ] || [ -z "${RUNPOD_ENDPOINT_ID:-}" ]; then
    echo "エラー: RUNPOD_API_KEY と RUNPOD_ENDPOINT_ID を設定してください"
    echo ""
    echo "方法1: .env ファイルを作成"
    echo "  cp .env.example .env"
    echo "  # .env を編集"
    echo ""
    echo "方法2: 環境変数で指定"
    echo "  RUNPOD_API_KEY=xxx RUNPOD_ENDPOINT_ID=yyy ./test_chat.sh"
    exit 1
fi

ENDPOINT="https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}"

# --- ヘルパー関数 ---

submit_job() {
    local payload="$1"
    curl -s -X POST "${ENDPOINT}/run" \
        -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
        -H "Content-Type: application/json" \
        -d "$payload"
}

check_status() {
    local job_id="$1"
    curl -s "${ENDPOINT}/status/${job_id}" \
        -H "Authorization: Bearer ${RUNPOD_API_KEY}"
}

poll_result() {
    local job_id="$1"
    local max_wait=300
    local waited=0

    while [ $waited -lt $max_wait ]; do
        local result
        result=$(check_status "$job_id")
        local status
        status=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")

        case "$status" in
            COMPLETED)
                echo "$result" | python3 -c "
import sys, json
data = json.load(sys.stdin)
output = data.get('output', {})
if 'error' in output:
    print(f\"エラー: {output['error']}\")
else:
    print(output.get('response', '(空の応答)'))
    usage = output.get('usage', {})
    if usage:
        print(f\"\\n[tokens: prompt={usage.get('prompt_tokens',0)}, completion={usage.get('completion_tokens',0)}]\")
"
                return 0
                ;;
            FAILED)
                echo "$result" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"ジョブ失敗: {data.get('error', '不明なエラー')}\")
"
                return 1
                ;;
            IN_QUEUE|IN_PROGRESS)
                printf "\r待機中... (%ds)" "$waited"
                sleep 2
                waited=$((waited + 2))
                ;;
            *)
                echo "不明なステータス: $status"
                echo "$result"
                return 1
                ;;
        esac
    done
    echo "タイムアウト (${max_wait}s)"
    return 1
}

# --- メイン ---

echo "=========================================="
echo "  KOTONOHA テストシェル"
echo "  LLM-jp-4 on RunPod"
echo "=========================================="
echo ""
echo "エンドポイント: ${RUNPOD_ENDPOINT_ID}"
echo ""
echo "コマンド:"
echo "  /quit     終了"
echo "  /status   エンドポイントの状態確認"
echo "  /system   システムプロンプトを設定"
echo "  /clear    会話履歴をクリア"
echo "  /history  会話履歴を表示"
echo ""

SYSTEM_PROMPT=""
MESSAGES="[]"

while true; do
    echo -n "あなた> "
    read -r user_input

    [ -z "$user_input" ] && continue

    case "$user_input" in
        /quit|/exit)
            echo "終了します"
            exit 0
            ;;
        /status)
            echo "エンドポイント状態を確認中..."
            curl -s "${ENDPOINT}/health" \
                -H "Authorization: Bearer ${RUNPOD_API_KEY}" | python3 -m json.tool 2>/dev/null || echo "取得失敗"
            echo ""
            continue
            ;;
        /system)
            echo -n "システムプロンプト> "
            read -r SYSTEM_PROMPT
            echo "システムプロンプトを設定しました"
            echo ""
            continue
            ;;
        /system\ *)
            SYSTEM_PROMPT="${user_input#/system }"
            echo "システムプロンプトを設定しました: ${SYSTEM_PROMPT}"
            echo ""
            continue
            ;;
        /clear)
            MESSAGES="[]"
            echo "会話履歴をクリアしました"
            echo ""
            continue
            ;;
        /history)
            echo "$MESSAGES" | python3 -m json.tool 2>/dev/null || echo "$MESSAGES"
            echo ""
            continue
            ;;
    esac

    # メッセージを追加
    MESSAGES=$(echo "$MESSAGES" | python3 -c "
import sys, json
msgs = json.load(sys.stdin)
msgs.append({'role': 'user', 'content': '''${user_input//\'/\'\\\'\'}'''})
print(json.dumps(msgs, ensure_ascii=False))
")

    # ペイロード構築
    if [ -n "$SYSTEM_PROMPT" ]; then
        PAYLOAD=$(python3 -c "
import json
msgs = json.loads('''${MESSAGES}''')
full = [{'role': 'system', 'content': '''${SYSTEM_PROMPT//\'/\'\\\'\'}'''}] + msgs
print(json.dumps({'input': {'messages': full, 'stream': True}}, ensure_ascii=False))
")
    else
        PAYLOAD=$(python3 -c "
import json
msgs = json.loads('''${MESSAGES}''')
print(json.dumps({'input': {'messages': msgs, 'stream': True}}, ensure_ascii=False))
")
    fi

    # ジョブ送信
    RESPONSE=$(submit_job "$PAYLOAD")
    JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

    if [ -z "$JOB_ID" ]; then
        echo "ジョブ送信失敗:"
        echo "$RESPONSE"
        echo ""
        continue
    fi

    echo ""
    echo -n "KOTONOHA> "
    RESULT_TEXT=$(poll_result "$JOB_ID")
    printf "\r"
    echo "KOTONOHA> ${RESULT_TEXT}"
    echo ""

    # アシスタントの応答を履歴に追加（tokenカウント行を除く）
    ASSISTANT_RESPONSE=$(echo "$RESULT_TEXT" | head -1)
    MESSAGES=$(echo "$MESSAGES" | python3 -c "
import sys, json
msgs = json.load(sys.stdin)
msgs.append({'role': 'assistant', 'content': '''${ASSISTANT_RESPONSE//\'/\'\\\'\'}'''})
print(json.dumps(msgs, ensure_ascii=False))
")
done
