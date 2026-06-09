#!/bin/bash
# ============================================================
# 字幕校准 API — 一键 curl 测试脚本
# Subtitle Calibration API — Quick Curl Test
#
# 用法:
#   chmod +x curl_test.sh
#   ./curl_test.sh example.srt example.txt
#
# 依赖:
#   - curl, uuidgen (Linux/macOS 内置, Windows Git Bash 可用)
# ============================================================

set -e

API_BASE="https://api.666082.xyz/v1"
API_KEY="sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ"

SRT_FILE="${1:?错误: 请指定 SRT 文件路径，例如 ./curl_test.sh example.srt example.txt}"
TXT_FILE="${2:?错误: 请指定 TXT 文件路径}"

# 生成通用请求头
gen_headers() {
    local ts=$(date +%s%3N)
    local nonce=$(uuidgen | tr '[:upper:]' '[:lower:]')
    echo "-H \"X-API-Key: ${API_KEY}\" -H \"X-Ca-Timestamp: ${ts}\" -H \"X-Ca-Nonce: ${nonce}\""
}

echo "============================================"
echo "  字幕校准 API — 快速测试"
echo "============================================"
echo "  API:    ${API_BASE}"
echo "  Key:    ${API_KEY:0:20}..."
echo "  SRT:    ${SRT_FILE}"
echo "  TXT:    ${TXT_FILE}"
echo "============================================"

# ----- Step 0: 验证 Key（可选）-----
echo ""
echo "[Step 0] 验证 API Key..."
eval curl -s $(gen_headers) "${API_BASE}/api/verify_key" | python3 -m json.tool 2>/dev/null || \
eval curl -s $(gen_headers) "${API_BASE}/api/verify_key"
echo ""

# ----- Step 1: 上传文件 -----
echo "[Step 1] 上传文件..."
UPLOAD_RESP=$(eval curl -s $(gen_headers) \
    -F "files=@${SRT_FILE}" \
    -F "files=@${TXT_FILE}" \
    "${API_BASE}/api/upload_analyze")
echo "${UPLOAD_RESP}" | python3 -m json.tool 2>/dev/null || echo "${UPLOAD_RESP}"

TASK_ID=$(echo "${UPLOAD_RESP}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('task_id',''))" 2>/dev/null)
if [ -z "${TASK_ID}" ]; then
    echo "[错误] 未获取到 task_id，终止。"
    exit 1
fi
echo "  → task_id: ${TASK_ID}"

# 频率限制等待
sleep 1

# ----- Step 2: 启动校准 -----
echo ""
echo "[Step 2] 启动校准..."
eval curl -s $(gen_headers) \
    -H "Content-Type: application/json" \
    -d "{\"task_id\": \"${TASK_ID}\", \"read_parentheses\": true}" \
    "${API_BASE}/api/start_process" | python3 -m json.tool 2>/dev/null

sleep 1

# ----- Step 3: 轮询结果 -----
echo ""
echo "[Step 3] 轮询结果..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [ ${ATTEMPT} -lt ${MAX_ATTEMPTS} ]; do
    ATTEMPT=$((ATTEMPT + 1))
    STATUS_RESP=$(eval curl -s $(gen_headers) "${API_BASE}/api/status/${TASK_ID}")
    STATUS=$(echo "${STATUS_RESP}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)

    case "${STATUS}" in
        completed)
            echo ""
            echo "✅ 校准完成！结果如下："
            echo "${STATUS_RESP}" | python3 -m json.tool 2>/dev/null
            # 保存 LRC 到文件
            echo "${STATUS_RESP}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data.get('results', []):
    if r.get('type') == 'LRC' and r.get('content'):
        fname = r.get('name', 'output.lrc')
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(r['content'])
        print(f'  → 已保存: {fname}')
" 2>/dev/null
            exit 0
            ;;
        processing|pending)
            echo "  [${ATTEMPT}/${MAX_ATTEMPTS}] 处理中，等待 3 秒..."
            sleep 3
            ;;
        error|failed)
            echo ""
            echo "❌ 处理失败："
            echo "${STATUS_RESP}" | python3 -m json.tool 2>/dev/null
            exit 1
            ;;
        *)
            echo "  [${ATTEMPT}/${MAX_ATTEMPTS}] 状态: ${STATUS:-未知}，等待 3 秒..."
            sleep 3
            ;;
    esac
done

echo ""
echo "⚠️  超时：已轮询 ${MAX_ATTEMPTS} 次，任务未完成。请手动检查 task_id=${TASK_ID}"
exit 1
