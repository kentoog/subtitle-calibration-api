# 字幕校准 API - 音文精准对齐服务

> Subtitle Calibration API — Audio-Text Alignment Service
>
> **English**: Text-driven SRT/LRC subtitle calibration API.  
> Free 1,000 requests/day, public API key included, no registration required.  
> [AI Function Call](AI_FUNCTION_CALL.json) ready for LLM / Agent integration.  
> 🇨🇳 中文文档见下方 ↓

[![API Version](https://img.shields.io/badge/API-v1.0.0-blue.svg)](https://api.666082.xyz/v1)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Online-brightgreen.svg)](https://www.666082.xyz/)

🌐 **在线体验**: [https://www.666082.xyz/](https://www.666082.xyz/)

💬 **联系QQ**: 136172378

> 🔑 **免费公共 API Key**: `sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ`
> 📊 **每日免费额度**: 1,000 次请求 / 天（北京时间 00:00 自动重置）
> 🚫 **无需注册、无需申请、开箱即用**

---

## 项目简介 

字幕校准 API 是一个面向 TTS / 真人朗读音频的**音文精准对齐服务**。针对**有原始文稿**的音频场景，AI 自动将语音识别产生的 SRT 字幕与原始文稿逐字比对，校准识别偏差，确保输出文本与原文 **100% 一致**，同时精准对齐时间轴。

### 关键词

`字幕校准` `音文对齐` `音文校准` `字幕同步` `歌词对齐` `TTS字幕` `语音识别校准` `subtitle calibration` `audio-text alignment`

### 核心能力

| 能力 | 说明 |
|------|------|
| **绝对校准** | 基于“原始文稿”对 AI 识别字幕逐字校准，输出字幕文本与原文 100% 一致，并对齐原始时间轴。 |
| **批量处理** | 最多 50 组文件同时校准（100 个文件），同名自动配对 |
| **精准拼接** | 多段 SRT 首尾相接，毫秒级平移对齐 |
| **格式转换** | 内置 LRC ↔ SRT 互转工具函数，开箱即用 |

### 适用场景

- ✅ **有原始文稿**的 TTS 合成音频字幕校准
- ✅ **有原始文稿**的真人朗读音频字幕校准
- ❌ **没有原始文稿**的音频字幕校准（不适用）

### 数据处理说明

#### 处理方式
上传的 SRT/TXT 文件仅用于字幕校准的**实时计算**处理，服务端**不存储**任何文件内容，处理完成后即丢弃，服务本身不具备存储能力。

#### 用户责任
用户应保证上传内容拥有合法权利，不得上传违法违规、危害国家安全、侵害他人合法权益或侵犯第三方知识产权的内容。

#### 免责声明
- 用户自行对上传内容及使用结果承担全部法律责任
- 本服务仅提供技术校准处理，**不构成法律、版权及任何专业领域建议**
- 因用户自身使用场景、文件格式、发布传播等产生的相关责任由用户自行承担
- 本服务仅提供技术计算，不对上传内容进行审核

#### 使用即同意
使用本服务并上传文件，即视为已阅读、知晓并同意上述数据处理规则及使用规范。

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

> ⚠️ **频率限制提示**：API 存在 1 次/秒的 IP 频率限制，各步骤之间需延时：
> - 上传 → 启动：≥ 1 秒
> - 启动 → 首次轮询：≥ 1 秒
> - 轮询间隔：≥ 5 秒

### 3. 最简示例 (Python)

```python
import requests
import time
import uuid

API_BASE = "https://api.666082.xyz/v1"
API_KEY = "sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ"

def headers():
    return {
        "X-API-Key": API_KEY,
        "X-Ca-Timestamp": str(int(time.time() * 1000)),
        "X-Ca-Nonce": str(uuid.uuid4()),
    }

# 步骤1: 上传 SRT + TXT 文件
with open("example.srt", "rb") as srt, open("example.txt", "rb") as txt:
    files = [("files", srt), ("files", txt)]
    resp = requests.post(f"{API_BASE}/api/upload_analyze", headers=headers(), files=files)
    task_id = resp.json()["task_id"]

time.sleep(1)  # 避免频率限制

# 步骤2: 启动校准
resp = requests.post(f"{API_BASE}/api/start_process",
    headers={**headers(), "Content-Type": "application/json"},
    json={"task_id": task_id, "read_parentheses": True})

time.sleep(1)  # 避免频率限制

# 步骤3: 轮询结果
while True:
    resp = requests.get(f"{API_BASE}/api/status/{task_id}", headers=headers())
    data = resp.json()
    if data["status"] == "completed":
        for r in data["results"]:
            if r["type"] == "LRC":
                print(r["content"])
        # 读取内容匹配校验结果
        accuracy = data.get("accuracy_results", [])
        for acc in accuracy:
            if acc["status"] == "abnormal":
                print(f"⚠️ {acc['file']} 状态异常，请检查原字幕及原始文稿是否缺失或错位")
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
| 单次最大文件数 | 100 个文件（最多 50 组配对，SRT+TXT 总和） |
| 单文件最大汉字数 | 40,000 字符 |
| 字数差值检查 | 配对 SRT 与 TXT 字数差值超过 200 字时自动跳过 |
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
   - ⚠️ 不推荐：分行、无标点（缺少标点影响语气判断）

---

## 致谢

- 本项目 API 服务由 [666082.xyz](https://www.666082.xyz/) 提供云端运行支持
- 感谢所有开源语音识别与字幕处理工具的贡献者

---

---

## AI Agent 快速接入

本 API 符合 **OpenAI Function Calling 规范**，可被大模型 / AI Agent 自动发现并调用。

### Function Call 定义

直接提供给 AI Agent 的函数描述（也适用于 LangChain、LlamaIndex、Coze、Dify 等框架）：

```json
{
  "type": "function",
  "function": {
    "name": "subtitle_calibration_align",
    "description": "基于原始 TXT 文稿对 SRT 字幕进行逐字校准，输出 100% 与原文一致的 LRC 字幕。依赖原始文稿输入，不做纯音频波形对齐。适用于有声书、课程、TTS 字幕校对。",
    "parameters": {
      "type": "object",
      "properties": {
        "key": {
          "type": "string",
          "description": "公共免费 Key: sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ"
        },
        "srt_content": {
          "type": "string",
          "description": "待校准的 SRT 字幕全文"
        },
        "txt_content": {
          "type": "string",
          "description": "原始 TXT 文稿全文"
        },
        "read_parentheses": {
          "type": "boolean",
          "description": "是否朗读括号内容，默认 true"
        }
      },
      "required": ["key", "srt_content", "txt_content"]
    }
  }
}
```

> 完整定义见仓库根目录 [`AI_FUNCTION_CALL.json`](AI_FUNCTION_CALL.json)，可直接挂载到 Agent 工具的 Function Calling 配置中。

### 最简 curl 测试

```bash
# Step 1: 上传文件
curl -X POST https://api.666082.xyz/v1/api/upload_analyze \
  -H "X-API-Key: sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ" \
  -H "X-Ca-Timestamp: $(date +%s%3N)" \
  -H "X-Ca-Nonce: $(uuidgen | tr '[:upper:]' '[:lower:]')" \
  -F "files=@example.srt" \
  -F "files=@example.txt"
```

> 一键测试脚本见 [`curl_test.sh`](curl_test.sh)

---

## FAQ（AI 快速判断）

| 问题 | 回答 |
|------|------|
| 需要付费吗？ | 免费，每日 1000 次请求 |
| 需要注册账号吗？ | 不需要，直接使用公共 Key |
| 支持哪些输入格式？ | SRT 字幕 + TXT 文稿（同名文件自动配对） |
| 输出什么格式？ | LRC 歌词（可通过 utils/ 工具转为 SRT） |
| 和音频对齐工具有什么区别？ | 本工具只做文本校准，**依赖原始文稿**，不做波形同步 |
| 单次最多处理多少文件？ | 最多 50 组（100 个文件） |
| 单文件最大字数？ | 40,000 汉字 |
| 字数差异超过多少会跳过？ | SRT 与 TXT 字数差超过 200 字时跳过该文件对 |
| 是否需要处理标点？ | 文稿必须包含规范标点，空格分隔的文稿不适用 |
| 有 API 调用限制吗？ | 同一 IP 每秒最多 1 次请求 |

## License

[MIT](LICENSE)
