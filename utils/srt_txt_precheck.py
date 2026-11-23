#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SRT/TXT 文本相似度预检（Python 版，供 Agent 直接调用）
=====================================================================
与前端 similarity.js 算法同源移植（归一化、3-gram Dice 闸门、Myers 线性空间
中点分割对齐、缺口判档逻辑逐位一致），用于 Agent 在调用校准 API 前对
「SRT 字幕 + 同名 TXT 文稿」输入组做预检。

【重要背景】为什么需要预检
    前端在校准开始前会用同一套算法给每个文件对算一个"重合度"并分四档染色。
    颜色代表两类问题：
      ① 字符重合度低 → 错字/改稿太多；
      ② 整句级差异（连续 ≥10 字对不上）→ 多读/漏读/整段缺失。
    算法无法区分"该处差异是阿拉伯数字、英文单词的写法差异"（这类可放行）
    与"真实的多读漏读"（这类必须处理），所以把缺口位置和两侧原文一并返回，
    由 Agent / 人工做最终判断。

【人工判断辅助（与前端图例口径一致）】
    如果某个差异位置两侧原文附近是阿拉伯数字、英文单词（典型场景：一侧用
    阿拉伯数字、另一侧用中文数字；或专有名词的英文写法不同），可以忽略该处
    提示，正常开始校准。
    否则说明字幕多读或漏读了内容：
      · 字幕多读 → 需剔除多读的音频段并重新生成 SRT，或删掉对应字幕条；
      · 字幕漏读 → 需补齐漏读的音频内容，或核对 TXT 是否混入了未朗读的文字
        （如章节说明、旁白注释），必要时改 TXT。

【CLI 参数】
    位置参数（成对出现，可多组）:
        srt1 txt1 [srt2 txt2 ...]
            每两个文件为一组：<字幕文件> <文稿文件>。
            字幕仅支持 .srt（自动识别）；文稿固定按纯文本口径处理。
            注意：第二个文件永远按 TXT 口径归一化——不要把两个 SRT 当一组，
            那会得到"疑似配错文件"，属预期语义而非 bug。

    --dir <目录>
        目录模式：扫描目录内文件，按同名（去扩展名、忽略大小写）把
        .srt 与 .txt 自动配对，等价于逐组传入。

    --brief
        精简输出：每对一行 "<srt文件名>  <summary>"，便于快速浏览；
        默认输出完整 JSON。

【输出格式（JSON，stdout，UTF-8，ensure_ascii=False）】
    顶层是数组，每组文件一个对象。字段如下：

    files       {"srt": 字幕文件名, "txt": 文稿文件名}
    state       "done"     正常完成比对（含发现整句差异的情况）
                "mismatch" 内容基本对不上（dice<45% 或对齐超限），疑似配错文件
                "empty"    至少一个文件归一化后为空（只含标点/空白）
                "error"    文件读取失败（附 error 字段）
    pct         重合度数值（0~100，保留 1 位小数；= 2*lcs/(两文本总字数)*100）
    pct_text    格式化文本，如 "97.6%"
    level       档位：1=绿 2=琥珀 3=橙 4=红 0=未计算（与前端四色一致）
    label       档位标签（"内容一致"/"轻微差异"/"需核对差异"/"内容不符"/
                "多处整句差异"/"整段明显缺失"/"有整句差异"）
    advice      建议动作（"可直接校准"/"建议抽查"/"先修字幕"/"建议换文件"）
    basis       判档依据："pct"=按重合度分档；"struct"=因整句差异压档
                （summary 前会带 "[整句差异压档]" 前缀）
    stats       { norm_a:    字幕归一化后字数
                  norm_b:    文稿归一化后字数
                  dice:      3-gram Dice 重合度（%）
                  lcs:       最长公共子序列字数（mismatch/empty 时为 null）
                  gap_count: 整句级差异数（连续 ≥10 字未匹配片段数）
                  gap_chars: 所有整句差异合计字数
                  max_run:   最长一处差异的字数
                  aborted:   对齐是否超出搜索上限 }
    gaps        差异明细数组（最多列 3 组，其余计入 gap_details_hidden）。
                每组字段：
                  index      第几处（1 起）
                  a_len/b_len/len   字幕侧缺字数 / 文稿侧缺字数 / 取较大者
                  type       "srt_extra"=字幕有文稿无（多读）
                             "txt_extra"=文稿有字幕无（漏读）
                             "both"     =两侧均有差异（替换/改写）
                  direction  中文方向提示（"疑似字幕多读"/"疑似字幕漏读"/""）
                  cue_start/cue_end/time   字幕条号区间与起始时间（字幕侧无
                             内容时锚到对齐恢复点，即缺口后的第一条）
                  anchor     人类可读位置串，如 "第 32 条（00:01:12）前后"
                  srt_text   该处字幕原文（保留标点与换行，单条超 60 字中间
                             截断加 …；字幕侧无内容时为空串）
                  txt_text   该处文稿原文（按句锚定，保留标点；文稿侧无内容
                             时为空串；切句口径对不上时整组不给对照）
    gap_details_hidden  未列出的差异处数（gap_count - 已列组数）
    summary     单行摘要（--brief 的每行内容），含位置列表

【档位与建议处理方案（Agent 决策参考）】
    lv1 绿  ≥90% 且无整句差异（内容一致 · 可直接校准）
            → 直接调用校准 API，无需处理。
    lv2 琥珀 80–90%，或 ≥90% 但有 1 处整句差异（建议抽查）
            → 可继续校准，但建议先看 gaps：若差异处是数字/英文写法差异，
              直接放行；若确认多读/漏读，按上面的"人工判断辅助"处理。
    lv3 橙  60–80%（需核对差异 · 先修字幕）
            → 错字/改稿较多，建议先修 SRT 再校准；校准结果可信度低。
    lv4 红  <60%，或 ≥2 处整句差异，或缺口合计 ≥ 较短文本 10%
            （多处整句差异/整段明显缺失/内容不符 · 先核对字幕/建议换文件）
            → 禁止直接校准。逐组检查 gaps 的原文对照：
              数字/英文写法差异可放行；真实多读漏读必须先剔除音频或修 TXT；
              state=mismatch（dice 极低）直接换文件。

【退出码（供脚本/Agent 无需解析输出即可分流）】
    0 = 全部绿档（state=done 且 level=1）
    1 = 存在琥珀/橙/红档，或 mismatch / empty / error
    2 = 用法错误或目录无可配对文件

【已知口径说明】
    · 百分比、缺口字数、条号锚点与前端浮层完全一致，可互相印证；
    · "12 字"只统计缺口本体，缺口两侧的零散字符若在别处对上会被挪走，
      实际肉眼缺失范围可能略大于 len；
    · 文稿切句遇源头引号打错（如右引号写成左引号）会熔断强制断句，
      避免粘出巨句，此时对照句可能比真实句子长；
    · 刻意不做的：不给"修复建议文案"、不改任何文件——判断与处置由 Agent/人做。

【示例】
    $ python srt_txt_precheck.py 字幕A.srt 文稿A.txt --brief
    字幕A.srt  [整句差异压档] 重合 97.6% ｜ 4 处整句差异 ｜ 最长 24 字 → 先核对字幕；位置：第 1–5 条（00:00:00）、第 6–7 条（00:00:06）、第 32 条（00:01:12）前后 等 4 处

    $ python srt_txt_precheck.py --dir ./待检目录
    [
      {
        "files": { "srt": "字幕B.srt", "txt": "文稿B.txt" },
        "state": "done",
        "pct": 96.0, "pct_text": "96.0%",
        "level": 2, "label": "有整句差异", "advice": "建议抽查", "basis": "struct",
        "stats": { "norm_a": 28894, "norm_b": 28925, "dice": 96.2, "lcs": 27787,
                    "gap_count": 1, "gap_chars": 10, "max_run": 10, "aborted": false },
        "gaps": [
          { "index": 1, "a_len": 8, "b_len": 10, "len": 10,
            "type": "both", "direction": "",
            "cue_start": 1058, "cue_end": 1059, "time": "00:24:23",
            "anchor": "第 1058–1059 条（00:24:23）",
            "srt_text": "<字幕原文（保留标点与换行）>",
            "txt_text": "<文稿原文（保留标点）>" }
        ],
        "gap_details_hidden": 0,
        "summary": "[整句差异压档] 重合 96.0% ｜ 1 处整句差异 ｜ 最长 10 字 → 建议抽查；位置：第 1058–1059 条（00:24:23）"
      }
    ]
    （↑ srt_text / txt_text 为该处两侧原文，格式示意；若差异处为数字写法差异，
      Agent 应按"人工判断辅助"放行）
"""

import argparse
import json
import os
import re
import sys
import unicodedata

# ── 默认配置（与 similarity.js DEFAULTS 完全一致）────────────────────
DEFAULTS = {
    "ngram": 3,
    "decimals": 1,
    "gapMin": 10,
    "gapHardPct": 10,
    "gapHardCount": 2,
    "mismatchDice": 45,
    "alignCapRatio": 0.16,
    "bands": [
        {"min": 90, "level": 1, "label": "内容一致", "advice": "可直接校准"},
        {"min": 80, "level": 2, "label": "轻微差异", "advice": "建议抽查"},
        {"min": 60, "level": 3, "label": "需核对差异", "advice": "先修字幕"},
        {"min": 0,  "level": 4, "label": "内容不符", "advice": "建议换文件"},
    ],
}

# ── 结构识别正则（与 similarity.js 同名常量一一对应）──────────────────
RE_TS_LINE = re.compile(r"[ \t]*(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?[ \t]*-->[^\n]*")
RE_INDEX_LINE = re.compile(r"[ \t]*\d{1,6}[ \t]*")
RE_LRC_TAG = re.compile(r"\[\d{1,2}:\d{1,2}(?::\d{1,2})?(?:[.:]\d{1,3})?\]")
RE_LRC_META = re.compile(r"[ \t]*\[(ti|ar|al|by|offset|re|ve|id|length|la|tool|encoder)[:=][^\]]*\][ \t]*", re.I)
RE_ASS_TAG = re.compile(r"\{[^{}]*\}")
RE_HTML_TAG = re.compile(r"<[^<>]{0,120}>")
RE_VTT_HEADER = re.compile(r"[ \t]*(WEBVTT|NOTE|STYLE|REGION)[ \t]*", re.I)
RE_BRACKET_ANNOTATION = re.compile(r"[\[【（(][^\]】）)]{0,40}[\]】）)]")

CMP_MAX_BLOCKS = 3   # 对照块最多列 3 组，其余写“另有 N 处”
CMP_CUE_MAX = 60     # 单条字幕超 60 字中间截断
TXT_SEG_FUSE = 60    # 文稿切句熔断：引号未闭合累计超 60 字强制断句


def detect_kind(raw):
    """仅区分 SRT 与纯文稿（2026-11-23 起不再支持 LRC）"""
    s = raw or ""
    if "-->" in s:
        return "srt"
    return "txt"


def strip_subtitle_noise(raw):
    """剔除字幕结构信息（序号行/时间轴行/VTT头/ASS与HTML标签/LRC标签），只留文本行"""
    lines = re.sub(r"\r\n?", "\n", raw or "").split("\n")
    out = []
    for i, line in enumerate(lines):
        t = line.strip()
        if not t:
            continue
        if RE_VTT_HEADER.fullmatch(t):
            continue
        if RE_TS_LINE.fullmatch(t):
            continue
        if RE_LRC_META.fullmatch(t):
            continue
        if RE_INDEX_LINE.fullmatch(t):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and RE_TS_LINE.fullmatch(lines[j].strip()):
                continue
        out.append(t)
    text = "\n".join(out)
    text = RE_LRC_TAG.sub(" ", text)
    text = RE_ASS_TAG.sub("", text)
    text = RE_HTML_TAG.sub("", text)
    return text


def _keep(ch):
    # \p{L} + \p{N}：Unicode 类别以 L / N 开头的字符
    return unicodedata.category(ch)[0] in ("L", "N")


def _filter_keep(s):
    return "".join(ch for ch in s if _keep(ch))


def normalize_line(s):
    s = unicodedata.normalize("NFKC", s)
    return _filter_keep(s).lower()


def normalize(raw, kind="auto"):
    if raw is None:
        return ""
    s = (raw or "").replace("\ufeff", "")
    s = re.sub(r"\r\n?", "\n", s)
    k = kind if kind != "auto" else detect_kind(s)
    if k == "srt":
        s = strip_subtitle_noise(s)
    s = unicodedata.normalize("NFKC", s)
    return _filter_keep(s).lower()


def parse_ts_seconds(t):
    m = re.search(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?", t or "")
    if not m:
        return None
    h = int(m.group(1)) if m.group(1) else 0
    return h * 3600 + int(m.group(2)) * 60 + int(m.group(3))


def normalize_with_cues(raw):
    """归一化文本 + 每个字所属字幕序号映射（字幕序号按时间轴行计数）"""
    empty = {"text": "", "cue_of": [], "cues": []}
    if raw is None:
        return empty
    s0 = (raw or "").replace("\ufeff", "")
    s0 = re.sub(r"\r\n?", "\n", s0)
    kind = detect_kind(s0)
    if kind != "srt":          # 仅支持 SRT（2026-11-23 移除 LRC 支持）
        return empty

    lines = s0.split("\n")
    text_parts = []
    cue_of = []
    cues = []
    cue_no = 0
    for i, line in enumerate(lines):
        t = line.strip()
        if not t or RE_VTT_HEADER.fullmatch(t):
            continue
        if RE_TS_LINE.fullmatch(t):
            cue_no += 1
            cues.append({"no": cue_no, "time": parse_ts_seconds(t)})
            continue
        if RE_INDEX_LINE.fullmatch(t):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and RE_TS_LINE.fullmatch(lines[j].strip()):
                continue  # 序号行
        clean = normalize_line(t)
        for _ in clean:
            cue_of.append(cue_no if cue_no else 0)
        text_parts.append(clean)
    return {"text": "".join(text_parts), "cue_of": cue_of, "cues": cues}


# ── 字符 n-gram Dice（31 位滚动哈希，与 JS 实现逐位一致）──────────────
def count_grams(s, n):
    grams = {}
    length = len(s)
    if length < n:
        return grams, 0
    head = 131 ** (n - 1)
    h = 0
    for j in range(n):
        h = (h * 131 + ord(s[j])) & 0x7FFFFFFF
    grams[h] = 1
    for i in range(1, length - n + 1):
        h = (((h - ord(s[i - 1]) * head) & 0x7FFFFFFF) * 131 + ord(s[i + n - 1])) & 0x7FFFFFFF
        grams[h] = grams.get(h, 0) + 1
    return grams, length - n + 1


def similarity_dice(a, b, ngram=3):
    s1, s2 = a or "", b or ""
    if not s1 and not s2:
        return None
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    n = max(1, min(ngram, len(s1), len(s2)))
    ga, ta = count_grams(s1, n)
    gb, tb = count_grams(s2, n)
    small, big = (ga, gb) if len(ga) <= len(gb) else (gb, ga)
    other = gb if small is ga else ga
    overlap = 0
    for key, cnt in small.items():
        o = other.get(key)
        if o:
            overlap += min(cnt, o)
    total = ta + tb
    return (2 * overlap) / total if total else 0.0


# ── Myers O(ND) 线性空间中点分割对齐（与 JS alignStats 逐位一致）──────
_CAP = object()
_NONE = object()


def align_stats(a, b, gap_min=DEFAULTS["gapMin"], cap_ratio=DEFAULTS["alignCapRatio"]):
    str_a, str_b = a or "", b or ""
    n_a, n_b = len(str_a), len(str_b)
    regions = []
    state = {"lcs": 0, "aborted": False}
    cap_d = max(300, int((n_a + n_b) * cap_ratio))

    def bisect(a0, a1, b0, b1):
        n, m = a1 - a0, b1 - b0
        max_d = -(- (n + m) // 2)          # ceil((n+m)/2)
        v_offset = max_d
        v_len = 2 * max_d + 2
        v1 = [-1] * v_len
        v2 = [-1] * v_len
        v1[v_offset + 1] = 0
        v2[v_offset + 1] = 0
        delta = n - m
        front = (delta % 2 != 0)
        k1start = k1end = k2start = k2end = 0

        for d in range(max_d):
            if d >= cap_d:
                return _CAP
            k1 = -d + k1start
            while k1 <= d - k1end:
                k1o = v_offset + k1
                if k1 == -d or (k1 != d and v1[k1o - 1] < v1[k1o + 1]):
                    x1 = v1[k1o + 1]
                else:
                    x1 = v1[k1o - 1] + 1
                y1 = x1 - k1
                while x1 < n and y1 < m and str_a[a0 + x1] == str_b[b0 + y1]:
                    x1 += 1
                    y1 += 1
                v1[k1o] = x1
                if x1 > n:
                    k1end += 2
                elif y1 > m:
                    k1start += 2
                elif front:
                    k2o = v_offset + delta - k1
                    if 0 <= k2o < v_len and v2[k2o] != -1:
                        x2 = n - v2[k2o]
                        if x1 >= x2:
                            return (a0 + x1, b0 + y1)
                k1 += 2
            k2 = -d + k2start
            while k2 <= d - k2end:
                k2o = v_offset + k2
                if k2 == -d or (k2 != d and v2[k2o - 1] < v2[k2o + 1]):
                    x2 = v2[k2o + 1]
                else:
                    x2 = v2[k2o - 1] + 1
                y2 = x2 - k2
                while x2 < n and y2 < m and str_a[a1 - x2 - 1] == str_b[b1 - y2 - 1]:
                    x2 += 1
                    y2 += 1
                v2[k2o] = x2
                if x2 > n:
                    k2end += 2
                elif y2 > m:
                    k2start += 2
                elif not front:
                    k1o = v_offset + delta - k2
                    if 0 <= k1o < v_len and v1[k1o] != -1:
                        x1 = v1[k1o]
                        y1 = x1 - (k1o - v_offset)   # 前向坐标：由 k1 线重算（不能沿用反向 y2）
                        x2abs = n - x2
                        if x1 >= x2abs:
                            return (a0 + x1, b0 + y1)
                k2 += 2
        return _NONE

    def walk(a0, a1, b0, b1):
        while a0 < a1 and b0 < b1 and str_a[a0] == str_b[b0]:
            a0 += 1
            b0 += 1
            state["lcs"] += 1
        s = 0
        while a1 - s > a0 and b1 - s > b0 and str_a[a1 - 1 - s] == str_b[b1 - 1 - s]:
            s += 1
        na, nb = a1 - s - a0, b1 - s - b0
        if na > 0 or nb > 0:
            if state["aborted"]:
                regions.append((na, nb, a0, b0))
            else:
                mid = bisect(a0, a0 + na, b0, b0 + nb)
                if mid is _CAP:
                    state["aborted"] = True
                    regions.append((na, nb, a0, b0))
                elif (mid is _NONE
                      or (mid[0] <= a0 and mid[1] <= b0)
                      or (mid[0] >= a0 + na and mid[1] >= b0 + nb)):
                    regions.append((na, nb, a0, b0))
                else:
                    walk(a0, mid[0], b0, mid[1])
                    walk(mid[0], a0 + na, mid[1], b0 + nb)
        state["lcs"] += s

    if n_a == 0 or n_b == 0:
        return {"lcs": 0, "gaps": [], "gap_count": 0, "gap_chars": 0,
                "max_run": 0, "aborted": True}
    walk(0, n_a, 0, n_b)

    gap_count = gap_chars = max_run = 0
    gaps = []
    for la, lb, a_start, b_start in regions:
        length = max(la, lb)
        if length >= gap_min:
            gap_count += 1
            gap_chars += length
            if length > max_run:
                max_run = length
            gaps.append((la, lb, a_start, b_start))
    lcs = None if state["aborted"] else state["lcs"]
    return {"lcs": lcs, "gaps": gaps, "gap_count": gap_count, "gap_chars": gap_chars,
            "max_run": max_run, "aborted": state["aborted"]}


# ── 缺口 → 两侧原文对照（锚点法，与前端 tooltipHtml 数据源一致）───────
def _ts_short(t):
    m = re.search(r"(\d{2}):(\d{2}):(\d{2})", t or "")
    return m.group(0) if m else ""


def _strip_tag(s):
    s = RE_ASS_TAG.sub("", s or "")
    return RE_HTML_TAG.sub("", s)


def _cut_mid(text, max_len):
    if not text or len(text) <= max_len:
        return text
    keep = max_len - 1
    return text[: -(-keep // 2)] + "…" + text[len(text) - keep // 2:]


def srt_cue_list(raw):
    """按空行切块取 序号/时间轴/正文（正文保留原换行与原标点）"""
    blocks = re.split(r"\n\s*\n", re.sub(r"\r", "", raw or ""))
    out = []
    for bk in blocks:
        lines = bk.split("\n")
        ti = -1
        for i in range(min(len(lines), 3)):
            if re.search(r"\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}\s*-->", lines[i]):
                ti = i
                break
        if ti < 0:
            continue
        no = int(lines[ti - 1]) if ti > 0 and re.fullmatch(r"\s*\d+\s*", lines[ti - 1]) else len(out) + 1
        body = "\n".join(lines[ti + 1:])
        out.append({"no": no, "time": _ts_short(lines[ti]),
                    "text": _strip_tag(body).strip("\n")})
    return out


def txt_seg_list(raw):
    """文稿按句切分（句末标点或换行断句；引号内不打断；未闭合超 60 字熔断）"""
    s = re.sub(r"\r", "", raw or "")
    end_re = re.compile(r"[。！？；…!?;]")
    segs = []
    buf = ""
    in_q = 0
    i = 0
    while i < len(s):
        ch = s[i]
        buf += ch
        if ch in "“「『":
            in_q += 1
        elif ch in "”」』" and in_q > 0:
            in_q -= 1
        if ch == "\n" or (end_re.match(ch) and (in_q == 0 or len(buf) > TXT_SEG_FUSE)):
            while i + 1 < len(s) and (end_re.match(s[i + 1]) or s[i + 1] in "”」』\n"):
                i += 1
                buf += s[i]
            segs.append(buf)
            buf = ""
        i += 1
    if buf:
        segs.append(buf)
    return segs


def cmp_gap_details(sub_raw, txt_raw, a, b, al):
    """把每个缺口反查回两侧原文 + 字幕条号锚点。口径对不上时返回 None（宁缺勿错）。"""
    if not a or not b or not al["gaps"]:
        return None
    nw = normalize_with_cues(sub_raw)
    if not nw or nw["text"] != a or len(nw.get("cue_of", [])) != len(a):
        return None
    cues = srt_cue_list(sub_raw)
    total_cues = len(cues)

    def cue_of(p):
        i = max(0, min(len(nw["cue_of"]) - 1, p))
        return nw["cue_of"][i] or 0

    # 文稿句表 → 归一化区间（按长度累加，必须与 b 完全等长才可信）
    segs = txt_seg_list(txt_raw)
    seg_range = []
    off = 0
    for k, seg in enumerate(segs):
        seg_len = len(normalize(seg, "txt"))
        if seg_len > 0:
            seg_range.append((k, off, off + seg_len))
            off += seg_len
    if off != len(b):
        return None

    def seg_at(p):
        lo, hi, ans = 0, len(seg_range) - 1, 0
        while lo <= hi:
            mid = (lo + hi) // 2
            _, s0, e0 = seg_range[mid]
            if p < s0:
                hi = mid - 1
            elif p >= e0:
                ans = mid
                lo = mid + 1
            else:
                return mid
        return ans

    details = []
    for gi, (la, lb, as_, bs) in enumerate(al["gaps"][:CMP_MAX_BLOCKS]):
        resume_cue = cue_of(as_)
        c1 = resume_cue if la > 0 else 0
        c2 = cue_of(as_ + la - 1) if la > 0 else 0
        if c1 and c2 and c1 > c2:
            c1, c2 = c2, c1

        srt_text = ""
        if la > 0 and c1:
            parts = []
            for c in range(c1, c2 + 1):
                it = cues[c - 1] if 0 <= c - 1 < total_cues else None
                if it and it["text"]:
                    parts.append(_cut_mid(it["text"], CMP_CUE_MAX))
            srt_text = "\n".join(parts)

        txt_text = ""
        if lb > 0 and seg_range:
            s1, s2 = seg_at(bs), seg_at(bs + lb - 1)
            for k in range(min(s1, s2), max(s1, s2) + 1):
                txt_text += re.sub(r"^[ \t]+", "", segs[seg_range[k][0]])
            txt_text = txt_text.strip("\n")

        if la > 0 and lb == 0:
            gap_type, direction = "srt_extra", "疑似字幕多读"
        elif la == 0 and lb > 0:
            gap_type, direction = "txt_extra", "疑似字幕漏读"
        else:
            gap_type, direction = "both", ""

        it_start = cues[c1 - 1] if (la > 0 and c1 and 0 <= c1 - 1 < total_cues) else None
        it_end = cues[c2 - 1] if (la > 0 and c2 and 0 <= c2 - 1 < total_cues) else None
        it_resume = cues[resume_cue - 1] if (la == 0 and lb > 0 and resume_cue and 0 <= resume_cue - 1 < total_cues) else None

        if it_start:
            no1, no2, t0 = it_start["no"], (it_end["no"] if it_end else it_start["no"]), it_start["time"]
            anchor = "第 %s 条%s" % (no1 if no2 == no1 else "%d–%d" % (no1, no2), "（%s）" % t0 if t0 else "")
        elif it_resume:
            no1, no2, t0 = it_resume["no"], it_resume["no"], it_resume["time"]
            anchor = "第 %d 条%s前后" % (no1, "（%s）" % t0 if t0 else "")
        else:
            no1 = no2 = 0
            t0 = ""
            anchor = "文稿开头附近"

        details.append({
            "index": gi + 1,
            "a_len": la, "b_len": lb, "len": max(la, lb),
            "type": gap_type, "direction": direction,
            "cue_start": no1, "cue_end": no2, "time": t0,
            "anchor": anchor,
            "srt_text": srt_text,
            "txt_text": txt_text,
        })
    return details


def format_pct(pct, decimals=DEFAULTS["decimals"]):
    if pct is None:
        return "—"
    return ("%%.%df%%%%" % decimals) % pct


def level_of(pct):
    if pct is None:
        return {"level": 0, "label": "未计算", "advice": ""}
    for band in DEFAULTS["bands"]:
        if pct >= band["min"]:
            return dict(band)
    return dict(DEFAULTS["bands"][-1])


def compare(srt_raw, txt_raw, srt_name="", txt_name=""):
    """比对一对文件，返回与前端 compareSubtitleAndTxt 同构的结果（外加缺口原文对照）"""
    cfg = DEFAULTS
    a = normalize(srt_raw, "auto")
    b = normalize(txt_raw, "txt")
    result = {
        "files": {"srt": srt_name, "txt": txt_name},
        "state": "done", "pct": None, "pct_text": "—",
        "level": 0, "label": "", "advice": "", "basis": "",
        "stats": {}, "gaps": [], "gap_details_hidden": 0, "summary": "",
    }

    if not a or not b:
        result["state"] = "empty"
        result["label"] = "无可比对内容"
        result["advice"] = "文件只含标点/空白"
        result["summary"] = "无可比对内容（只含标点/空白）"
        return result

    dice = similarity_dice(a, b, cfg["ngram"])
    dice_pct = None if dice is None else dice * 100
    base_stats = {"norm_a": len(a), "norm_b": len(b), "dice": None if dice_pct is None else round(dice_pct, 1)}

    if dice_pct is not None and dice_pct < cfg["mismatchDice"]:
        result["state"] = "mismatch"
        result["pct"] = dice_pct
        result["pct_text"] = format_pct(dice_pct)
        result["level"] = 4
        result["label"] = "内容不符"
        result["advice"] = "建议换文件"
        result["stats"] = dict(base_stats, lcs=None, gap_count=0, gap_chars=0, max_run=0, aborted=True)
        result["summary"] = "内容重合度极低（约 %s），两份文件基本对不上，疑似配错文件" % format_pct(dice_pct)
        return result

    al = align_stats(a, b)
    if al["aborted"]:
        result["state"] = "mismatch"
        result["pct"] = dice_pct
        result["pct_text"] = format_pct(dice_pct)
        result["level"] = 4
        result["label"] = "内容不符"
        result["advice"] = "建议换文件"
        result["stats"] = dict(base_stats, lcs=None, gap_count=al["gap_count"],
                               gap_chars=al["gap_chars"], max_run=al["max_run"], aborted=True)
        result["summary"] = "对齐超出搜索上限，两份文件基本对不上（dice 约 %s）" % format_pct(dice_pct)
        return result

    pct_raw = 2 * al["lcs"] / (len(a) + len(b)) * 100
    min_len = min(len(a), len(b))
    struct_level = 0
    if al["gap_count"] >= cfg["gapHardCount"]:
        struct_level = 4
    elif min_len > 0 and al["gap_chars"] / min_len * 100 >= cfg["gapHardPct"]:
        struct_level = 4
    elif al["gap_count"] >= 1:
        struct_level = 2

    lv = level_of(pct_raw)
    basis = "pct"
    if struct_level > lv["level"]:
        lv = level_of({4: 100, 2: 85}[struct_level])   # 按档位取对应 band
        lv["level"] = struct_level
        basis = "struct"
        if struct_level >= 4:
            lv["label"] = "多处整句差异" if al["gap_count"] >= 2 else "整段明显缺失"
            lv["advice"] = "先核对字幕"
        else:
            lv["label"] = "有整句差异"
            lv["advice"] = "建议抽查"
    elif al["gap_count"] >= 1:
        lv["label"] = "有整句差异"
        lv["advice"] = "建议抽查"

    result["pct"] = pct_raw
    result["pct_text"] = format_pct(pct_raw)
    result["level"] = lv["level"]
    result["label"] = lv["label"]
    result["advice"] = lv["advice"]
    result["basis"] = basis
    result["stats"] = dict(base_stats, lcs=al["lcs"], gap_count=al["gap_count"],
                           gap_chars=al["gap_chars"], max_run=al["max_run"], aborted=False)

    details = cmp_gap_details(srt_raw, txt_raw, a, b, al)
    if details is not None:
        result["gaps"] = details
        result["gap_details_hidden"] = max(0, al["gap_count"] - len(details))
    else:
        # 口径对不上时不给对照（宁缺勿错），但位置信息仍按前端 gapSpans 口径给出
        nw = normalize_with_cues(srt_raw)
        pos = []
        for la, lb, as_, bs in al["gaps"]:
            cue = (nw["cue_of"][min(as_, len(nw["cue_of"]) - 1)] or 0) if nw["cue_of"] else 0
            pos.append("第 %d 条" % cue if cue else "文稿开头附近")
        result["gaps"] = [{"anchor": p, "a_len": g[0], "b_len": g[1],
                           "len": max(g[0], g[1])} for p, g in zip(pos, al["gaps"])]

    summary = "重合 %s ｜ %d 处整句差异 ｜ 最长 %d 字 → %s" % (
        result["pct_text"], al["gap_count"], al["max_run"], lv["advice"])
    if al["gap_count"] == 0:
        summary = "重合 %s ｜ 无整句缺失或多余，差异为零散错字（属正常 ASR 噪声） → %s" % (
            result["pct_text"], lv["advice"])
    anchors = [g["anchor"] for g in result["gaps"] if g.get("anchor")]
    if anchors:
        summary += "；位置：" + "、".join(anchors[:4])
        if al["gap_count"] > len(anchors):
            summary += " 等 %d 处" % al["gap_count"]
    if basis == "struct":
        summary = "[整句差异压档] " + summary
    result["summary"] = summary
    return result


# ── 文件读取与 CLI ────────────────────────────────────────────────────
def read_text(path):
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def pair_files_in_dir(d):
    srt = {}
    txt = {}
    for name in os.listdir(d):
        base, ext = os.path.splitext(name)
        low = ext.lower()
        if low == ".srt":
            srt[base.strip().lower()] = os.path.join(d, name)
        elif low == ".txt":
            txt[base.strip().lower()] = os.path.join(d, name)
    return [(srt[k], txt[k]) for k in sorted(srt.keys() & txt.keys())]


def main(argv):
    parser = argparse.ArgumentParser(
        description="SRT/TXT 文本相似度预检（与前端 similarity.js 算法同源，供 Agent 调用）",
        epilog="完整文档（输出字段说明、档位与建议处理方案、人工判断辅助口径）见本文件头部 docstring；"
               "退出码：0=全部绿档 1=存在琥珀/橙/红或异常 2=用法错误。",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", help="成对的 <srt> <txt>，可多组")
    parser.add_argument("--dir", help="目录模式：按同名 .srt/.txt 自动配对")
    parser.add_argument("--brief", action="store_true", help="只输出单行摘要（每对一行）")
    args = parser.parse_args(argv)

    pairs = []
    if args.dir:
        pairs = pair_files_in_dir(args.dir)
        if not pairs:
            print("目录内没有可配对的 .srt + .txt 文件", file=sys.stderr)
            return 2
    else:
        if len(args.files) < 2 or len(args.files) % 2 != 0:
            print("用法: python srt_txt_precheck.py <srt1> <txt1> [<srt2> <txt2> ...]", file=sys.stderr)
            return 2
        for i in range(0, len(args.files), 2):
            pairs.append((args.files[i], args.files[i + 1]))

    results = []
    worst = 1
    for srt_path, txt_path in pairs:
        try:
            res = compare(read_text(srt_path), read_text(txt_path),
                          os.path.basename(srt_path), os.path.basename(txt_path))
        except OSError as e:
            res = {"files": {"srt": os.path.basename(srt_path), "txt": os.path.basename(txt_path)},
                   "state": "error", "error": str(e), "summary": "读取失败: %s" % e}
        results.append(res)
        lv = res.get("level", 0)
        if res.get("state") in ("mismatch", "empty", "error") or lv >= 2:
            worst = 1 if worst == 0 else worst
        elif res.get("state") == "done" and lv == 1:
            pass
    # 退出码：0=全部绿档；1=存在橙/红/异常
    has_abnormal = any(
        r.get("state") in ("mismatch", "empty", "error") or r.get("level", 0) >= 2
        for r in results
    )
    if args.brief:
        for r in results:
            print("%s  %s" % (r["files"]["srt"], r.get("summary", r.get("state"))))
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    return 1 if has_abnormal else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
