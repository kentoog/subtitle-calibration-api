# 字幕校准 API 完整文档

> Subtitle Calibration API - Audio-Text Alignment Service
>
> Base URL: `https://api.666082.xyz/v1`
>
> 在线体验: [https://www.666082.xyz/](https://www.666082.xyz/)
>
> 联系QQ: 136172378

---

## 目录

- [认证方式](#认证方式)
- [请求限制](#请求限制)
- [错误码](#错误码)
- [接口列表](#接口列表)
  - [验证 API Key（可选）](#1-验证-api-key可选)
  - [上传文件](#2-上传文件)
  - [启动校准](#3-启动校准)
  - [查询状态](#4-查询状态)
- [完整调用流程](#完整调用流程)
- [文件配对规则](#文件配对规则)
- [文稿格式要求](#文稿格式要求)
- [输入输出格式](#输入输出格式)

---

## 认证方式

所有需要认证的接口均通过以下方式传递 API Key：

### 方式一：请求头（推荐）

```
X-API-Key: sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ
```

### 方式二：请求体

在 JSON 请求体中添加 `key` 字段：

```json
{
    "key": "sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ",
    "task_id": "xxx"
}
```

### 免费 API Key

```
sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ
```

- 每天限量 **1000 次请求**
- 每日北京时间 00:00 自动重置配额
- 如需更高配额，请联系 QQ: 136172378

---

## 请求限制

| 限制项 | 值 | 说明 |
|--------|------|------|
| 每日请求配额 | 1000 次/天 | 免费Key，每日北京时间 00:00 重置 |
| IP 频率限制 | 1 次/秒 | 同一 IP 每秒最多 1 次请求 |
| 单次最大文件数 | 40 个 | 单次上传最多 40 个文件 |
| 单次最大配对组 | 20 组 | SRT + TXT 同名配对，最多 20 组 |
| 单文件最小字符数 | 100 字符 | 低于此值可能影响校准质量 |
| 单文件最大字符数 | 20,000 字符 | 超出需拆分处理 |
| 支持的输入格式 | `.srt`（字幕） + `.txt`（文稿） | |
| 输出格式 | `.lrc`（歌词） | 可通过转换工具转为 .srt |
| 轮询间隔建议 | ≥ 5 秒 | 建议 5 秒轮询一次任务状态 |
| 单文件超时 | 10 分钟 | 单个文件处理超过 10 分钟视为超时，跳过并继续下一组 |

---

## 错误码

| HTTP 状态码 | 含义 | 说明 |
|-------------|------|------|
| 200 | 成功 | 请求处理成功 |
| 400 | 请求格式错误 | 参数缺失或格式不正确 |
| 401 | 认证失败 | API Key 无效或缺失 |
| 403 | 访问被拒绝 | 域名不在允许列表中 |
| 404 | 资源不存在 | task_id 无效或文件不存在 |
| 429 | 请求过于频繁 | IP 频率限制或每日配额用尽 |
| 500 | 服务器内部错误 | 服务端异常，请稍后重试 |
| 502 | 网关错误 | 上游服务异常 |
| 503 | 服务不可用 | 服务暂时过载或维护中 |

### 错误响应格式

```json
{
    "error": "错误类型",
    "message": "详细错误信息",
    "detail": "额外详情（可选）"
}
```

### 常见错误示例

**API Key 无效：**
```json
{
    "error": "Invalid API key",
    "detail": "Invalid API key"
}
```

**配额用尽：**
```json
{
    "error": "Daily limit exceeded (1000/1000)",
    "detail": "Daily limit exceeded (1000/1000)"
}
```

**IP 频率限制：**
```json
{
    "error": "Too Many Requests",
    "message": "请求过于频繁，请等待 0.52 秒后再试",
    "retry_after": 0.52
}
```

---

## 接口列表

---

### 1. 验证 API Key（可选）

验证 API Key 的有效性，并查询当前配额使用情况。

**请求**

```
POST /v1/api/verify_key
```

**请求头**

| 参数 | 必填 | 说明 |
|------|------|------|
| `X-API-Key` | 是 | API 密钥 |

**成功响应**

```json
{
    "valid": true,
    "usage_count": 42,
    "daily_limit": 1000,
    "remaining": 958
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `valid` | boolean | Key 是否有效 |
| `usage_count` | number | 今日已使用次数 |
| `daily_limit` | number | 每日限额（-1 表示无限制） |
| `remaining` | number | 今日剩余次数（-1 表示无限制） |

**失败响应**

```json
{
    "valid": false,
    "error": "Invalid API key"
}
```

或配额用尽时：

```json
{
    "valid": false,
    "error": "Daily limit exceeded (1000/1000)"
}
```

---

### 2. 上传文件

上传 SRT 字幕文件和 TXT 原始文稿，系统自动按文件名配对。

**请求**

```
POST /v1/api/upload_analyze
```

**请求头**

| 参数 | 必填 | 说明 |
|------|------|------|
| `X-API-Key` | 是 | API 密钥 |

**请求体**

`multipart/form-data` 格式，所有文件通过 `files` 字段上传：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `files` | File[] | 是 | SRT 和 TXT 文件，可同时上传多个 |

**文件命名规则**

SRT 和 TXT 文件通过**同名配对**（去掉扩展名后名称一致）：

```
example.srt  ←→  example.txt
chapter1.srt ←→  chapter1.txt
```

**成功响应**

```json
{
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "file_count": 2,
    "srt_files": ["example.srt"],
    "txt_files": ["example.txt"]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务 ID，后续操作需要此 ID |
| `file_count` | number | SRT 文件数量 |
| `srt_files` | string[] | 识别到的 SRT 文件名列表 |
| `txt_files` | string[] | 识别到的 TXT 文件名列表 |

**错误响应**

```json
{
    "error": "No files uploaded"
}
```

---

### 3. 启动校准

启动已上传文件的 AI 校准任务。

**请求**

```
POST /v1/api/start_process
```

**请求头**

| 参数 | 必填 | 说明 |
|------|------|------|
| `X-API-Key` | 是 | API 密钥 |
| `Content-Type` | 是 | `application/json` |

**请求体**

```json
{
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "read_parentheses": true
}
```

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `task_id` | string | 是 | - | 上传文件时返回的任务 ID |
| `read_parentheses` | boolean | 否 | `true` | 是否朗读括号内容（如旁白说明） |

**成功响应**

```json
{
    "status": "started",
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "allowed_count": 2,
    "total_files": 2
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | 任务状态：`started` |
| `task_id` | string | 任务 ID |
| `allowed_count` | number | 本次允许处理的文件数（受配额限制） |
| `total_files` | number | 总文件数 |

**配额不足时的响应**

当剩余配额不足以处理所有文件时，`allowed_count` 会小于 `total_files`，超出部分将返回错误结果。

**错误响应**

```json
{
    "error": "task_id is required"
}
```

```json
{
    "error": "Invalid task_id"
}
```

---

### 4. 查询状态

查询校准任务的执行状态和结果。**结果直接在响应中返回 LRC 内容**。

**请求**

```
GET /v1/api/status/{task_id}
```

**请求头**

| 参数 | 必填 | 说明 |
|------|------|------|
| `X-API-Key` | 是 | API 密钥 |

**路径参数**

| 参数 | 说明 |
|------|------|
| `task_id` | 任务 ID |

**处理中响应**

```json
{
    "status": "processing",
    "completed": 1,
    "total": 2,
    "current_file": "chapter1.srt",
    "results": [
        {
            "name": "example.lrc",
            "type": "LRC",
            "error": null,
            "content": "[00:00.00]校准后的歌词内容..."
        }
    ]
}
```

**完成响应**

```json
{
    "status": "completed",
    "completed": 2,
    "total": 2,
    "results": [
        {
            "name": "example.lrc",
            "type": "LRC",
            "error": null,
            "content": "[00:00.00]校准后的歌词第一行\n[00:05.23]校准后的歌词第二行\n..."
        },
        {
            "name": "chapter1.lrc",
            "type": "LRC",
            "error": null,
            "content": "[00:00.00]另一段校准内容..."
        }
    ]
}
```

**错误结果**

如果某个文件校准失败，该条目的 `type` 为 `ERROR`：

```json
{
    "name": "failed.srt",
    "type": "ERROR",
    "error": "Missing corresponding TXT file: failed.txt",
    "content": null
}
```

**超时错误**

单个文件处理超过 10 分钟时，该文件会被跳过，任务继续处理下一组：

```json
{
    "name": "large_file.srt",
    "type": "ERROR",
    "error": "处理超时 (10分钟)，已跳过",
    "content": null
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | 任务状态：`pending` / `processing` / `completed` / `error` |
| `completed` | number | 已完成文件数 |
| `total` | number | 总文件数 |
| `current_file` | string | 当前正在处理的文件名（仅 `processing` 状态时有值） |
| `results` | array | 结果列表 |
| `results[].name` | string | 输出文件名（.lrc） |
| `results[].type` | string | 结果类型：`LRC`（成功） / `ERROR`（失败） |
| `results[].content` | string\|null | LRC 文件内容（成功时有值） |
| `results[].error` | string\|null | 错误信息（失败时有值） |

---

## 完整调用流程

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌───────────────┐
│  1. 上传文件  │────▶│  2. 启动校准任务   │────▶│  3. 轮询任务状态   │────▶│  4. 获取结果   │
│  upload_     │     │  start_process   │     │  status/{id}     │     │  results中     │
│  analyze     │     │                  │     │  (每5秒轮询)      │     │  的content     │
└─────────────┘     └──────────────────┘     └──────────────────┘     └───────────────┘
       │                    │                        │
       │  返回 task_id      │  传入 task_id           │  status=completed
       │                    │                        │  时停止轮询
       ▼                    ▼                        ▼
```

### 详细步骤

**Step 1: 上传文件**

```bash
curl -X POST https://api.666082.xyz/v1/api/upload_analyze \
  -H "X-API-Key: sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ" \
  -F "files=@example.srt" \
  -F "files=@example.txt"
```

响应：
```json
{
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "file_count": 1,
    "srt_files": ["example.srt"],
    "txt_files": ["example.txt"]
}
```

**Step 2: 启动校准**

```bash
curl -X POST https://api.666082.xyz/v1/api/start_process \
  -H "X-API-Key: sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "read_parentheses": true}'
```

响应：
```json
{
    "status": "started",
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "allowed_count": 1,
    "total_files": 1
}
```

**Step 3: 轮询状态**

```bash
curl https://api.666082.xyz/v1/api/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -H "X-API-Key: sk-vMw7Y25rAbc8NG9Wr0iNacVGKYn4xmOS6FuXDodmavpLzquJ"
```

处理中响应：
```json
{
    "status": "processing",
    "completed": 0,
    "total": 1,
    "results": []
}
```

**Step 4: 获取结果**

当 `status` 变为 `completed` 时，结果直接包含在响应中：

```json
{
    "status": "completed",
    "completed": 1,
    "total": 1,
    "results": [
        {
            "name": "example.lrc",
            "type": "LRC",
            "error": null,
            "content": "[00:00.50]第一句校准后的歌词\n[00:05.23]第二句校准后的歌词\n[00:10.15]第三句校准后的歌词"
        }
    ]
}
```

---

## 文件配对规则

上传的 SRT 和 TXT 文件通过**去除扩展名后的文件名**自动配对：

| SRT 文件 | TXT 文件 | 配对结果 |
|----------|----------|----------|
| `example.srt` | `example.txt` | ✅ 配对成功 |
| `chapter1.srt` | `chapter1.txt` | ✅ 配对成功 |
| `a.srt` | `b.txt` | ❌ 无匹配，a.srt 将报错 |
| `x.srt` | (无) | ❌ 缺少文稿，x.srt 将报错 |

> 配对失败的文件在结果中 `type` 为 `ERROR`，`error` 字段说明原因。

---

## 文稿格式要求

文稿格式直接影响 AI 断句准确率，**必须包含符合 TTS 合成习惯的标点符号**。

### ✅ 推荐格式

**连续文本 + 标点：**
```
第一句，第二句。第三句！
```

**分行 + 标点：**
```
第一句，
第二句。
第三句！
```

### ❌ 不适合格式

**空格分隔（严重错误）：**
```
第一句 第二句 第三句
```
AI 无法识别句子边界，会导致严重的断句错误。

### ⚠️ 不推荐格式

**分行无标点：**
```
第一句
第二句
第三句
```
缺少标点影响语气判断，断句准确率下降。

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

**Python:**
```python
from utils.lrc_srt_converter import lrc_to_srt

srt_content = lrc_to_srt(lrc_content)
```

**JavaScript:**
```javascript
const { lrcToSrt } = require('./utils/lrc_srt_converter.js');
const srtContent = lrcToSrt(lrcContent);
```
