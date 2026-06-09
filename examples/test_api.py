"""
API 调用测试脚本

测试内容:
  1. calibrate() 完整校准流程（上传 → 启动 → 轮询 → 保存 LRC）

测试文件:
  - SRT: 1.srt
  - TXT: 1.txt

依赖:
  example.py 中的 calibrate() 函数
"""

import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from example import calibrate

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRT_FILE = os.path.join(SCRIPT_DIR, r"1.srt")
TXT_FILE = os.path.join(SCRIPT_DIR, r"1.txt")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "test_output")


def test_calibrate():
    """测试完整的校准流程"""
    print("\n" + "=" * 60)
    print("测试: 完整校准流程")
    print("=" * 60)

    if not os.path.exists(SRT_FILE):
        print(f"❌ SRT 文件不存在: {SRT_FILE}")
        return False

    if not os.path.exists(TXT_FILE):
        print(f"❌ TXT 文件不存在: {TXT_FILE}")
        return False

    print(f"SRT 文件: {SRT_FILE}")
    print(f"TXT 文件: {TXT_FILE}")
    print(f"输出目录: {OUTPUT_DIR}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        result = calibrate(SRT_FILE, TXT_FILE, output_dir=OUTPUT_DIR)

        if result is None:
            print("❌ 校准失败: 返回值为 None")
            return False

        print(f"\n返回结果:")
        print(f"  task_id: {result.get('task_id')}")
        print(f"  saved_files: {result.get('saved_files')}")

        if result.get("saved_files"):
            print("\n✅ 校准成功，已保存 LRC 文件:")
            for f in result["saved_files"]:
                print(f"  - {f}")

                with open(f, "r", encoding="utf-8") as file:
                    content = file.read()
                    lines = content.strip().split("\n")[:5]
                    print(f"    前5行预览:")
                    for line in lines:
                        print(f"      {line}")
            return True
        else:
            print("⚠️ 校准完成但未保存文件")
            return False

    except Exception as e:
        print(f"❌ 校准异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "=" * 60)
    print("字幕校准 API 测试脚本")
    print("=" * 60)

    results = []

    results.append(("完整校准", test_calibrate()))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\n总计: {passed}/{total} 通过")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
