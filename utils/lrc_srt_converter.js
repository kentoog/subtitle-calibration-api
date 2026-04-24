/**
 * LRC ↔ SRT 格式转换工具函数
 *
 * 来源: SRT-LRC 字幕校准工具 (https://www.666082.xyz/)
 * 联系QQ: 136172378
 *
 * 功能:
 *   - lrcToSrt(lrcContent): LRC 歌词 → SRT 字幕
 *   - srtToLrc(srtContent): SRT 字幕 → LRC 歌词
 *   - parseSrt(content): 解析 SRT 内容为结构化数据
 *   - parseLrc(content): 解析 LRC 内容为结构化数据
 *   - formatSrtTime(ms): 毫秒 → SRT 时间格式
 *   - parseSrtTime(timeStr): SRT 时间格式 → 毫秒
 *   - clearPunctuation(text): 清除中文标点
 */

function lrcToSrt(lrcContent) {
    /**
     * 将 LRC 歌词格式转换为 SRT 字幕格式
     *
     * @param {string} lrcContent - LRC 格式字符串，如 "[00:05.23]歌词内容"
     * @returns {string} SRT 格式字符串
     *
     * @example
     * const lrc = "[00:00.50]第一句\n[00:05.23]第二句";
     * const srt = lrcToSrt(lrc);
     * // 1
     * // 00:00:00,500 --> 00:00:05,220
     * // 第一句
     * //
     * // 2
     * // 00:00:05,230 --> 00:00:08,230
     * // 第二句
     */
    const lines = lrcContent.split("\n");
    const srtLines = [];
    const parsedLines = [];

    for (const line of lines) {
        const match = line.match(/\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)/);
        if (match) {
            const minutes = parseInt(match[1]);
            const seconds = parseInt(match[2]);
            const milliseconds = match[3].padEnd(3, "0");
            const text = match[4].trim();

            if (text) {
                const totalMs =
                    minutes * 60 * 1000 + seconds * 1000 + parseInt(milliseconds);
                parsedLines.push({ totalMs, text });
            }
        }
    }

    for (let i = 0; i < parsedLines.length; i++) {
        const current = parsedLines[i];
        const next = parsedLines[i + 1];

        const startMs = current.totalMs;
        let endMs;

        if (next) {
            endMs = next.totalMs - 10;
            if (endMs <= startMs) {
                endMs = startMs + 1000;
            }
        } else {
            endMs = startMs + 3000;
        }

        const startTime = formatSrtTime(startMs);
        const endTime = formatSrtTime(endMs);

        srtLines.push(`${i + 1}`);
        srtLines.push(`${startTime} --> ${endTime}`);
        srtLines.push(current.text);
        srtLines.push("");
    }

    return srtLines.join("\n");
}

function srtToLrc(srtContent) {
    /**
     * 将 SRT 字幕格式转换为 LRC 歌词格式
     *
     * @param {string} srtContent - SRT 格式字符串
     * @returns {string} LRC 格式字符串
     *
     * @example
     * const srt = "1\n00:00:00,500 --> 00:00:05,220\n第一句";
     * const lrc = srtToLrc(srt);
     * // [00:00.50]第一句
     */
    const subs = parseSrt(srtContent);
    const lrcLines = [];

    for (const sub of subs) {
        const startMs = sub.start_ms;
        const minutes = Math.floor(startMs / 60000);
        const seconds = Math.floor((startMs % 60000) / 1000);
        const centiseconds = Math.floor((startMs % 1000) / 10);
        const timeTag = `[${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${String(centiseconds).padStart(2, "0")}]`;
        lrcLines.push(`${timeTag}${sub.text}`);
    }

    return lrcLines.join("\n");
}

function parseSrt(content) {
    /**
     * 解析 SRT 内容为结构化数据
     *
     * @param {string} content - SRT 格式字符串
     * @returns {Array<{index: number, start_ms: number, end_ms: number, text: string}>}
     */
    const subs = [];
    const pattern =
        /(\d+)\n(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\n$|\Z)/gs;
    let match;

    while ((match = pattern.exec(content)) !== null) {
        subs.push({
            index: parseInt(match[1]),
            start_ms: parseSrtTime(match[2]),
            end_ms: parseSrtTime(match[3]),
            text: match[4].trim(),
        });
    }

    return subs;
}

function parseLrc(content) {
    /**
     * 解析 LRC 内容为结构化数据
     *
     * @param {string} content - LRC 格式字符串
     * @returns {Array<{time_ms: number, text: string}>}
     */
    const lines = [];

    for (const line of content.split("\n")) {
        const match = line.match(/\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)/);
        if (match) {
            const minutes = parseInt(match[1]);
            const seconds = parseInt(match[2]);
            const milliseconds = match[3].padEnd(3, "0");
            const text = match[4].trim();

            if (text) {
                const totalMs =
                    minutes * 60 * 1000 + seconds * 1000 + parseInt(milliseconds);
                lines.push({ time_ms: totalMs, text });
            }
        }
    }

    return lines;
}

function formatSrtTime(ms) {
    /**
     * 毫秒数转换为 SRT 时间格式
     *
     * @param {number} ms - 毫秒数
     * @returns {string} "HH:MM:SS,mmm" 格式
     *
     * @example
     * formatSrtTime(3661500) // "01:01:01,500"
     */
    const h = Math.floor(ms / 3600000);
    ms %= 3600000;
    const m = Math.floor(ms / 60000);
    ms %= 60000;
    const s = Math.floor(ms / 1000);
    ms %= 1000;
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")},${ms.toString().padStart(3, "0")}`;
}

function parseSrtTime(timeStr) {
    /**
     * SRT 时间格式转换为毫秒数
     *
     * @param {string} timeStr - "HH:MM:SS,mmm" 或 "HH:MM:SS.mmm" 格式
     * @returns {number} 毫秒数
     *
     * @example
     * parseSrtTime("01:01:01,500") // 3661500
     */
    const parts = timeStr.replace(",", ".").split(":");
    const h = parseInt(parts[0]);
    const m = parseInt(parts[1]);
    const sMs = parts[2].split(".");
    const s = parseInt(sMs[0]);
    const ms = sMs.length > 1 ? parseInt(sMs[1]) : 0;
    return h * 3600000 + m * 60000 + s * 1000 + ms;
}

function clearPunctuation(text) {
    /**
     * 清除中文标点符号
     *
     * @param {string} text - 原始文本
     * @returns {string} 清除标点后的文本
     *
     * 清除范围: ，。！？、；：""''（）【】《》
     */
    return text.replace(/[，。！？、；：""''（）【】《》]/g, "");
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        lrcToSrt,
        srtToLrc,
        parseSrt,
        parseLrc,
        formatSrtTime,
        parseSrtTime,
        clearPunctuation,
    };
}
