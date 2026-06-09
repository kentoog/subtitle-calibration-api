"""
LRC ↔ SRT 格式转换工具函数

来源: SRT-LRC 字幕校准工具 (https://www.666082.xyz/)
联系QQ: 136172378

功能:
  - lrc_to_srt(lrc_content): LRC 歌词 → SRT 字幕
  - srt_to_lrc(srt_content): SRT 字幕 → LRC 歌词
  - parse_srt(content): 解析 SRT 内容为结构化数据
  - parse_lrc(content): 解析 LRC 内容为结构化数据
  - format_srt_time(ms): 毫秒 → SRT 时间格式
  - parse_srt_time(time_str): SRT 时间格式 → 毫秒
  - clear_punctuation(text): 清除中文标点
"""


def lrc_to_srt(lrc_content):
    """
    将 LRC 歌词格式转换为 SRT 字幕格式

    Args:
        lrc_content: LRC 格式字符串，如 "[00:05.23]歌词内容"

    Returns:
        str: SRT 格式字符串

    示例:
        >>> lrc = "[00:00.50]第一句\\n[00:05.23]第二句"
        >>> srt = lrc_to_srt(lrc)
        >>> print(srt)
        1
        00:00:00,500 --> 00:00:05,220
        第一句

        2
        00:00:05,230 --> 00:00:08,230
        第二句
    """
    import re

    lines = lrc_content.strip().split("\n")
    parsed_lines = []

    for line in lines:
        match = re.match(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)", line.strip())
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            milliseconds = match.group(3).ljust(3, "0")
            text = match.group(4).strip()

            if text:
                total_ms = minutes * 60 * 1000 + seconds * 1000 + int(milliseconds)
                parsed_lines.append({"total_ms": total_ms, "text": text})

    srt_lines = []
    for i, current in enumerate(parsed_lines):
        next_item = parsed_lines[i + 1] if i + 1 < len(parsed_lines) else None

        start_ms = current["total_ms"]
        if next_item:
            end_ms = next_item["total_ms"] - 10
            if end_ms <= start_ms:
                end_ms = start_ms + 1000
        else:
            end_ms = start_ms + 3000

        start_time = format_srt_time(start_ms)
        end_time = format_srt_time(end_ms)

        srt_lines.append(str(i + 1))
        srt_lines.append(f"{start_time} --> {end_time}")
        srt_lines.append(current["text"])
        srt_lines.append("")

    return "\n".join(srt_lines)


def srt_to_lrc(srt_content):
    """
    将 SRT 字幕格式转换为 LRC 歌词格式

    Args:
        srt_content: SRT 格式字符串

    Returns:
        str: LRC 格式字符串

    示例:
        >>> srt = "1\\n00:00:00,500 --> 00:00:05,220\\n第一句"
        >>> lrc = srt_to_lrc(srt)
        >>> print(lrc)
        [00:00.50]第一句
    """
    subs = parse_srt(srt_content)
    lrc_lines = []

    for sub in subs:
        start_ms = sub["start_ms"]
        minutes = start_ms // 60000
        seconds = (start_ms % 60000) // 1000
        centiseconds = (start_ms % 1000) // 10
        time_tag = f"[{minutes:02d}:{seconds:02d}.{centiseconds:02d}]"
        lrc_lines.append(f"{time_tag}{sub['text']}")

    return "\n".join(lrc_lines)


def parse_srt(content):
    """
    解析 SRT 内容为结构化数据

    Args:
        content: SRT 格式字符串

    Returns:
        list[dict]: 每条字幕包含 index, start_ms, end_ms, text
    """
    import re

    subs = []
    pattern = r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\n$|\Z)"
    matches = re.findall(pattern, content, flags=re.DOTALL)

    for match in matches:
        subs.append(
            {
                "index": int(match[0]),
                "start_ms": parse_srt_time(match[1]),
                "end_ms": parse_srt_time(match[2]),
                "text": match[3].strip(),
            }
        )

    return subs


def parse_lrc(content):
    """
    解析 LRC 内容为结构化数据

    Args:
        content: LRC 格式字符串

    Returns:
        list[dict]: 每行歌词包含 time_ms, text
    """
    import re

    lines = []
    for line in content.strip().split("\n"):
        match = re.match(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)", line.strip())
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            milliseconds = match.group(3).ljust(3, "0")
            text = match.group(4).strip()

            if text:
                total_ms = minutes * 60 * 1000 + seconds * 1000 + int(milliseconds)
                lines.append({"time_ms": total_ms, "text": text})

    return lines


def format_srt_time(ms):
    """
    毫秒数转换为 SRT 时间格式

    Args:
        ms: 毫秒数

    Returns:
        str: "HH:MM:SS,mmm" 格式

    示例:
        >>> format_srt_time(3661500)
        '01:01:01,500'
    """
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt_time(time_str):
    """
    SRT 时间格式转换为毫秒数

    Args:
        time_str: "HH:MM:SS,mmm" 或 "HH:MM:SS.mmm" 格式

    Returns:
        int: 毫秒数

    示例:
        >>> parse_srt_time("01:01:01,500")
        3661500
    """
    parts = time_str.replace(",", ".").split(":")
    h = int(parts[0])
    m = int(parts[1])
    s_ms = parts[2].split(".")
    s = int(s_ms[0])
    ms = int(s_ms[1]) if len(s_ms) > 1 else 0
    return h * 3600000 + m * 60000 + s * 1000 + ms


def clear_punctuation(text):
    """
    清除中文标点符号

    Args:
        text: 原始文本

    Returns:
        str: 清除标点后的文本

    清除范围: ，。！？、；：""''""''（）【】《》
    """
    import re

    return re.sub(r"[，。！？、；：\u201c\u201d\u2018\u2019\u201c\u201d\u2018\u2019\uff08\uff09\u3010\u3011\u300a\u300b]", "", text)


if __name__ == "__main__":
    lrc_sample = "[00:00.50]第一句歌词\n[00:05.23]第二句歌词\n[00:10.15]第三句歌词"

    print("=== LRC → SRT ===")
    srt_result = lrc_to_srt(lrc_sample)
    print(srt_result)

    print("\n=== SRT → LRC ===")
    lrc_result = srt_to_lrc(srt_result)
    print(lrc_result)

    print("\n=== 清除标点 ===")
    text_with_punct = "你好，世界！这是测试。"
    print(f"原文: {text_with_punct}")
    print(f"清除: {clear_punctuation(text_with_punct)}")
