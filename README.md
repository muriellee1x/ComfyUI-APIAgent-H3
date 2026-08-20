# ComfyUI-APIAgent-H3

APIAgent 是一个 API-only ComfyUI 节点包，用于通过 OpenAI 兼容 API 执行内置 Skill，并生成直播礼物图像提示词和 MiniMax H3 视频提示词。

本版本不包含本地 Qwen/Gemma4 推理，不加载 GGUF 模型，不依赖 `llama-cpp-python`。

## 节点

- `APIAgent_SkillLoader`：加载并选择插件 `skills/` 目录中的 Skill。
- `APIAgent_LiveGiftTaskBuilder`：构建直播礼物任务；支持 `趣味 / 彰显 / 应援 / 惊喜` 情感表达，并按价格同时输出确定的图像和视频 Skill 路由及整数价格。
- `APIAgent_OpenAIAPIConfig`：配置 OpenAI 兼容 API 的 URL、模型、密钥、图片支持、超时和重试。
- `APIAgent_SkillSingleRunAPI`：通过远程 API 执行 Skill，支持最多 9 张图片、H3 自动校验和 API 自动修复，并在 `API运行信息` 中输出校验报告。
- `APIAgent_ImageSkillSingleRunAPI`：执行直播礼物图像 Skill，融合最多 9 张软参考图，输出中文提示词、英文提示词和包含结构化图像分析的运行信息。

推荐连接顺序：

```text
APIAgent_LiveGiftTaskBuilder（任务 + 图像路由）──> APIAgent_ImageSkillSingleRunAPI
APIAgent_LiveGiftTaskBuilder（任务 + 视频路由）──> APIAgent_SkillSingleRunAPI
APIAgent_OpenAIAPIConfig ────────────────────────> 两个执行节点
IMAGE / IMAGE 2 ... IMAGE 9 ─────────────────────> 两个执行节点
```

直播礼物构建器输出依次为任务、H3 帧数、实际时长、`图像Skill路由`、`视频Skill路由` 和整数 `礼物价格`。新增价格位于第六个端口，原有前五个输出索引不变。独立的 `APIAgent_SkillLoader` 仍用于手动选择和通用自动路由。

价格输入范围为 `99–3000`，98 以下和 3000 以上会直接拒绝。价格 Skill 路由是本地确定性逻辑，不会额外请求 API。

低价礼物使用固定有效规格：99–299 为 73 帧（约 3.04 秒），300–999 为 90 帧（3.75 秒），并强制单镜头、静音及 `1:1 / 4:3` 画幅。构建器保留用户填写的原始值，但发生冲突时以低价价效规范为准。

视频执行节点提供可选的 `低价固定背景色` 输入，只接受六位 `#RRGGBB`。99–499 留空时自动使用 `#00FF00`；500–999 留空时保留紧凑场景能力，填写时切换为指定的全程固定纯色背景；高价及其他 Skill 会忽略该输入并在运行信息中说明。固定色值不占用参考图片，I2VA、FL2VA、L2VA 的端点图需要由上游预先使用相同背景色。

## Skill 渐进式披露

两个直播礼物 Skill 将上下文分为必读规则和可选 Reference：

- 必读：当前价格规范、H3 基础规范、Ref2VA 专用规范（仅 Ref2VA）和所选情感规范。
- 可选：故事、动效因果、四秒节奏与非线性运动、量化安全构图、组件高潮、镜头连续性及与主体匹配的风险章节。
- 每次执行固定增加一次 Reference 路由请求，并向路由模型发送任务与最长边 512px 的参考图。

路由支持 JSON 数组、常见 JSON 对象和 JSON 代码围栏；仍无法解析、返回非法 ID 或超出路由上下文时会直接报错，不会静默加载全部资料。已加载规则、Reference ID、注入字符数及各阶段请求次数都会写入 `API运行信息`。`evaluation-cases.md` 仅用于回归评测，不会进入生成上下文。

`APIAgent_SkillSingleRunAPI` 不再暴露“参考资料策略”和“缺失信息策略”。礼物 Skill 固定使用“确定性必读规则 + LLM 选择可选 Reference”；缺失参数统一遵循各 Skill 自身的默认值和错误规则。

API 配置默认使用 `119808` 上下文长度和 `300` 秒请求超时；上下文长度仅用于客户端发送前的预算检查，不会修改远程模型能力。

`APIAgent_SkillSingleRunAPI` 会在生成后校验 H3 格式；失败时按“自动修复次数”再次调用 API。最终状态、初始错误、修复次数和警告会追加到 `API运行信息`。独立的 H3 校验节点已移除。

两个图像提示词 Skill 使用相同的价格边界：`image-low-coin-gift-prompt-director` 处理 99–999，`image-live-gift-prompt-director` 处理 1000–3000。低价图像中，99–499 固定使用纯黑背景，500–999 可使用纯黑背景或一处紧凑简单背景。每次确定性加载价效、配色、prompt pattern、当前情感章节和输出审计规则，再通过一次 LLM Reference 路由选择视觉风格及人物服装章节。非法路由结果会直接报错，不会加载全部资料。

图像执行节点把参考图视为主体、妆造、场景、材质、风格或构图软参考。`参考图说明` 可指定每张图片的用途；生成时先形成逐图结构化分析，再融合为一组中英文 W+ 提示词。分析写入 `API运行信息`，提示词输出保持纯文本。JSON 结构、图片索引、分析字段和 W+ 触发词校验失败时自动修复一次。

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
- 图像提示词节点：0-9 张软参考图片，多张图片融合为一组提示词

## 安装

将插件放入 ComfyUI 的 `custom_nodes` 目录后重启 ComfyUI。当前 API-only 版本没有额外 pip 依赖。
