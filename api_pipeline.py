# -*- coding: utf-8 -*-
import json
import math
import re
import secrets
import socket
import threading
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import comfy.model_management as mm

from .skill_loader import 获取skill, 读取skill正文
from .skill_pipeline import (
    直播礼物SKILL_ID,
    _h3_reference,
    _构建用户内容,
    _构建系统提示词,
    _拆分礼物外部提示,
    _收集图片,
    _检查h3图片数量,
    _清理最终文本,
    _礼物h3_references,
    _解析h3时长,
    _解析h3模式,
    _解析reference选择,
    _计算上下文预算,
    _默认单次设置,
    校验h3提示词,
)


API服务预设 = (
    "通用 OpenAI Chat Completions",
    "通用 OpenAI Responses API",
    "业务 AzureOpenAI Chat Completions",
)

_API预设配置 = {
    "通用 OpenAI Chat Completions": {
        "协议": "chat",
        "API地址": "",
        "模型名称": "",
        "输出Token字段": "自动选择",
    },
    "通用 OpenAI Responses API": {
        "协议": "responses",
        "API地址": "",
        "模型名称": "",
        "输出Token字段": "自动选择",
    },
    "业务 AzureOpenAI Chat Completions": {
        "协议": "azure_chat",
        "API地址": "https://aidp.bytedance.net/api/modelhub/online/v2/crawl",
        "模型名称": "gpt-5-2025-08-07",
        "API版本": "2024-02-01",
        "输出Token字段": "自动选择",
    },
}

_可重试HTTP状态 = {408, 429, 500, 502, 503, 504}
_截断原因 = {"length", "max_tokens", "max_output_tokens"}


class _禁止重定向(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class API请求错误(RuntimeError):
    def __init__(self, message: str, status: int = -1, retry_after: float = 0.0):
        super().__init__(message)
        self.status = int(status or 0)
        self.retry_after = float(retry_after or 0.0)


class _API密钥缓存:
    _values: dict[str, str] = {}
    _lock = threading.Lock()
    _max_entries = 128

    @classmethod
    def store(cls, api_key: str) -> str:
        value = str(api_key or "").strip()
        if not value:
            return ""
        reference = secrets.token_urlsafe(24)
        with cls._lock:
            cls._values[reference] = value
            while len(cls._values) > cls._max_entries:
                cls._values.pop(next(iter(cls._values)))
        return reference

    @classmethod
    def get(cls, reference: str) -> str:
        with cls._lock:
            return cls._values.get(str(reference or ""), "")


def _中断检查() -> None:
    if mm.processing_interrupted():
        raise mm.InterruptProcessingException()


def _脱敏文本(text: str, api_key: str = "") -> str:
    cleaned = str(text or "")
    if api_key:
        cleaned = cleaned.replace(api_key, "<API_KEY>")
    cleaned = re.sub(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;\"']+", r"\1<API_KEY>", cleaned)
    cleaned = re.sub(r"(?i)((?:api[-_]?key|token|secret|password|\bak\b)\s*[:=]\s*)[^\s,;\"']+", r"\1<API_KEY>", cleaned)
    cleaned = re.sub(r"(?i)([?&](?:api[-_]?key|key|token|secret|password|authorization|ak)=)[^&\s]+", r"\1<API_KEY>", cleaned)
    return cleaned[:1200]


def _是敏感查询字段(name: str) -> bool:
    compact = re.sub(r"[^a-z0-9]", "", str(name or "").lower())
    return compact in {
        "ak",
        "apikey",
        "key",
        "token",
        "accesstoken",
        "refreshtoken",
        "idtoken",
        "secret",
        "clientsecret",
        "password",
        "authorization",
        "authentication",
        "auth",
        "bearer",
        "credential",
        "credentials",
        "signature",
        "sig",
        "jwt",
    }


def _校验API地址(url: str) -> str:
    value = str(url or "").strip().rstrip("/")
    if not value:
        raise ValueError("API地址不能为空，请填写 OpenAI 兼容服务地址。")
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("API地址必须是完整的 http:// 或 https:// 地址。")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("API地址不能包含用户名或密码；鉴权信息请通过 API密钥 提供。")
    if parsed.fragment:
        raise ValueError("API地址不能包含 #fragment。")
    hostname = (parsed.hostname or "").lower()
    local_http = hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme == "http" and not local_http:
        raise ValueError("远程 API 默认要求 HTTPS；localhost/127.0.0.1 可使用 HTTP。")
    for key, _value in parse_qsl(parsed.query, keep_blank_values=True):
        if _是敏感查询字段(key):
            raise ValueError("API地址不能在 URL 查询参数中携带密钥、token 或 AK；请改用 API密钥。")
    return value


def _合并查询参数(url: str, values: dict[str, str]) -> str:
    parsed = urlsplit(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({key: str(value) for key, value in values.items() if value not in (None, "")})
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


def _追加路径(url: str, suffix: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path.rstrip("/")
    if not path.lower().endswith(suffix.lower()):
        path += suffix
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))


def _构建请求URL(config: dict) -> str:
    base_url = str(config["API地址"]).rstrip("/")
    protocol = config["协议"]
    if protocol == "azure_chat":
        suffix = "/chat/completions"
        path = urlsplit(base_url).path.lower()
        if path.endswith(suffix):
            request_url = base_url
        elif "/openai/deployments/" in path:
            request_url = _追加路径(base_url, suffix)
        else:
            deployment = quote(str(config["模型名称"]), safe="")
            request_url = _追加路径(base_url, f"/openai/deployments/{deployment}/chat/completions")
        return _合并查询参数(request_url, {"api-version": str(config.get("API版本") or "2024-02-01")})
    suffix = "/chat/completions" if protocol == "chat" else "/responses"
    if urlsplit(base_url).path.lower().endswith(suffix):
        return base_url
    return _追加路径(base_url, suffix)


def _规范化API配置(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("请连接“API配置”节点。")
    preset_name = str(value.get("服务预设") or "").strip()
    if preset_name not in _API预设配置:
        raise ValueError("API配置中的服务预设无效，请重新选择。")
    preset = dict(_API预设配置[preset_name])
    for key in ("API地址", "模型名称"):
        override = str(value.get(key) or "").strip()
        if override:
            preset[key] = override
    preset.update(
        {
            "服务预设": preset_name,
            "上下文长度": int(value.get("上下文长度") or 4096),
            "支持图片": bool(value.get("支持图片", True)),
            "图片细节": str(value.get("图片细节") or "auto"),
            "请求超时秒": int(value.get("请求超时秒") or 10),
            "失败重试次数": int(value.get("失败重试次数") or 1),
            "输出Token字段": str(value.get("输出Token字段") or preset.get("输出Token字段") or "自动选择"),
            "发送高级采样参数": bool(value.get("发送高级采样参数", False)),
            "直接密钥引用": str(value.get("直接密钥引用") or ""),
        }
    )
    preset["API地址"] = _校验API地址(preset["API地址"])
    if not preset["模型名称"]:
        raise ValueError("模型名称不能为空。")
    if preset["上下文长度"] < 4096:
        raise ValueError("API上下文长度不能小于 4096。")
    if preset["图片细节"] not in {"auto", "high", "low"}:
        raise ValueError("图片细节只能是 auto、high 或 low。")
    if preset["输出Token字段"] not in {"自动选择", "max_tokens", "max_completion_tokens", "max_output_tokens"}:
        raise ValueError("输出 token 字段配置无效。")
    if not 10 <= preset["请求超时秒"] <= 600:
        raise ValueError("API 请求超时必须在 10–600 秒之间。")
    if not 0 <= preset["失败重试次数"] <= 3:
        raise ValueError("API 失败重试次数必须在 0–3 之间。")
    return preset


def _提取内容文本(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
    return "\n".join(parts).strip()


def _解析API回复(data: dict, protocol: str, allow_truncated: bool = False) -> str:
    if not isinstance(data, dict):
        raise RuntimeError("API 返回格式无效：响应不是 JSON 对象。")
    error = data.get("error")
    if error:
        if isinstance(error, dict):
            message = error.get("message") or error.get("code") or json.dumps(error, ensure_ascii=False)
        else:
            message = str(error)
        raise RuntimeError(f"API 返回错误：{message}")
    truncated = False
    if protocol in {"chat", "azure_chat"}:
        choices = data.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            if allow_truncated:
                return ""
            raise RuntimeError("API 返回为空：没有 choices。")
        finish_reason = str(choices[0].get("finish_reason") or "").lower()
        truncated = finish_reason in _截断原因
        if finish_reason in {"content_filter", "safety"}:
            raise RuntimeError("API 输出被服务方的内容安全策略拦截。")
        message = choices[0].get("message") or {}
        refusal = message.get("refusal") if isinstance(message, dict) else ""
        if refusal:
            raise RuntimeError(f"API 拒绝了当前请求：{refusal}")
        text = _提取内容文本(message.get("content") if isinstance(message, dict) else "")
    else:
        incomplete = data.get("incomplete_details") or {}
        reason = str(incomplete.get("reason") or "").lower() if isinstance(incomplete, dict) else ""
        status = str(data.get("status") or "").lower()
        truncated = reason in _截断原因 or (
            status == "incomplete" and reason in {"", "length", "max_output_tokens"}
        )
        if status == "incomplete":
            if reason in {"content_filter", "safety"}:
                raise RuntimeError("API 输出被服务方的内容安全策略拦截。")
            if not truncated:
                raise RuntimeError(f"API 未完成当前请求：{reason or '服务未提供原因'}")
        if status and status != "completed":
            if not truncated:
                raise RuntimeError(f"API 请求状态不是 completed：{status}")
        if data.get("refusal"):
            raise RuntimeError(f"API 拒绝了当前请求：{data['refusal']}")
        text = str(data.get("output_text") or "").strip()
        if not text:
            parts = []
            for item in data.get("output") or []:
                if not isinstance(item, dict):
                    continue
                for content_item in item.get("content") or []:
                    if isinstance(content_item, dict) and content_item.get("type") == "refusal":
                        refusal = content_item.get("refusal") or content_item.get("text") or "服务未提供原因"
                        raise RuntimeError(f"API 拒绝了当前请求：{refusal}")
                extracted = _提取内容文本(item.get("content"))
                if extracted:
                    parts.append(extracted)
            text = "\n".join(parts).strip()
    if not text:
        if allow_truncated:
            return ""
        if truncated:
            raise ValueError("API 输出达到最大生成 token 且未产生正文，请提高“最大生成token”或缩短任务。")
        raise RuntimeError("API 返回了空文本；请检查模型是否支持当前请求和图片输入。")
    if truncated and not allow_truncated:
        raise ValueError("API 输出达到最大生成 token 后被截断，请提高“最大生成token”或缩短任务。")
    return text


def _转Responses输入(messages: list[dict], image_detail: str) -> tuple[str, list[dict]]:
    instructions = "\n\n".join(
        str(message.get("content") or "").strip()
        for message in messages
        if message.get("role") == "system" and str(message.get("content") or "").strip()
    )
    inputs = []
    for message in messages:
        if message.get("role") == "system":
            continue
        content = message.get("content")
        converted = []
        if isinstance(content, str):
            converted.append({"type": "input_text", "text": content})
        elif isinstance(content, list):
            image_items = []
            text_items = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "image_url":
                    image_value = item.get("image_url")
                    if isinstance(image_value, dict):
                        image_url = image_value.get("url")
                        detail = image_value.get("detail") or image_detail
                    else:
                        image_url = image_value
                        detail = image_detail
                    if image_url:
                        image_items.append({"type": "input_image", "image_url": image_url, "detail": detail})
                elif item.get("type") in {"text", "input_text"} and isinstance(item.get("text"), str):
                    text_items.append({"type": "input_text", "text": item["text"]})
            converted.extend(image_items)
            converted.extend(text_items)
        if converted:
            inputs.append({"role": message.get("role") or "user", "content": converted})
    return instructions, inputs


def _补充Chat图片细节(messages: list[dict], image_detail: str) -> list[dict]:
    converted_messages = []
    for message in messages:
        copied = dict(message)
        content = copied.get("content")
        if isinstance(content, list):
            copied_content = []
            for item in content:
                if not isinstance(item, dict):
                    copied_content.append(item)
                    continue
                copied_item = dict(item)
                if copied_item.get("type") == "image_url" and isinstance(copied_item.get("image_url"), dict):
                    image_value = dict(copied_item["image_url"])
                    image_value.setdefault("detail", image_detail)
                    copied_item["image_url"] = image_value
                copied_content.append(copied_item)
            copied["content"] = copied_content
        converted_messages.append(copied)
    return converted_messages


def _估算远程消息token数(messages: list[dict], image_count: int = 0) -> int:
    ascii_chars = 0
    non_ascii_chars = 0

    def consume(value) -> None:
        nonlocal ascii_chars, non_ascii_chars
        if isinstance(value, str):
            if value.startswith("data:image/"):
                return
            for char in value:
                if ord(char) < 128:
                    ascii_chars += 1
                else:
                    non_ascii_chars += 1
        elif isinstance(value, list):
            for item in value:
                consume(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key not in {"url", "image_url"} or not (isinstance(item, str) and item.startswith("data:image/")):
                    consume(item)

    consume(messages)
    return int(math.ceil(ascii_chars / 4.0 + non_ascii_chars * 1.15)) + int(image_count) * 2048 + 32


def _选择ChatToken字段(config: dict) -> str:
    configured = str(config.get("输出Token字段") or "自动选择")
    if configured in {"max_tokens", "max_completion_tokens"}:
        return configured
    if config.get("协议") == "azure_chat":
        return "max_tokens"
    model_name = str(config.get("模型名称") or "").lower().rsplit("/", 1)[-1]
    if re.match(r"^(?:gpt-5(?:[-.]|$)|o[1-9](?:[-.]|$))", model_name):
        return "max_completion_tokens"
    return "max_tokens"


class _远程API客户端:
    def __init__(self, config: dict, opener=None):
        self.config = _规范化API配置(config)
        direct_reference = self.config.get("直接密钥引用") or ""
        self.api_key = _API密钥缓存.get(direct_reference)
        if direct_reference and not self.api_key:
            raise RuntimeError("直接填写的 API 密钥缓存已失效，请重新执行 API配置节点后重试。")
        self.url = _构建请求URL(self.config)
        self.opener = opener or build_opener(_禁止重定向())
        self.request_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        self.stage_request_counts = {
            "Skill路由": 0,
            "Reference路由": 0,
            "最终生成": 0,
            "H3自动修复": 0,
        }

    def _headers(self, request_id: str) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            if self.config.get("协议") == "azure_chat":
                headers["api-key"] = self.api_key
                headers["X-TT-LOGID"] = request_id
            else:
                headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _记录usage(self, data: dict) -> None:
        if not isinstance(data, dict):
            return
        usage = data.get("usage") or {}
        if not isinstance(usage, dict):
            return
        input_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
        output_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
        total_tokens = usage.get("total_tokens", 0) or 0
        try:
            self.total_input_tokens += int(input_tokens)
            self.total_output_tokens += int(output_tokens)
            self.total_tokens += int(total_tokens) if total_tokens else int(input_tokens) + int(output_tokens)
        except (TypeError, ValueError):
            pass

    def _请求(self, payload: dict, stage: str) -> dict:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request_id = uuid.uuid4().hex
        retries = max(0, min(3, int(self.config["失败重试次数"])))
        for attempt in range(retries + 1):
            _中断检查()
            request = Request(self.url, data=body, headers=self._headers(request_id), method="POST")
            self.request_count += 1
            self.stage_request_counts[stage] = self.stage_request_counts.get(stage, 0) + 1
            try:
                with self.opener.open(request, timeout=int(self.config["请求超时秒"])) as response:
                    raw = response.read().decode("utf-8", errors="replace")
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise API请求错误("API 返回的不是 JSON：" + _脱敏文本(raw, self.api_key), status=-1) from exc
                if not isinstance(data, dict):
                    raise API请求错误("API 返回格式无效：JSON 顶层必须是对象。", status=-1)
                if data.get("error"):
                    error = data["error"]
                    detail = error.get("message") if isinstance(error, dict) else str(error)
                    raise API请求错误("API 返回错误：" + _脱敏文本(detail, self.api_key), status=-1)
                return data
            except HTTPError as exc:
                raw_detail = exc.read().decode("utf-8", errors="replace")
                retry_after = 0.0
                try:
                    retry_after = float(exc.headers.get("Retry-After") or 0)
                except (TypeError, ValueError):
                    retry_after = 0.0
                error = API请求错误(
                    f"API HTTP {exc.code}：{_脱敏文本(raw_detail, self.api_key)}",
                    status=exc.code,
                    retry_after=retry_after,
                )
            except (TimeoutError, socket.timeout) as exc:
                error = API请求错误(
                    "API 请求超时，结果状态未知；为避免重复计费，本次不会自动重试："
                    + _脱敏文本(str(exc), self.api_key),
                    status=-2,
                )
            except URLError as exc:
                if isinstance(getattr(exc, "reason", None), (TimeoutError, socket.timeout)):
                    error = API请求错误(
                        "API 请求超时，结果状态未知；为避免重复计费，本次不会自动重试："
                        + _脱敏文本(str(exc), self.api_key),
                        status=-2,
                    )
                else:
                    error = API请求错误("API 网络连接失败：" + _脱敏文本(str(exc), self.api_key), status=0)
            except API请求错误 as exc:
                error = exc
            retryable = error.status == 0 or error.status in _可重试HTTP状态
            if attempt >= retries or not retryable:
                raise error
            _中断检查()
            delay = error.retry_after if error.retry_after > 0 else 0.5 * (2**attempt)
            delay = min(max(delay, 0.0), 8.0)
            print(f"[APIAgent API] 请求暂时失败，{delay:g} 秒后进行第 {attempt + 2} 次尝试。")
            time.sleep(delay)
        raise RuntimeError("API 请求失败。")

    def complete(
        self,
        messages: list[dict],
        max_tokens: int,
        settings: dict | None = None,
        *,
        stage: str = "最终生成",
        allow_truncated: bool = False,
    ) -> str:
        protocol = self.config["协议"]
        payload = {"model": self.config["模型名称"]}
        if protocol == "responses":
            instructions, inputs = _转Responses输入(messages, self.config["图片细节"])
            payload.update({"input": inputs, "max_output_tokens": int(max_tokens)})
            if instructions:
                payload["instructions"] = instructions
        else:
            token_field = _选择ChatToken字段(self.config)
            payload.update(
                {
                    "messages": _补充Chat图片细节(messages, self.config["图片细节"]),
                    token_field: int(max_tokens),
                    "stream": False,
                }
            )
            if self.config.get("发送高级采样参数") and settings:
                payload.update(
                    {
                        "temperature": float(settings["温度"]),
                        "top_p": float(settings["top_p"]),
                        "frequency_penalty": float(settings["频率惩罚"]),
                        "presence_penalty": float(settings["存在惩罚"]),
                        "seed": int(settings["seed"]),
                    }
                )
        try:
            data = self._请求(payload, stage)
            self._记录usage(data)
            return _解析API回复(data, protocol, allow_truncated=allow_truncated)
        except mm.InterruptProcessingException:
            raise
        except ValueError as exc:
            raise ValueError(f"{stage}失败：{exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"{stage}失败：{exc}") from exc

    def summary(self) -> str:
        lines = [
            f"服务：{self.config['服务预设']}",
            f"模型：{self.config['模型名称']}",
            f"API请求次数：{self.request_count}",
        ]
        lines.extend(
            f"{stage}请求：{self.stage_request_counts.get(stage, 0)}"
            for stage in ("Skill路由", "Reference路由", "最终生成", "H3自动修复")
        )
        if self.total_tokens:
            lines.append(
                f"服务返回Token：输入 {self.total_input_tokens}，输出 {self.total_output_tokens}，合计 {self.total_tokens}"
            )
        else:
            lines.append("服务未返回Token统计。")
        return "\n".join(lines)


def _解析skill选择(text: str, valid_ids: set[str]) -> str:
    selected = _清理最终文本(text).strip().strip("`'\".,，。 ")
    if selected in valid_ids:
        return selected
    matches = [
        skill_id
        for skill_id in sorted(valid_ids)
        if re.search(rf"(?<![A-Za-z0-9_.-]){re.escape(skill_id)}(?![A-Za-z0-9_.-])", selected)
    ]
    return matches[0] if len(matches) == 1 else ""


def _选择skill_api(client: _远程API客户端, skill_loader: dict, task: str) -> dict:
    if not isinstance(skill_loader, dict):
        raise ValueError("请连接 API Skill加载器。")
    selected_id = str(skill_loader.get("selected") or "").strip()
    skills = list(skill_loader.get("skills") or [])
    if not selected_id:
        if not skills:
            raise ValueError("Skill加载器没有发现可用 Skill，请把 Skill 放入插件的 skills 目录。")
        catalogue = "\n".join(
            f'- {item["id"]}: {item["name"]}；{str(item.get("description") or "")[:500]}' for item in skills
        )
        messages = [
            {"role": "system", "content": "根据用户任务选择唯一最匹配的 Skill。只输出 Skill ID，不解释，不添加标点。"},
            {"role": "user", "content": f"可用 Skills：\n{catalogue}\n\n用户任务：\n{task}"},
        ]
        valid_ids = {item["id"] for item in skills}
        selected = ""
        for max_tokens in (512, 1024):
            selected = client.complete(
                messages,
                max_tokens,
                stage="Skill路由",
                allow_truncated=True,
            )
            selected_id = _解析skill选择(selected, valid_ids)
            if selected_id:
                break
        if not selected_id:
            preview = _脱敏文本(selected)[:120] or "<空输出>"
            raise ValueError(f"Skill路由失败：API 未返回唯一有效的 Skill ID，最后输出：{preview}。请在 Skill加载器中手动选择。")
    skill = 获取skill(selected_id)
    if skill is None:
        raise ValueError(f"找不到 Skill：{selected_id}，请刷新 Skill加载器。")
    return skill


def _自动选择references_api(client: _远程API客户端, skill: dict, task: str, n_ctx: int) -> list[str]:
    references = list(skill.get("references") or [])
    if not references:
        return []
    if len(references) == 1:
        return references
    catalogue = "\n".join(f"- {path}" for path in references)
    prompt = (
        "根据 Skill 工作流和当前任务，选择完成任务必须读取的 reference。"
        "只输出 JSON 字符串数组，元素必须来自候选路径；不需要 reference 时输出 []。\n\n"
        f"当前任务：\n{task}\n\n候选 reference：\n{catalogue}\n\nSkill：\n{读取skill正文(skill)}"
    )
    messages = [{"role": "user", "content": prompt}]
    required_tokens = _估算远程消息token数(messages)
    selected = ""
    last_error = None
    for max_tokens in (1024, 2048):
        _output_reserve, prompt_budget = _计算上下文预算(max_tokens, n_ctx)
        if required_tokens > prompt_budget:
            raise ValueError(
                f"Reference路由失败：reference 选择估算需要 {required_tokens} tokens，"
                f"超过可用输入上下文 {prompt_budget}。请提高 API上下文长度，或使用“加载全部”。"
            )
        selected = client.complete(
            messages,
            max_tokens,
            stage="Reference路由",
            allow_truncated=True,
        )
        try:
            return _解析reference选择(selected, references)
        except ValueError as exc:
            last_error = exc
    preview = _脱敏文本(selected)[:120] or "<空输出>"
    raise ValueError(f"Reference路由失败：两次请求均未返回有效 reference，最后输出：{preview}。") from last_error


def _API推理(client: _远程API客户端, messages: list[dict], settings: dict, stage: str = "最终生成") -> str:
    text = client.complete(messages, int(settings["最大生成token"]), settings=settings, stage=stage)
    return _清理最终文本(text.lstrip().removeprefix(": ").strip())


class APIAgentAPI配置:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "服务预设": (list(API服务预设), {"default": "通用 OpenAI Chat Completions"}),
                "API地址": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "填写 OpenAI 兼容基础地址（如 https://api.openai.com/v1）或完整端点。",
                    },
                ),
                "模型名称": ("STRING", {"default": "", "tooltip": "填写远程服务的模型名称。"}),
                "输出Token字段": (
                    ["自动选择", "max_tokens", "max_completion_tokens", "max_output_tokens"],
                    {
                        "default": "自动选择",
                        "tooltip": "Chat Completions 使用。通用 OpenAI 自动会为 GPT-5/o 系列选择 max_completion_tokens；业务 AzureOpenAI 预设自动使用 max_tokens。",
                    },
                ),
                "上下文长度": (
                    "INT",
                    {"default": 4096, "min": 4096, "max": 1048576, "step": 1024, "tooltip": "用于发送前的近似预算检查，不会修改服务端模型。"},
                ),
                "支持图片": ("BOOLEAN", {"default": True}),
                "图片细节": (["auto", "high", "low"], {"default": "auto"}),
                "请求超时秒": (
                    "INT",
                    {
                        "default": 10,
                        "min": 10,
                        "max": 600,
                        "step": 10,
                        "tooltip": "单次 HTTP 请求的最长等待时间；正在等待服务器返回时，ComfyUI 中断需要等请求返回或超时后才能生效。",
                    },
                ),
                "失败重试次数": ("INT", {"default": 1, "min": 0, "max": 3, "step": 1}),
                "发送高级采样参数": (
                    "BOOLEAN",
                    {"default": False, "tooltip": "仅 Chat Completions 接口使用。关闭兼容性最好。"},
                ),
            },
            "optional": {
                "API密钥": (
                    "STRING",
                    {
                        "default": "",
                        "password": True,
                        "tooltip": "可直接填写。该值会保存在 workflow JSON 中，但不会进入 API配置输出、运行信息或插件日志。",
                    },
                ),
            },
        }

    RETURN_TYPES = ("APIAGENT_API_CONFIG",)
    RETURN_NAMES = ("API配置",)
    FUNCTION = "run"
    CATEGORY = "APIAgent/API"

    def run(
        self,
        服务预设,
        API地址,
        模型名称,
        输出Token字段,
        上下文长度,
        支持图片,
        图片细节,
        请求超时秒,
        失败重试次数,
        发送高级采样参数,
        API密钥="",
    ):
        value = {
            "服务预设": 服务预设,
            "API地址": API地址,
            "模型名称": 模型名称,
            "输出Token字段": 输出Token字段,
            "上下文长度": int(上下文长度),
            "支持图片": bool(支持图片),
            "图片细节": 图片细节,
            "请求超时秒": int(请求超时秒),
            "失败重试次数": int(失败重试次数),
            "发送高级采样参数": bool(发送高级采样参数),
        }
        normalized = _规范化API配置(value)
        direct_reference = _API密钥缓存.store(API密钥)
        if direct_reference:
            normalized["直接密钥引用"] = direct_reference
        return (normalized,)


class APIAgentSkillAPI单次执行:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "API配置": ("APIAGENT_API_CONFIG",),
                "skill加载器": ("APIAGENT_SKILL",),
                "任务": ("STRING", {"default": "", "multiline": True}),
                "参考资料策略": (["按任务自动选择", "加载全部", "不加载"], {"default": "按任务自动选择"}),
                "缺失信息策略": (["自动采用合理默认值", "信息不足时报错"], {"default": "自动采用合理默认值"}),
                "H3格式自动校验": (
                    "BOOLEAN",
                    {"default": True, "tooltip": "关闭后跳过格式校验和自动修复；Skill 与必需写作规范仍会正常加载。"},
                ),
                "自动修复次数": ("INT", {"default": 1, "min": 0, "max": 2, "step": 1}),
                "最大生成token": (
                    "INT",
                    {
                        "default": 8192,
                        "min": 512,
                        "max": 32768,
                        "step": 512,
                        "tooltip": "最终生成和 H3 自动修复的输出预算；推理模型的隐藏推理 token 也可能占用该预算。",
                    },
                ),
            },
            "optional": {
                "图片": ("IMAGE", {"tooltip": "Picture 1；如果输入为批次，会按批次顺序继续展开。"}),
                "图片2": ("IMAGE", {"tooltip": "上一输入展开后继续编号。"}),
                "图片3": ("IMAGE", {"tooltip": "上一输入展开后继续编号。"}),
                "图片4": ("IMAGE", {"tooltip": "上一输入展开后继续编号。"}),
                "图片5": ("IMAGE", {"tooltip": "上一输入展开后继续编号。"}),
                "图片6": ("IMAGE", {"tooltip": "上一输入展开后继续编号。"}),
                "图片7": ("IMAGE", {"tooltip": "上一输入展开后继续编号。"}),
                "图片8": ("IMAGE", {"tooltip": "上一输入展开后继续编号。"}),
                "图片9": ("IMAGE", {"tooltip": "上一输入展开后继续编号；总数最多 9 张。"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("Skill结果", "API运行信息")
    FUNCTION = "run"
    CATEGORY = "APIAgent/Skill流水线"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def run(
        self,
        API配置,
        skill加载器,
        任务,
        参考资料策略,
        缺失信息策略,
        H3格式自动校验,
        自动修复次数,
        最大生成token=8192,
        图片=None,
        图片2=None,
        图片3=None,
        图片4=None,
        图片5=None,
        图片6=None,
        图片7=None,
        图片8=None,
        图片9=None,
    ):
        task = str(任务 or "").strip()
        if not task:
            raise ValueError("Skill API 单次执行的任务不能为空。")
        client = _远程API客户端(API配置)
        config = client.config
        settings = _默认单次设置()
        settings["最大生成token"] = int(最大生成token)
        n_ctx = int(config["上下文长度"])
        skill = _选择skill_api(client, skill加载器, task)

        images = _收集图片(图片, 图片2, 图片3, 图片4, 图片5, 图片6, 图片7, 图片8, 图片9)
        image_count = len(images)
        h3_mode = _解析h3模式(task) if skill["id"].startswith("h3-") else ""
        h3_duration = _解析h3时长(task) if h3_mode else 0.0

        if skill["id"] == 直播礼物SKILL_ID and 参考资料策略 != "不加载":
            reference_paths = _礼物h3_references(skill, task)
        elif 参考资料策略 == "加载全部":
            reference_paths = list(skill.get("references") or [])
        elif 参考资料策略 == "不加载":
            reference_paths = []
        elif skill["id"] == "h3-prompt-writing":
            reference_paths = _h3_reference(skill, task)
        else:
            reference_paths = _自动选择references_api(client, skill, task, n_ctx)

        if h3_mode:
            _检查h3图片数量(h3_mode, image_count)
        if image_count and not config["支持图片"]:
            raise RuntimeError("当前 API配置已关闭图片支持，请启用后重试，或使用纯文本任务。")

        system_text = _构建系统提示词(skill, reference_paths, 缺失信息策略, settings["系统提示词"])
        budget_messages = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": task, "images": [{}] * image_count},
        ]
        output_reserve, prompt_budget = _计算上下文预算(int(settings["最大生成token"]), n_ctx)
        required_tokens = _估算远程消息token数(budget_messages, image_count=image_count)
        if required_tokens > prompt_budget:
            raise ValueError(
                f"当前 Skill、reference、任务和图片估算需要 {required_tokens} tokens，超过可用输入上下文 {prompt_budget}。"
                "请提高 API配置中的上下文长度；H3 基础模式建议至少 16384，Ref2VA 多图建议至少 32768。"
            )
        settings["最大生成token"] = output_reserve
        messages = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": _构建用户内容(task, images, int(settings["最大边长"]))},
        ]
        print(f"[APIAgent API] 使用 {config['服务预设']} / {config['模型名称']}，输入约 {required_tokens} tokens。")
        result_text = _API推理(client, messages, settings)
        if result_text.startswith("QWEN_TE_INPUT_ERROR:"):
            raise ValueError(result_text.removeprefix("QWEN_TE_INPUT_ERROR:").strip())
        if skill["id"] == 直播礼物SKILL_ID and h3_mode:
            result_text, external_notice = _拆分礼物外部提示(result_text, h3_mode)
            if external_notice:
                print(f"[APIAgent API] 直播礼物外部提示：{external_notice}")

        if h3_mode and bool(H3格式自动校验):
            result_text, errors, warnings = 校验h3提示词(result_text, h3_mode, h3_duration, image_count, h3_mode == "Ref2VA")
            attempts = 0
            while errors and attempts < int(自动修复次数):
                repair_task = (
                    f"{task}\n\n以下是上一次生成的 H3 提示词：\n{result_text}\n\n"
                    "格式校验发现以下错误：\n- " + "\n- ".join(errors)
                    + "\n\n请依据当前 Skill 和 reference 修正全部错误，只返回完整的修正版最终提示词。"
                )
                repair_budget_messages = [
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": repair_task, "images": [{}] * image_count},
                ]
                repair_tokens = _估算远程消息token数(repair_budget_messages, image_count=image_count)
                if repair_tokens > prompt_budget:
                    raise ValueError("H3 输出格式错误且修复请求超出当前 API上下文：" + "；".join(errors))
                repair_messages = [
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": _构建用户内容(repair_task, images, int(settings["最大边长"]))},
                ]
                result_text = _API推理(client, repair_messages, settings, stage="H3自动修复")
                if result_text.startswith("QWEN_TE_INPUT_ERROR:"):
                    raise ValueError(result_text.removeprefix("QWEN_TE_INPUT_ERROR:").strip())
                if skill["id"] == 直播礼物SKILL_ID:
                    result_text, external_notice = _拆分礼物外部提示(result_text, h3_mode)
                    if external_notice:
                        print(f"[APIAgent API] 直播礼物外部提示：{external_notice}")
                result_text, errors, warnings = 校验h3提示词(
                    result_text, h3_mode, h3_duration, image_count, h3_mode == "Ref2VA"
                )
                attempts += 1
            if errors:
                raise ValueError("H3 提示词校验失败：" + "；".join(errors))
            for warning in warnings:
                print(f"[APIAgent API] H3 校验提示：{warning}")

        _中断检查()
        return result_text, client.summary()
