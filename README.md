# 字幕校准 API - 音文精准对齐服务

> Subtitle Calibration API - Audio-Text Alignment Service

[![API Version](https://img.shields.io/badge/API-v1.0.0-blue.svg)](https://api.666082.xyz/v1)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Online-brightgreen.svg)](https://www.666082.xyz/)

🌐 **在线体验**: [https://www.666082.xyz/](https://www.666082.xyz/)

💬 **联系QQ**: 136172378

---

## 项目简介

字幕校准 API 是一个面向 TTS / 真人朗读音频的**音文精准对齐服务**。针对**有原始文稿**的音频场景，AI 自动将语音识别产生的 SRT 字幕与原始文稿逐字比对，校准识别偏差，确保输出文本与原文 **100% 一致**，同时精准对齐时间轴。

### 关键词

`字幕校准` `音文对齐` `音文校准` `字幕同步` `歌词对齐` `TTS字幕` `语音识别校准` `subtitle calibration` `audio-text alignment`

### 核心能力

| 能力 | 说明 |
|------|------|
| **绝对校准** | 基于原始文稿对 AI 识别字幕逐字校准，输出文本与原文 100% 一致 |
| **批量处理** | 最多 20 组文件同时校准，同名自动配对 |
| **精准拼接** | 多段 SRT 首尾相接，毫秒级平移对齐 |
| **格式转换** | 内置 LRC ↔ SRT 互转工具函数，开箱即用 |

### 适用场景

- ✅ **有原始文稿**的 TTS 合成音频字幕校准
- ✅ **有原始文稿**的真人朗读音频字幕校准
- ❌ **没有原始文稿**的音频字幕校准（不适用）

---

## 快速开始

### 1. 获取 API Key

本项目提供**免费 API Key**，每天限量 **1000 次请求**：

```
sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ
```

> 如需更高配额，请联系 QQ: 136172378

### 2. 三步完成校准

```
步骤1: 上传文件 → 步骤2: 启动校准 → 步骤3: 轮询结果
```

### 3. 最简示例 (Python)

```python
import requests
import time

API_BASE = "https://api.666082.xyz/v1"
API_KEY = "sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ"
HEADERS = {"X-API-Key": API_KEY}

# 步骤1: 上传 SRT + TXT 文件
with open("example.srt", "rb") as srt, open("example.txt", "rb") as txt:
    files = [("files", srt), ("files", txt)]
    resp = requests.post(f"{API_BASE}/api/upload_analyze", headers=HEADERS, files=files)
    task_id = resp.json()["task_id"]

# 步骤2: 启动校准
resp = requests.post(f"{API_BASE}/api/start_process",
    headers={**HEADERS, "Content-Type": "application/json"},
    json={"task_id": task_id, "read_parentheses": True})

# 步骤3: 轮询结果
while True:
    resp = requests.get(f"{API_BASE}/api/status/{task_id}", headers=HEADERS)
    data = resp.json()
    if data["status"] == "completed":
        for r in data["results"]:
            if r["type"] == "LRC":
                print(r["content"])
        break
    time.sleep(5)
```

---

## 文档目录

| 文件 | 说明 |
|------|------|
| [API.md](API.md) | 完整 API 接口文档（请求格式、参数、返回值、错误码） |
| [examples/](examples/) | Python / JavaScript 调用示例 |
| [utils/](utils/) | LRC↔SRT 转换工具函数（Python / JavaScript） |
| [LICENSE](LICENSE) | MIT 开源协议 |

---

## API 概览

| 接口 | 方法 | 说明 |
|------|------|------|
| `/v1/api/upload_analyze` | POST | 上传 SRT 字幕 + TXT 文稿 |
| `/v1/api/start_process` | POST | 启动校准任务 |
| `/v1/api/status/{task_id}` | GET | 查询任务状态与结果（返回 LRC 内容） |
| `/v1/api/verify_key` | POST | （可选）验证 API Key 及剩余配额 |

> 详见 [API.md](API.md)

---

## 输入输出格式

### 输入格式

| 类型 | 格式 | 说明 |
|------|------|------|
| 字幕文件 | `.srt` | 语音识别生成的 SRT 字幕文件 |
| 文稿文件 | `.txt` | 原始文稿，需包含规范标点 |

### 输出格式

| 类型 | 格式 | 说明 |
|------|------|------|
| 校准结果 | `.lrc` | LRC 歌词格式，时间轴精准对齐 |

### 格式转换

如需 SRT 格式，可使用本项目提供的转换工具：

```python
from utils.lrc_srt_converter import lrc_to_srt

srt_content = lrc_to_srt(lrc_content)
```

```javascript
const { lrcToSrt } = require('./utils/lrc_srt_converter.js');
const srtContent = lrcToSrt(lrcContent);
```

---

## 请求限制

| 项目 | 限制 |
|------|------|
| 免费配额 | 每天 1000 次请求 |
| IP 频率限制 | 同一 IP 每秒最多 1 次请求 |
| 单次最大文件数 | 40 个文件（最多 20 组配对） |
| 单文件字符数 | 100 ~ 20,000 字符 |
| 支持的输入格式 | `.srt`（字幕） + `.txt`（文稿） |
| 输出格式 | `.lrc`（歌词） |
| 文件配对规则 | 同名文件自动配对（如 `a.srt` + `a.txt`） |

---

## 前期准备

在使用本 API 前，您需要：

1. **准备 SRT 字幕文件** — 将原始音频通过语音识别工具转换为 `.srt` 格式
   - 推荐工具：FunASR（高精度开源模型）、MediaToolkit（B站有包，或站内搜索MediaToolkit）
   - 输出后缀必须为 `.srt`，无需手动修改内容

2. **准备 TXT 原始文稿** — 必须包含符合朗读习惯的标点符号
   - ✅ 推荐：`第一句，第二句。第三句！`（连续文本+标点 或 分行+标点）
   - ❌ 不适合：`第一句 第二句 第三句`（空格分隔，AI 无法识别句子边界）
   - ⚠️ 不推荐：分行无标点（缺少标点影响语气判断）

---

## 致谢

- 本项目 API 服务由 [666082.xyz](https://www.666082.xyz/) 提供云端运行支持
- 感谢所有开源语音识别与字幕处理工具的贡献者

---

## License

[MIT](LICENSE)
