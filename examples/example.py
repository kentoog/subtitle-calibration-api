"""
字幕校准 API - Python 调用示例

在线体验: https://www.666082.xyz/
联系QQ: 136172378

输入格式: .srt 字幕文件 + .txt 文稿文件
输出格式: .lrc 歌词文件（可通过 lrc_srt_converter 转换为 .srt）
"""

import requests
import time
import os
import sys

API_BASE = "https://api.666082.xyz/v1"
API_KEY = "sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ"

POLL_INTERVAL = 5
MAX_POLL_TIME = 300


def get_headers():
    return {
        "X-API-Key": API_KEY,
        "X-Ca-Nonce": f"{int(time.time())}-{os.urandom(6).hex()}",
        "X-Ca-Timestamp": str(int(time.time() * 1000)),
    }


def verify_key():
    """
    验证 API Key 有效性及剩余配额（可选接口）
    """
    resp = requests.post(f"{API_BASE}/api/verify_key", headers=get_headers())
    data = resp.json()
    if data.get("valid"):
        print(f"✅ API Key 有效 | 今日已用: {data['usage_count']} | 剩余: {data['remaining']}")
    else:
        print(f"❌ API Key 无效: {data.get('error')}")
    return data


def calibrate(srt_path, txt_path, read_parentheses=True, output_dir="."):
    """
    完整的字幕校准流程：上传 → 启动 → 轮询 → 获取结果

    Args:
        srt_path: SRT 字幕文件路径
        txt_path: TXT 原始文稿路径
        read_parentheses: 是否朗读括号内容（默认 True）
        output_dir: 输出目录（默认当前目录）

    Returns:
        dict: 校准结果，包含 LRC 内容
    """
    print(f"📤 上传文件: {srt_path} + {txt_path}")

    with open(srt_path, "rb") as srt_f, open(txt_path, "rb") as txt_f:
        files = [
            ("files", (os.path.basename(srt_path), srt_f, "text/plain")),
            ("files", (os.path.basename(txt_path), txt_f, "text/plain")),
        ]
        resp = requests.post(
            f"{API_BASE}/api/upload_analyze", headers=get_headers(), files=files
        )

    if resp.status_code != 200:
        print(f"❌ 上传失败: {resp.status_code} {resp.text}")
        return None

    upload_data = resp.json()
    if "error" in upload_data:
        print(f"❌ 上传错误: {upload_data['error']}")
        return None

    task_id = upload_data["task_id"]
    print(f"✅ 上传成功 | task_id: {task_id}")
    print(f"   SRT 文件: {upload_data['srt_files']}")
    print(f"   TXT 文件: {upload_data['txt_files']}")

    print(f"🚀 启动校准任务...")
    resp = requests.post(
        f"{API_BASE}/api/start_process",
        headers={**get_headers(), "Content-Type": "application/json"},
        json={"task_id": task_id, "read_parentheses": read_parentheses},
    )

    if resp.status_code != 200:
        print(f"❌ 启动失败: {resp.status_code} {resp.text}")
        return None

    start_data = resp.json()
    if "error" in start_data:
        print(f"❌ 启动错误: {start_data['error']}")
        return None

    print(f"✅ 任务已启动 | 允许处理: {start_data['allowed_count']} 个文件")

    print(f"⏳ 等待校准完成...")
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        if elapsed > MAX_POLL_TIME:
            print(f"❌ 超时（{MAX_POLL_TIME}秒）")
            return None

        resp = requests.get(
            f"{API_BASE}/api/status/{task_id}", headers=get_headers()
        )
        data = resp.json()

        if data["status"] == "pending":
            print(f"   ⏳ 排队中...")
        elif data["status"] == "processing":
            current = data.get("current_file", "")
            print(f"   🔄 处理中: {data['completed']}/{data['total']}" + (f" — {current}" if current else ""))
        elif data["status"] == "completed":
            print(f"✅ 校准完成!")
            results = data.get("results", [])
            saved_files = []

            for r in results:
                if r["type"] == "LRC" and r.get("content"):
                    out_path = os.path.join(output_dir, r["name"])
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(r["content"])
                    saved_files.append(out_path)
                    print(f"   💾 已保存: {out_path}")
                elif r["type"] == "ERROR":
                    print(f"   ❌ {r['name']}: {r.get('error', '未知错误')}")

            return {"task_id": task_id, "results": results, "saved_files": saved_files}

        elif data["status"] == "error":
            print(f"❌ 任务错误: {data.get('error', '未知错误')}")
            return None

        time.sleep(POLL_INTERVAL)


def batch_calibrate(file_pairs, read_parentheses=True, output_dir="."):
    """
    批量校准多组 SRT + TXT 文件

    Args:
        file_pairs: [(srt_path, txt_path), ...] 文件对列表
        read_parentheses: 是否朗读括号内容
        output_dir: 输出目录

    Returns:
        list: 所有校准结果
    """
    print(f"📤 批量上传 {len(file_pairs)} 组文件")

    files = []
    for srt_path, txt_path in file_pairs:
        files.append(
            ("files", (os.path.basename(srt_path), open(srt_path, "rb"), "text/plain"))
        )
        files.append(
            ("files", (os.path.basename(txt_path), open(txt_path, "rb"), "text/plain"))
        )

    try:
        resp = requests.post(
            f"{API_BASE}/api/upload_analyze", headers=get_headers(), files=files
        )

        if resp.status_code != 200:
            print(f"❌ 上传失败: {resp.status_code} {resp.text}")
            return None

        upload_data = resp.json()
        if "error" in upload_data:
            print(f"❌ 上传错误: {upload_data['error']}")
            return None

        task_id = upload_data["task_id"]
        print(f"✅ 上传成功 | task_id: {task_id}")
        print(f"   SRT: {upload_data['srt_files']}")
        print(f"   TXT: {upload_data['txt_files']}")

        print(f"🚀 启动批量校准...")
        resp = requests.post(
            f"{API_BASE}/api/start_process",
            headers={**get_headers(), "Content-Type": "application/json"},
            json={"task_id": task_id, "read_parentheses": read_parentheses},
        )

        start_data = resp.json()
        if "error" in start_data:
            print(f"❌ 启动错误: {start_data['error']}")
            return None

        print(f"✅ 任务已启动 | 允许处理: {start_data['allowed_count']} 个文件")

        print(f"⏳ 等待校准完成...")
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > MAX_POLL_TIME:
                print(f"❌ 超时")
                return None

            resp = requests.get(
                f"{API_BASE}/api/status/{task_id}", headers=get_headers()
            )
            data = resp.json()

            if data["status"] == "completed":
                print(f"✅ 批量校准完成!")
                results = data.get("results", [])
                saved_files = []

                for r in results:
                    if r["type"] == "LRC" and r.get("content"):
                        out_path = os.path.join(output_dir, r["name"])
                        with open(out_path, "w", encoding="utf-8") as f:
                            f.write(r["content"])
                        saved_files.append(out_path)
                        print(f"   💾 已保存: {out_path}")
                    elif r["type"] == "ERROR":
                        print(f"   ❌ {r['name']}: {r.get('error')}")

                return {"task_id": task_id, "results": results, "saved_files": saved_files}

            elif data["status"] == "processing":
                current = data.get("current_file", "")
                print(f"   🔄 处理中: {data['completed']}/{data['total']}" + (f" — {current}" if current else ""))

            elif data["status"] == "error":
                print(f"❌ 任务错误: {data.get('error')}")
                return None

            time.sleep(POLL_INTERVAL)

    finally:
        for _, file_tuple in files:
            file_tuple[1].close()


if __name__ == "__main__":
    print("=" * 50)
    print("字幕校准 API - Python 示例")
    print("输入: .srt 字幕 + .txt 文稿")
    print("输出: .lrc 歌词")
    print("=" * 50)

    print("\n1. 验证 API Key（可选）...")
    verify_key()

    if len(sys.argv) >= 3:
        srt_file = sys.argv[1]
        txt_file = sys.argv[2]
        out_dir = sys.argv[3] if len(sys.argv) >= 4 else "."

        print(f"\n2. 校准文件: {srt_file} + {txt_file}")
        result = calibrate(srt_file, txt_file, output_dir=out_dir)

        if result:
            print(f"\n🎉 完成! 共保存 {len(result['saved_files'])} 个 LRC 文件")
            print("   如需 SRT 格式，可使用 utils/lrc_srt_converter.py 进行转换")
        else:
            print(f"\n💔 校准失败")
    else:
        print("\n用法: python example.py <srt文件> <txt文件> [输出目录]")
        print("示例: python example.py example.srt example.txt ./output")
