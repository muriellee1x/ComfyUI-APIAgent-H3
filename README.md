# ComfyUI-APIAgent-H3

APIAgent 是一个 API-only ComfyUI 节点包，用于通过 OpenAI 兼容 API 执行内置 Skill，并生成、修复和校验 MiniMax H3 直播礼物提示词。

本版本不包含本地 Qwen/Gemma4 推理，不加载 GGUF 模型，不依赖 `llama-cpp-python`。

## 节点

- `APIAgent_SkillLoader`：加载并选择插件 `skills/` 目录中的 Skill。
- `APIAgent_LiveGiftTaskBuilder`：构建直播礼物 H3 任务，输出任务文本、H3 帧数和实际时长。
- `APIAgent_OpenAIAPIConfig`：配置 OpenAI 兼容 API 的 URL、模型、密钥、图片支持、超时和重试。
- `APIAgent_SkillSingleRunAPI`：通过远程 API 执行 Skill，支持最多 9 张图片和 H3 自动修复。
- `APIAgent_H3PromptValidator`：校验并规范化 H3 提示词，输出检查报告和是否通过。

推荐连接顺序：

```text
APIAgent_OpenAIAPIConfig ───────────┐
APIAgent_SkillLoader ───────────────┤
APIAgent_LiveGiftTaskBuilder ───────┼─> APIAgent_SkillSingleRunAPI -> APIAgent_H3PromptValidator
IMAGE / IMAGE 2 ... IMAGE 9 ────────┘
```

## API 密钥

`APIAgent_OpenAIAPIConfig` 的 `API密钥` 字段使用 ComfyUI 的 password 输入方式，前端会遮挡显示。

注意：这只是前端遮挡，不是加密存储。密钥不会进入 API 配置输出、运行信息或插件日志，但仍可能随 workflow JSON、PNG 工作流元数据或执行历史保存。需要共享工作流时，请先清空 `API密钥`。

## 业务 AzureOpenAI 预设

`业务 AzureOpenAI Chat Completions` 预设用于兼容 `AzureOpenAI(azure_endpoint=..., api_version=...)` 形式的业务网关。

- 默认 API 地址：`https://aidp.bytedance.net/api/modelhub/online/v2/crawl`
- 内部 API 版本：`2024-02-01`
- 请求路径：`{API地址}/openai/deployments/{模型名称}/chat/completions?api-version=2024-02-01`
- 鉴权头：`api-key: <API密钥>`
- 追踪头：`X-TT-LOGID: <每次请求自动生成的请求ID>`

## 图片数量规则

- T2VA：0 张图片
- I2VA：1 张首帧图片
- FL2VA：2 张首尾帧图片
- L2VA：1 张尾帧图片
- Ref2VA：1-9 张参考图片

## 安装

将插件放入 ComfyUI 的 `custom_nodes` 目录后重启 ComfyUI。当前 API-only 版本没有额外 pip 依赖。
