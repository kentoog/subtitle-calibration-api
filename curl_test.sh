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
#
# 调用规范提示:
#   - 上传前会先用仓库 utils/srt_txt_precheck.py 做本地输入预检（Python 3 零依赖，不耗配额）。
#     预检未通过（退出码非 0，含琥珀/橙/红档）时中止；确认差异仅为数字/英文写法可忽略时，
#     用 SKIP_PRECHECK=1 ./curl_test.sh ... 跳过预检。
#   - 本脚本演示单组文件调用；实际使用建议单次请求批量携带多组文件（≤100 文件 / 50 组），
#     不建议多次单文件发送请求，以节省资源。
#   - 大文件建议 gzip 压缩后上传，并在表单中附带 compress=gzip 字段（服务端自动解压）。
# ============================================================

set -e

API_BASE="https://api.yzbch.cn/v1"
API_BASE_ALT="https://api.666082.xyz/v1"   # 备选入口：将上面 API_BASE 替换为此值即可
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

# ----- Step 0: 输入预检（本地运行，不消耗额度）-----
# 用仓库自带 utils/srt_txt_precheck.py 检查 SRT/TXT 是否适合校准（判级与处置见 API.md）。
# 退出码非 0（存在琥珀/橙/红档或异常）时中止；若差异仅为数字/英文写法，可 SKIP_PRECHECK=1 跳过。
if [ "${SKIP_PRECHECK:-0}" = "1" ]; then
    echo "[Step 0] SKIP_PRECHECK=1，跳过输入预检。"
elif [ -f "utils/srt_txt_precheck.py" ]; then
    echo ""
    echo "[Step 0] 输入预检（本地，不耗额度）..."
    if ! python3 utils/srt_txt_precheck.py "${SRT_FILE}" "${TXT_FILE}" --brief; then
        echo ""
        echo "[中止] 预检未通过：请核对摘要与 gaps 原文对照。"
        echo "       若差异仅为数字/英文写法可忽略，用 SKIP_PRECHECK=1 重新运行本脚本跳过预检。"
        exit 1
    fi
else
    echo ""
    echo "[Step 0] 未找到 utils/srt_txt_precheck.py，跳过预检（建议从仓库获取后先预检）。"
fi

# ----- Step 1: 连通性探测（不消耗校准额度）-----
# 说明: 本 API 不提供 /api/verify_key 端点（Key 有效性在首次上传时校验）。
# 返回 {"error":"Invalid task_id"} 即代表网络可达、鉴权头格式正确。
echo ""
echo "[Step 1] 连通性探测..."
eval curl -s $(gen_headers) "${API_BASE}/api/status/probe-connectivity" | python3 -m json.tool 2>/dev/null || \
eval curl -s $(gen_headers) "${API_BASE}/api/status/probe-connectivity"
echo ""

# ----- Step 2: 上传文件 -----
echo "[Step 2] 上传文件..."
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

# ----- Step 3: 启动校准 -----
echo ""
echo "[Step 3] 启动校准..."
eval curl -s $(gen_headers) \
    -H "Content-Type: application/json" \
    -d "{\"task_id\": \"${TASK_ID}\", \"read_parentheses\": true}" \
    "${API_BASE}/api/start_process" | python3 -m json.tool 2>/dev/null

sleep 1

# ----- Step 4: 轮询结果 -----
echo ""
echo "[Step 4] 轮询结果..."
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
            # 保存校准后的 SRT 到文件
            echo "${STATUS_RESP}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data.get('results', []):
    if r.get('type') == 'SRT' and r.get('content'):
        fname = r.get('name', 'output.srt')
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
