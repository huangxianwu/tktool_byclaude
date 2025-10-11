# AI剪辑师（方案草案）

本文件用于规划“自动剪辑师”功能的最小可用实现（MVP），聚焦与 Google Gemini 2.5 Pro 的集成与基础对话/多媒体输入能力，不做过度设计，以便您后续二次修改与扩展。

## 1. 需求复述

在左侧菜单新增入口“自动剪辑师”，进入后：
- 提供一个对话框入口，面向 `gemini.google.com` 的同类能力，支持输入文字与上传不超过 10 个图片或视频文件；
- 将文本与附件一并调用 Google 官方 Gemini 2.5 Pro API（域名：`https://generativelanguage.googleapis.com`），获得模型回答；
- 使用提供的 API Key（`AIzaSyBwr0MWRyPPOUBUkId8NvBCPhmDffRmhGA`）进行鉴权。

## 2. 需求分析

- 用户希望获得一个简洁的“AI 剪辑师”页面，能像聊天一样发送文字和多媒体，让模型做理解/建议/剪辑构思。
- 输入约束：一次会话最多选择 10 个图片或视频文件（与现有 `config.ALLOWED_EXTENSIONS` 相匹配）。
- 模型：指定使用 Gemini 2.5 Pro（如不可用，需具备可切换为其他稳定模型的方案，例如 2.5 Flash/1.5 Pro）。
- 响应展示：以聊天气泡形式显示模型文本结果，必要时显示基础的元信息（耗时、tokens 估算）。
- 安全与合规：API Key 需通过环境变量或服务器端配置注入，避免前端暴露；上传文件大小需受限，视频大文件不直接走前端 base64。

## 3. 资料查询（要点与引用）

- Gemini API 的标准内容生成端点（REST）：`models.generateContent`，示例：`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent`（2.5 系列沿用相同的端点与结构）。该文档说明了 contents/parts 结构、`inline_data` 传图等方式。[参考：Gemini API 生成内容文档][2]
- 开发者参考页面展示了使用 `x-goog-api-key` 头或 `key` 查询参数进行鉴权、以及 2.5 系列模型的调用示例（`gemini-2.5-flash` 等）。[参考：Gemini API 参考][3]
- Vertex AI 文档也提供了 generateContent 与流式 streamGenerateContent 的使用说明（若后续迁移到 Vertex/企业方案可复用该模型/调用方式）。[参考：Vertex AI 文档][1]

引用：
1. [Vertex AI - 使用 Gemini 生成内容](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference)
2. [Gemini API 生成内容文档](https://ai.google.dev/api/generate-content)
3. [Gemini API 参考](https://ai.google.dev/api)

## 4. 交互设计（MVP）

页面：左侧菜单新增“自动剪辑师”，进入后采用两段式简洁布局：

1) 会话区（主内容区）
- 顶部：标题“自动剪辑师”与模型选择下拉（默认：`gemini-2.5-pro`，可选：`gemini-2.5-flash`）。
- 中部：对话气泡列表（用户/模型）与轻量滚动容器。
- 底部：输入条（多模态）
  - 文本输入框：支持 Enter 发送，Shift+Enter 换行；可折行显示长文本。
  - 附件选择：支持拖拽/点击选择，最多 10 个文件，展示为可移除的“文件胶囊”列表（显示文件名/大小/类型）。
  - 发送按钮：loading 态、可中断；显示调用状态（排队/已发送/响应中）。
- 辅助：每条消息右上角提供“复制”与“引用到下一条”两个操作；复制时仅复制该条消息的纯文本内容，避免粘到其它页面元素。

2) 侧栏（次要信息）
- 会话管理：新建会话 / 清空 / 导出（JSON 或 Markdown）。
- 基础统计：最近一次响应耗时、输入/输出字数估算、已用配额提示（可选）。
- 使用须知：提示不要上传受限内容；告知隐私与密钥安全策略。

空态与加载态：
- 初次进入显示空态卡片，提示可输入文本或添加素材。
- 调用时显示进度条或骨架屏，不打断用户操作。

错误与告警：
- API 失败：在消息气泡中红色提示“调用失败”，提供“重试/查看详情”。
- 附件校验：类型/大小/数量超限时，在附件胶囊下方给出明确提示，不弹多重提示框。

## 5. 调用与数据结构（不写代码，给出约定）

后端统一提供一个接口（示例）：`POST /api/auto-editor/chat`

请求体（约定）：
```
{
  "model": "gemini-2.5-pro",
  "text": "...用户输入...",
  "files": [
    { "name": "a.jpg", "mime": "image/jpeg", "size": 102400, "source": "inline", "data_b64": "..." },
    { "name": "b.mp4", "mime": "video/mp4", "size": 10485760, "source": "file_api", "file_uri": "..." }
  ],
  "context": [ { "role": "user", "text": "历史轮次..." }, { "role": "model", "text": "历史回应..." } ]
}
```

响应体（约定）：
```
{
  "message": {
    "role": "model",
    "text": "...模型返回文本...",
    "raw": { "candidates": [ ... ] }
  },
  "usage": { "input_tokens": 1234, "output_tokens": 567 },
  "latency_ms": 980
}
```

与 Gemini API 的映射：
- REST 端点：`https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`。[见 2、3]
- 内容结构：`contents: [{role:"user", parts:[{text:"..."}, {inline_data:{mime_type:"image/jpeg", data:"base64..."}}]}]`。[见 2]
- 鉴权：在请求头添加 `x-goog-api-key: <API_KEY>` 或使用 `?key=<API_KEY>` 查询参数。[见 3]
- 模型名：优先使用 `gemini-2.5-pro`；若不可用，降级到 `gemini-2.5-flash` 或 `gemini-1.5-pro`（配置可切换）。

文件策略：
- 图片：小文件走 `inline_data`（前端直转 base64）；
- 视频/大文件：避免前端 base64，后端走“文件 API”或云存储，返回 `file_uri` 供 parts 引用（若文件 API 不可用则限制视频大小并给出提示）。
- 数量限制：统一在前端与后端双重校验（≤10）；类型沿用 `config.ALLOWED_EXTENSIONS`。

## 6. 安全与合规

- API Key 不在前端暴露：通过后端读取环境变量（如 `GEMINI_API_KEY`），由后端转发请求。
- 限制上传：后端检查 `mime/type` 与大小上限；拒绝超过限制的上传。
- 日志与隐私：避免将原始素材持久化（除非用户勾选“保存会话”）；记录最少必要信息用于排错。
- 速率限制：简单的每 IP/每会话限流，避免滥用导致配额耗尽。

## 7. 最小实现里程碑（MVP）

阶段 A（页面与接口框架）
- 菜单入口与空白页面；
- 前端输入条（文本 + 文件选择 + 文件胶囊显示、移除）；
- 后端 `POST /api/auto-editor/chat` 接口接入，透传到 Gemini API；
- 展示模型文本回答。

阶段 B（多模态与体验细化）
- 图片 `inline_data` 接入；
- 视频上传限制与后端处理占位；
- 消息的“复制/引用到下一条”；
- 发送进度与错误提示。

阶段 C（稳健性与配置）
- 模型下拉与降级策略；
- 使用统计与基础限流；
- 会话导出（JSON/Markdown）。

## 8. 风险与取舍

- 2.5 Pro 的可用性：若地区或密钥权限不支持，需允许回退到 2.5 Flash/1.5 Pro；
- 大视频输入：REST `inline_data` 不适合大文件，需改为后端文件 API/云存储引用；
- 成本与配额：提供基础计数/告警，避免误用；
- 法规与内容安全：开启默认安全阈值（hate/sexual/dangerous/harassment 等）。

## 9. 验收标准（MVP）

- 左侧菜单出现“自动剪辑师”，可进入页面；
- 输入文本 + 上传 ≤10 图片/视频，点击发送；
- 后端成功调用 Gemini API 并返回文本；
- 页面显示模型回答；
- 错误时有明确提示；
- 不暴露明文 API Key；
- 文件类型与数量有前后端双重校验。

——

附：示例端点与负载结构说明均参考官方文档（REST v1beta）。