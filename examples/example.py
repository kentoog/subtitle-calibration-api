"""
字幕校准 API 示例模块

========== 接口契约 ==========

端点                     | 方法 | 请求格式            | 响应格式   | 说明
-------------------------|------|---------------------|-----------|--------------------------------------------
/api/upload_analyze      | POST | multipart/form-data | JSON      | 上传 SRT+TXT 文件对，返回 task_id
/api/start_process       | POST | application/json    | JSON      | 用 task_id 启动校准处理
/api/status/<task_id>    | GET  | —                   | JSON      | 轮询处理状态，返回 status/completed/error

上传字段说明:
  files (必填): 同时上传 SRT 和 TXT 文件，使用同一字段名 files
                每个文件使用独立的 multipart 条目
                后端通过文件扩展名 .srt / .txt 区分类型

状态轮询响应:
  status:   processing | completed | error
  results:  当 status=completed 时，LRC 内容在 results[].content 中
  accuracy_results:  当 status=completed 时返回，每个文件的内容匹配校验状态
                    (normal 或 abnormal)，以及异常行号 stuck_line（>0 时表示校准在该行提前终止，请检查该序号附近的字幕与文稿内容）。
                    如果结果为 abnormal，请检查原字幕及原始文稿是否缺失或错位。

========== curl 等价调用 ==========

上传文件:
  curl -X POST https://api.666082.xyz/v1/api/upload_analyze \\
    -H "X-API-Key: sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ" \\
    -H "X-Ca-Timestamp: $(date +%%s%%3N)" \\
    -F "files=@1.srt" \\
    -F "files=@1.txt"

启动校准:
  curl -X POST https://api.666082.xyz/v1/api/start_process \\
    -H "Content-Type: application/json" \\
    -H "X-API-Key: sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ" \\
    -d '{"task_id":"<task_id>","key":"sk-..."}'

轮询状态:
  curl https://api.666082.xyz/v1/api/status/<task_id> \\
    -H "X-API-Key: sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ"
"""

import requests
import os
import uuid
import time

API_BASE = "https://api.666082.xyz/v1"
API_KEY = "sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ"


def get_upload_headers():
    """返回文件上传用的请求头。
    
    注意: 不设 Content-Type，requests 会自动设为 multipart/form-data。
    如果在 session 层预置 Content-Type: application/json 会阻止此自动切换。
    """
    return {
        "X-API-Key": API_KEY,
        "X-Ca-Timestamp": str(int(time.time() * 1000)),
        "X-Ca-Nonce": str(uuid.uuid4()),
    }


def get_json_headers():
    """返回 JSON 请求用的请求头。
    
    用于 POST JSON body、GET 查询等不需要文件上传的请求。
    """
    return {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
        "X-Ca-Timestamp": str(int(time.time() * 1000)),
        "X-Ca-Nonce": str(uuid.uuid4()),
    }


def calibrate(srt_file, txt_file, output_dir="test_output"):
    """完整的字幕校准流程：上传 → 启动处理 → 轮询 → 保存 LRC
    
    Args:
        srt_file: SRT 字幕文件路径
        txt_file: TXT 文稿文件路径
        output_dir: LRC 输出目录（默认 test_output）
    
    Returns:
        dict: {"task_id": str, "saved_files": [str]} 或 {"error": str}
    """
    # 注意：session 不预置 Content-Type，否则 file upload 时 requests 无法自动切换 multipart
    session = requests.Session()
    session.headers.update(get_upload_headers())

    # Step 1: 上传文件
    # 后端使用 files 字段名接收多个文件（通过 .srt/.txt 扩展名区分）
    file_objs = {}
    for path, label in [(srt_file, "srt"), (txt_file, "txt")]:
        if os.path.exists(path):
            file_objs[label] = (os.path.basename(path), open(path, "rb"), "application/octet-stream")
        else:
            return {"error": f"文件不存在: {path}"}

    try:
        upload_resp = session.post(
            f"{API_BASE}/api/upload_analyze",
            files=[("files", file_objs["srt"]), ("files", file_objs["txt"])],
            timeout=60
        )
    finally:
        for f in file_objs.values():
            f[1].close()

    if upload_resp.status_code != 200:
        return {"error": f"上传失败: {upload_resp.text}"}

    upload_data = upload_resp.json()
    if "task_id" not in upload_data:
        return {"error": f"上传返回格式异常: {upload_data}"}

    task_id = upload_data["task_id"]

    # Step 2: 启动校准
    process_resp = session.post(
        f"{API_BASE}/api/start_process",
        json={
            "key": API_KEY,
            "task_id": task_id,
        },
        headers=get_json_headers(),
        timeout=30
    )

    if process_resp.status_code != 200:
        return {"error": f"启动处理失败: {process_resp.text}"}

    # Step 3: 轮询状态直到完成
    # 后端返回的 state 字段为 "processing" → "completed" / "error"
    saved_files = []
    for attempt in range(60):
        status_resp = session.get(
            f"{API_BASE}/api/status/{task_id}",
            timeout=15
        )
        if status_resp.status_code != 200:
            time.sleep(2)
            continue

        status_data = status_resp.json()
        state = status_data.get("status", status_data.get("state", ""))

        if state == "completed":
            # 优先从 results[] 取 LRC 内容（新版格式）
            results = status_data.get("results", [])
            for r in results:
                if r.get("type") == "LRC" and r.get("content"):
                    os.makedirs(output_dir, exist_ok=True)
                    raw_name = r.get("name", os.path.splitext(os.path.basename(srt_file))[0])
                    name = os.path.splitext(raw_name)[0]  # 去掉可能的 .lrc 后缀
                    lrc_path = os.path.join(output_dir, f"{name}.lrc")
                    with open(lrc_path, "w", encoding="utf-8") as f:
                        f.write(r["content"])
                    saved_files.append(lrc_path)

            # 兼容旧格式：直接取 lrc_content 字段
            if not saved_files:
                lrc_content = status_data.get("lrc_content") or status_data.get("result", "")
                if lrc_content:
                    os.makedirs(output_dir, exist_ok=True)
                    base = os.path.splitext(os.path.basename(srt_file))[0]
                    lrc_path = os.path.join(output_dir, f"{base}.lrc")
                    with open(lrc_path, "w", encoding="utf-8") as f:
                        f.write(lrc_content)
                    saved_files.append(lrc_path)

            # 读取内容匹配校验结果
            accuracy_results = status_data.get("accuracy_results", [])
            abnormal_files = [a["file"] for a in accuracy_results if a["status"] == "abnormal"]
            if abnormal_files:
                print("⚠️ 以下文件状态异常，请检查原字幕及原始文稿是否缺失或错位:")
                for f in abnormal_files:
                    print(f"   - {f}")

            return {"task_id": task_id, "saved_files": saved_files, "accuracy_results": accuracy_results}

        elif state in ("failed", "error"):
            return {"task_id": task_id, "error": status_data.get("error", status_data.get("message", "处理失败")), "accuracy_results": []}

        time.sleep(2)

    return {"task_id": task_id, "error": "超时"}




def get_status(task_id):
    """查询任务状态"""
    resp = requests.get(
        f"{API_BASE}/api/status/{task_id}",
        headers=get_json_headers(),
        timeout=15
    )
    return resp.json() if resp.status_code == 200 else None
