/**
 * 字幕校准 API - JavaScript 调用示例
 *
 * 在线体验: https://www.666082.xyz/
 * 联系QQ: 136172378
 *
 * 输入格式: .srt 字幕文件 + .txt 文稿文件
 * 输出格式: .lrc 歌词文件（可通过 lrc_srt_converter 转换为 .srt）
 */

const API_BASE = "https://api.666082.xyz/v1";
const API_KEY = "sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ";

const POLL_INTERVAL = 5000;
const MAX_POLL_TIME = 300000;

function generateNonce() {
    const timestamp = Math.floor(Date.now() / 1000);
    const randomStr = "xxxxxxxxxxxx".replace(/x/g, () =>
        Math.floor(Math.random() * 16).toString(16)
    );
    return `${timestamp}-${randomStr}`;
}

function getHeaders() {
    return {
        "X-API-Key": API_KEY,
        "X-Ca-Nonce": generateNonce(),
        "X-Ca-Timestamp": Date.now().toString(),
    };
}

async function verifyKey() {
    const resp = await fetch(`${API_BASE}/api/verify_key`, {
        method: "POST",
        headers: getHeaders(),
    });
    const data = await resp.json();

    if (data.valid) {
        console.log(
            `✅ API Key 有效 | 今日已用: ${data.usage_count} | 剩余: ${data.remaining}`
        );
    } else {
        console.log(`❌ API Key 无效: ${data.error}`);
    }

    return data;
}

async function calibrate(srtFile, txtFile, readParentheses = true) {
    console.log(`📤 上传文件: ${srtFile.name} + ${txtFile.name}`);

    const formData = new FormData();
    formData.append("files", srtFile);
    formData.append("files", txtFile);

    const uploadResp = await fetch(`${API_BASE}/api/upload_analyze`, {
        method: "POST",
        headers: getHeaders(),
        body: formData,
    });

    if (!uploadResp.ok) {
        const errData = await uploadResp.json().catch(() => ({}));
        throw new Error(`上传失败: ${uploadResp.status} ${errData.error || ""}`);
    }

    const uploadData = await uploadResp.json();
    if (uploadData.error) throw new Error(`上传错误: ${uploadData.error}`);

    const taskId = uploadData.task_id;
    console.log(`✅ 上传成功 | task_id: ${taskId}`);
    console.log(`   SRT: ${uploadData.srt_files}`);
    console.log(`   TXT: ${uploadData.txt_files}`);

    console.log("🚀 启动校准任务...");
    const startResp = await fetch(`${API_BASE}/api/start_process`, {
        method: "POST",
        headers: { ...getHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ task_id: taskId, read_parentheses: readParentheses }),
    });

    if (!startResp.ok) {
        const errData = await startResp.json().catch(() => ({}));
        throw new Error(`启动失败: ${startResp.status} ${errData.error || ""}`);
    }

    const startData = await startResp.json();
    if (startData.error) throw new Error(`启动错误: ${startData.error}`);

    console.log(`✅ 任务已启动 | 允许处理: ${startData.allowed_count} 个文件`);

    console.log("⏳ 等待校准完成...");
    const startTime = Date.now();

    while (true) {
        const elapsed = Date.now() - startTime;
        if (elapsed > MAX_POLL_TIME) {
            throw new Error("超时");
        }

        const statusResp = await fetch(`${API_BASE}/api/status/${taskId}`, {
            headers: getHeaders(),
        });
        const data = await statusResp.json();

        if (data.status === "pending") {
            console.log("   ⏳ 排队中...");
        } else if (data.status === "processing") {
            console.log(`   🔄 处理中: ${data.completed}/${data.total}`);
        } else if (data.status === "completed") {
            console.log("✅ 校准完成!");
            const results = data.results || [];

            results.forEach((r) => {
                if (r.type === "LRC" && r.content) {
                    console.log(`   📄 ${r.name}:`);
                    console.log(r.content.substring(0, 200) + "...");
                } else if (r.type === "ERROR") {
                    console.log(`   ❌ ${r.name}: ${r.error}`);
                }
            });

            return { taskId, results };
        } else if (data.status === "error") {
            throw new Error(`任务错误: ${data.error || "未知"}`);
        }

        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL));
    }
}

async function calibrateAndDownload(srtFile, txtFile, readParentheses = true) {
    const result = await calibrate(srtFile, txtFile, readParentheses);

    result.results.forEach((r) => {
        if (r.type === "LRC" && r.content) {
            const blob = new Blob([r.content], { type: "text/plain;charset=utf-8" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = r.name;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    });

    return result;
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = { verifyKey, calibrate, calibrateAndDownload };
}
