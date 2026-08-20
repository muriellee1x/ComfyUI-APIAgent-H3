# -*- coding: utf-8 -*-
import builtins
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
    直播礼物SKILL_IDS,
    直播礼物图像SKILL_IDS,
    低价直播礼物SKILL_ID,
    低价直播礼物图像SKILL_ID,
    直播礼物图像SKILL_ID,
    _h3_reference,
    _构建用户内容,
    _构建系统提示词,
    _构建图像礼物资源,
    _拆分礼物外部提示,
    _收集图片,
    _构建礼物资源,
    _检查h3图片数量,
    _清理最终文本,
    _礼物registry摘要,
    _解析h3时长,
    _解析h3模式,
    _解析礼物价格,
    _解析礼物registry选择,
    _解析reference选择,
    _计算上下文预算,
    _默认单次设置,
    规范化低价h3硬约束,
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
    _state = getattr(builtins, "_APIAGENT_H3_KEY_CACHE", None)
    if not isinstance(_state, dict):
        _state = {"values": {}, "lock": threading.Lock()}
        setattr(builtins, "_APIAGENT_H3_KEY_CACHE", _state)
    _values: dict[str, str] = _state["values"]
    _lock = _state["lock"]
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
            "上下文长度": int(value.get("上下文长度") or 119808),
            "支持图片": bool(value.get("支持图片", True)),
            "图片细节": str(value.get("图片细节") or "auto"),
            "请求超时秒": int(value.get("请求超时秒") or 300),
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
            "图像提示词修复": 0,
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
            for stage in ("Skill路由", "Reference路由", "最终生成", "H3自动修复", "图像提示词修复")
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
                f"超过可用输入上下文 {prompt_budget}。请提高 API上下文长度或缩减 Skill registry。"
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


def _自动选择礼物references_api(
    client: _远程API客户端,
    skill: dict,
    task: str,
    n_ctx: int,
    images: list[tuple[object, int]],
) -> tuple[list[str], dict]:
    prompt = (
        "你是直播礼物 Skill 的 Reference 路由器。根据任务、参考图片和 Skill 工作流，"
        "只选择最终生成确实需要读取的可选 registry 条目。必读价效、H3 和情感规则由后端加载，不要为它们选择条目。"
        "只输出严格 JSON 字符串数组，元素必须是下方 registry ID；可以输出 []。不要解释，不要使用 Markdown。\n\n"
        f"当前任务：\n{task}\n\nRegistry 摘要：\n{_礼物registry摘要(skill)}\n\n"
        f"Skill 工作流：\n{读取skill正文(skill)}"
    )
    # GPT-5 类推理模型会把隐藏推理计入输出预算；1024 可能在生成 JSON 前就耗尽。
    max_tokens = 4096
    budget_messages = [{"role": "user", "content": prompt, "images": [{}] * len(images)}]
    required_tokens = _估算远程消息token数(budget_messages, image_count=len(images))
    _output_reserve, prompt_budget = _计算上下文预算(max_tokens, n_ctx)
    report = {
        "requested": True,
        "image_count": len(images),
        "image_max_edge": 512 if images else None,
        "router_input_tokens_estimate": required_tokens,
    }
    if required_tokens > prompt_budget:
        raise ValueError(
            f"Reference 路由输入估算需要 {required_tokens} tokens，超过可用上下文 {prompt_budget}。"
        )
    messages = [{"role": "user", "content": _构建用户内容(prompt, images, 512)}]
    try:
        selected = client.complete(
            messages,
            max_tokens,
            stage="Reference路由",
            allow_truncated=True,
        )
        if not str(selected or "").strip():
            raise ValueError(
                "Reference 路由返回空文本；服务很可能在输出 JSON 前耗尽了 4096 token 路由预算。"
                "请确认业务模型允许至少 4096 个输出 token，或改用能够稳定返回短 JSON 的模型。"
            )
        try:
            selected_ids = _解析礼物registry选择(selected, skill)
        except ValueError as exc:
            preview = _脱敏文本(selected, client.api_key)[:300] or "<空输出>"
            raise ValueError(f"Reference 路由返回格式无效：{exc} 原始输出预览：{preview}") from exc
        report["router_selected"] = selected_ids
        return selected_ids, report
    except mm.InterruptProcessingException:
        raise
    except (ValueError, RuntimeError):
        raise


def _自动选择图像礼物references_api(
    client: _远程API客户端,
    skill: dict,
    task: str,
    reference_note: str,
    n_ctx: int,
    images: list[tuple[object, int]],
) -> tuple[list[str], dict]:
    prompt = (
        "你是直播礼物图像提示词 Skill 的 Reference 路由器。根据任务、参考图用途说明、参考图片和 Skill 工作流，"
        "只选择最终图像提示词确实需要读取的可选 registry 条目。价效、配色、提示词 pattern、情感和输出审计规则由后端必读，"
        "不要为它们选择条目。只有出现可见人物、服装、配饰、鞋履或人物妆造参考时才选择 wardrobe 条目。"
        "只输出严格 JSON 字符串数组，元素必须是下方 registry ID；可以输出 []。不要解释，不要使用 Markdown。\n\n"
        f"当前任务：\n{task}\n\n参考图用途说明：\n{reference_note or '未指定，由模型按图片内容判断。'}\n\n"
        f"Registry 摘要：\n{_礼物registry摘要(skill)}\n\nSkill 工作流：\n{读取skill正文(skill)}"
    )
    # GPT-5 类推理模型会把隐藏推理计入输出预算；1024 可能在生成 JSON 前就耗尽。
    max_tokens = 4096
    budget_messages = [{"role": "user", "content": prompt, "images": [{}] * len(images)}]
    required_tokens = _估算远程消息token数(budget_messages, image_count=len(images))
    _output_reserve, prompt_budget = _计算上下文预算(max_tokens, n_ctx)
    report = {
        "requested": True,
        "image_count": len(images),
        "image_max_edge": 512 if images else None,
        "router_input_tokens_estimate": required_tokens,
    }
    if required_tokens > prompt_budget:
        raise ValueError(f"Reference 路由输入估算需要 {required_tokens} tokens，超过可用上下文 {prompt_budget}。")
    messages = [{"role": "user", "content": _构建用户内容(prompt, images, 512)}]
    selected = client.complete(messages, max_tokens, stage="Reference路由", allow_truncated=True)
    if not str(selected or "").strip():
        raise ValueError(
            "Reference 路由返回空文本；服务很可能在输出 JSON 前耗尽了 4096 token 路由预算。"
            "请确认业务模型允许至少 4096 个输出 token，或改用能够稳定返回短 JSON 的模型。"
        )
    try:
        selected_ids = _解析礼物registry选择(selected, skill)
    except ValueError as exc:
        preview = _脱敏文本(selected, client.api_key)[:300] or "<空输出>"
        raise ValueError(f"Reference 路由返回格式无效：{exc} 原始输出预览：{preview}") from exc
    report["router_selected"] = selected_ids
    return selected_ids, report


def _检查参考图说明(reference_note: str, image_count: int) -> None:
    indexes = {
        int(value)
        for value in re.findall(r"(?:参考图|图片|picture|image)\s*#?\s*(\d+)", reference_note or "", re.IGNORECASE)
    }
    invalid = sorted(index for index in indexes if index < 1 or index > image_count)
    if invalid:
        raise ValueError(
            "参考图说明引用了未连接的图片："
            + "、".join(f"参考图{index}" for index in invalid)
            + f"；当前共连接 {image_count} 张图片。"
        )


def _解析JSON对象(text: str) -> dict:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", str(text or ""), flags=re.IGNORECASE).strip()
    lines = cleaned.splitlines()
    if len(lines) >= 2 and re.fullmatch(r"```(?:json|text)?", lines[0].strip(), re.IGNORECASE) and lines[-1].strip() == "```":
        cleaned = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(cleaned)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", cleaned):
        try:
            value, _end = decoder.raw_decode(cleaned[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("最终生成必须返回 JSON 对象。")


def _校验低价图像构图(zh_prompt: str, en_prompt: str, price: int) -> list[str]:
    errors = []
    if "主体位于画面中央" not in zh_prompt:
        errors.append("低价中文提示词必须明确写出“主体位于画面中央”")
    en_lower = en_prompt.lower()
    if "main subject centered in the frame" not in en_lower:
        errors.append("低价英文提示词必须明确写出“main subject centered in the frame”")

    combined = f"{zh_prompt}\n{en_prompt}"
    combined_lower = combined.lower()
    if price <= 499:
        if "画面为纯黑色背景" not in zh_prompt:
            errors.append("99–499 中文提示词必须明确写出“画面为纯黑色背景”")
        if "pure black background" not in en_lower:
            errors.append("99–499 英文提示词必须明确写出“pure black background”")
        forbidden_environment_patterns = (
            r"环境(?:为|是)",
            r"\benvironment\s+(?:is|of|with)\b",
            r"(?:建筑|远景|地平线|天气|环境光源?|场景空间)",
            r"(?:位于|坐落于|背景(?:中|里|为|是)?|场景(?:中|里|为|是)?).{0,16}(?:花园|舞台|街道)",
            r"(?:花园|舞台|街道).{0,8}(?:背景|环境|场景)",
            r"\b(?:architecture|distant view|horizon|weather|environmental light|scene space)\b",
            r"\b(?:garden|stage|street)\b.{0,24}\b(?:background|environment|scene)\b",
            r"\b(?:background|environment|scene)\b.{0,24}\b(?:garden|stage|street)\b",
        )
        if any(re.search(pattern, combined, flags=re.IGNORECASE) for pattern in forbidden_environment_patterns):
            errors.append("99–499 提示词不得使用环境开场或描述建筑、远景、地平线、天气、场景空间及环境光源")

        forbidden_backgrounds = (
            "纯白色背景",
            "纯白背景",
            "蓝色背景",
            "绿色背景",
            "红色背景",
            "彩色背景",
            "渐变背景",
            "透明背景",
        )
        if any(term in combined for term in forbidden_backgrounds) or re.search(
            r"\b(?:white|blue|green|red|colored|colourful|gradient|transparent)\s+background\b",
            combined_lower,
        ):
            errors.append("99–499 提示词不得指定非纯黑背景")
    else:
        complex_background_patterns = (
            r"(?:宏大|庞大|广阔|复杂|多层)(?:背景|环境|场景|建筑|舞台|空间|城市)|(?:城市全景|深远地平线|多个地点|复杂建筑群|拥挤群像|多层环境叙事)",
            r"\b(?:vast|grand|monumental|complex|elaborate|multi-layered)\s+(?:background|environment|scene|architecture|stage|space|cityscape)\b",
            r"\b(?:panoramic cityscape|deep horizon|multiple locations|crowded background group|multilayer environmental storytelling)\b",
        )
        if any(re.search(pattern, combined, flags=re.IGNORECASE) for pattern in complex_background_patterns):
            errors.append("500–999 只允许紧凑简单背景，不得描述复杂建筑、宏大空间、城市全景或多层环境叙事")

    if re.search(r"偏左|偏右|画面(?:左|右)侧|主体(?:位于|放在)一侧|off[- ]center|(?:left|right) side of the frame", combined, re.IGNORECASE):
        errors.append("低价主体或主体组合必须居中，不得使用偏置构图")
    return errors


def _校验高价人物构图(zh_prompt: str, en_prompt: str) -> list[str]:
    errors = []
    combined = f"{zh_prompt}\n{en_prompt}"
    human_terms_zh = r"人物|人类|角色|女性|男性|女人|男人|少女|少年|女孩|男孩|公主|王子|女王|皇后|国王|帝王|主播|演员|舞者|歌手|新娘|新郎|女神|仙女|骑士|武士|法师"
    human_terms_en = r"\b(?:person|people|human|character|woman|women|man|men|girl|boy|princess|prince|queen|king|empress|emperor|host|actor|actress|dancer|singer|bride|groom|goddess|fairy|knight|warrior|mage)\b"
    has_person = bool(
        "w+girl" in combined
        or "w+boy" in combined
        or re.search(human_terms_zh, combined)
        or re.search(human_terms_en, combined, re.IGNORECASE)
    )
    if not has_person:
        return errors

    if "w+girl" not in combined and "w+boy" not in combined:
        errors.append("高价提示词出现可见人物时必须包含对应的 w+girl 或 w+boy 触发词")

    zh_crops = (
        "胸像近景",
        "胸部以上近景",
        "半身近景",
        "上半身近景",
        "腰部以上近景",
        "大腿以上近景",
        "膝上近景",
        "膝盖以上近景",
        "小腿以上近景",
    )
    en_crops = (
        "bust close-up",
        "chest-up close-up",
        "half-body close-up",
        "upper-body close-up",
        "waist-up close-up",
        "thigh-up close-up",
        "knee-up close-up",
        "calf-up close-up",
    )
    if not any(term in zh_prompt for term in zh_crops):
        errors.append("高价中文人物提示词必须明确胸像至小腿以上范围内的近景裁切")
    en_lower = en_prompt.lower()
    if not any(term in en_lower for term in en_crops):
        errors.append("高价英文人物提示词必须明确 bust 至 calf-up 范围内的 close-up 裁切")

    zh_prominence = ("人物占据画面主要区域", "每个可见人物都占据画面主要区域", "人物主体占据画面主要区域")
    en_prominence = ("occupies most of the frame", "occupy most of the frame", "fills most of the frame", "fill most of the frame")
    if not any(term in zh_prompt for term in zh_prominence):
        errors.append("高价中文人物提示词必须明确人物占据画面主要区域")
    if not any(term in en_lower for term in en_prominence):
        errors.append("高价英文人物提示词必须明确人物 occupies most of the frame")

    if not any(term in zh_prompt for term in ("脚部不入镜", "脚部不可见", "脚部位于画面外")):
        errors.append("高价中文人物提示词必须明确脚部不入镜")
    if "feet out of frame" not in en_lower:
        errors.append("高价英文人物提示词必须明确 feet out of frame")

    forbidden_patterns = (
        r"人物全身图|完整全身|全身入镜|从头到脚|脚部入镜|脚部可见|鞋履可见|远景人物|背景人物|人物(?:很小|较小)|小比例人物",
        r"\bfull[- ]body\b|\bhead[- ]to[- ]toe\b|\bfeet visible\b|\bvisible feet\b|\ba[- ]pose\b",
        r"\b(?:long|wide) shot\b|\b(?:small|tiny|distant|background) figure\b|\bsmall in the frame\b",
    )
    if any(re.search(pattern, combined, flags=re.IGNORECASE) for pattern in forbidden_patterns):
        errors.append("高价人物提示词不得出现全身、脚部可见、A-pose、远景或小比例人物表达")
    return errors


def _校验图像提示词结果(
    text: str,
    image_count: int,
    skill_id: str = "",
    task: str = "",
) -> tuple[dict, list[str]]:
    errors = []
    try:
        value = _解析JSON对象(text)
    except ValueError as exc:
        return {}, [str(exc)]

    analysis = value.get("reference_analysis")
    if not isinstance(analysis, list):
        errors.append("reference_analysis 必须是数组")
        analysis = []
    if image_count == 0 and analysis:
        errors.append("没有连接参考图时 reference_analysis 必须为空数组")
    if image_count > 0:
        indexes = []
        required_fields = ("composition", "lighting", "color", "time_atmosphere", "scene", "props", "people")
        for position, item in enumerate(analysis, start=1):
            if not isinstance(item, dict):
                errors.append(f"reference_analysis 第 {position} 项必须是对象")
                continue
            try:
                index = int(item.get("image_index"))
            except (TypeError, ValueError):
                index = -1
            indexes.append(index)
            if not isinstance(item.get("declared_role", ""), str):
                errors.append(f"参考图 {index if index > 0 else position} 的 declared_role 必须是字符串")
            for field in required_fields:
                if not isinstance(item.get(field), str) or not str(item.get(field)).strip():
                    errors.append(f"参考图 {index if index > 0 else position} 缺少 {field} 分析")
        expected = list(range(1, image_count + 1))
        if sorted(indexes) != expected:
            errors.append(f"reference_analysis 必须且只能覆盖参考图 {expected}，当前为 {indexes}")

    fusion_strategy = value.get("fusion_strategy")
    if not isinstance(fusion_strategy, str):
        errors.append("fusion_strategy 必须是字符串")
    elif image_count > 1 and not fusion_strategy.strip():
        errors.append("多图输入时 fusion_strategy 不能为空")

    prompts = {}
    for field, label in (("zh_prompt", "中文提示词"), ("en_prompt", "英文提示词")):
        prompt = value.get(field)
        if not isinstance(prompt, str) or not prompt.strip():
            errors.append(f"{label}不能为空")
            prompts[field] = ""
            continue
        prompt = prompt.strip()
        if "\n" in prompt or prompt.startswith(("#", "```")) or prompt.endswith("```"):
            errors.append(f"{label}必须是无标题、无代码围栏的单段文本")
        prompts[field] = prompt

    trigger_names = ("w+style", "w+girl", "w+boy")
    zh_counts = {name: prompts.get("zh_prompt", "").count(name) for name in trigger_names}
    en_counts = {name: prompts.get("en_prompt", "").count(name) for name in trigger_names}
    if not any(zh_counts.values()):
        errors.append("中文提示词缺少 W+ 触发词")
    if zh_counts != en_counts:
        errors.append(f"中英文 W+ 触发词数量不一致：中文 {zh_counts}，英文 {en_counts}")

    if skill_id == 低价直播礼物图像SKILL_ID:
        errors.extend(
            _校验低价图像构图(
                prompts.get("zh_prompt", ""),
                prompts.get("en_prompt", ""),
                _解析礼物价格(task),
            )
        )
    elif skill_id == 直播礼物图像SKILL_ID:
        errors.extend(_校验高价人物构图(prompts.get("zh_prompt", ""), prompts.get("en_prompt", "")))

    value["reference_analysis"] = analysis
    value["fusion_strategy"] = fusion_strategy if isinstance(fusion_strategy, str) else ""
    value.update(prompts)
    return value, errors


def _格式化图像提示词报告(report: dict) -> str:
    return "图像提示词报告：\n" + json.dumps(report, ensure_ascii=False, indent=2)


def _API推理(client: _远程API客户端, messages: list[dict], settings: dict, stage: str = "最终生成") -> str:
    text = client.complete(messages, int(settings["最大生成token"]), settings=settings, stage=stage)
    return _清理最终文本(text.lstrip().removeprefix(": ").strip())


def _格式化H3校验报告(report: dict) -> str:
    return "H3校验报告：\n" + json.dumps(report, ensure_ascii=False, indent=2)


def _格式化Skill上下文报告(report: dict) -> str:
    return "Skill上下文报告：\n" + json.dumps(report, ensure_ascii=False, indent=2)


def _准备低价背景色任务(skill_id: str, task: str, raw_color: str) -> tuple[str, dict]:
    input_color = str(raw_color or "").strip()
    price = _解析礼物价格(task)
    cleaned_task = re.sub(
        r"\s*\[APIAGENT_GIFT_BG_COLOR=[^\]\r\n]*\]\s*",
        "\n",
        task,
        flags=re.IGNORECASE,
    ).strip()
    report = {
        "input": input_color,
        "normalized": None,
        "defaulted": False,
        "applied": False,
        "reason": "",
    }
    if skill_id != 低价直播礼物SKILL_ID:
        report["reason"] = "当前不是低价直播礼物视频 Skill，背景色输入未应用。" if input_color else "当前 Skill 不使用低价固定背景色。"
        return cleaned_task, report

    if not 99 <= price <= 999:
        report["reason"] = f"任务价格 {price} 不在低价 Skill 的 99–999 范围。"
        return cleaned_task, report

    if price <= 499 and not input_color:
        normalized = "#00FF00"
        report["defaulted"] = True
        report["reason"] = "99–499 未填写色值，使用默认低价抠像绿 #00FF00。"
    elif not input_color:
        report["reason"] = "500–999 未填写色值，保留紧凑场景或普通纯色背景策略。"
        return cleaned_task, report
    elif not re.fullmatch(r"#[0-9A-Fa-f]{6}", input_color):
        raise ValueError("低价固定背景色必须是六位标准 HEX 色值，例如 #00FF00。")
    else:
        normalized = input_color.upper()
        report["reason"] = "使用用户提供的低价固定背景色。"

    report["normalized"] = normalized
    report["applied"] = True
    effective_task = (
        f"{cleaned_task}\n\n[APIAGENT_GIFT_BG_COLOR={normalized}]\n"
        f"低价固定背景色：{normalized}。该色值是背景的唯一权威值；背景必须覆盖全画面，"
        "从首帧到末帧保持相同色相、亮度、纹理和覆盖范围，前景效果不得重染背景。"
    )
    return effective_task, report


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
                    {"default": 119808, "min": 4096, "max": 1048576, "step": 1024, "tooltip": "用于发送前的近似预算检查，不会修改服务端模型。"},
                ),
                "支持图片": ("BOOLEAN", {"default": True}),
                "图片细节": (["auto", "high", "low"], {"default": "auto"}),
                "请求超时秒": (
                    "INT",
                    {
                        "default": 300,
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
                "H3格式自动校验": (
                    "BOOLEAN",
                    {"default": True, "tooltip": "生成后校验 H3 格式；失败时按自动修复次数再次调用 API，并把校验报告写入 API运行信息。关闭后跳过校验和修复。"},
                ),
                "自动修复次数": (
                    "INT",
                    {"default": 1, "min": 0, "max": 2, "step": 1, "tooltip": "H3 校验失败后最多追加调用 API 的次数。"},
                ),
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
                "低价固定背景色": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "99–499 留空时使用 #00FF00；500–999 留空时不启用固定背景。非空值必须为 #RRGGBB。",
                    },
                ),
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
        H3格式自动校验,
        自动修复次数,
        最大生成token=8192,
        低价固定背景色="",
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
        if skill["id"] in 直播礼物图像SKILL_IDS:
            raise ValueError("当前连接的是图像提示词 Skill，请改用 APIAgent 图像Skill单次执行节点。")
        task, background_color_report = _准备低价背景色任务(skill["id"], task, 低价固定背景色)

        images = _收集图片(图片, 图片2, 图片3, 图片4, 图片5, 图片6, 图片7, 图片8, 图片9)
        image_count = len(images)
        h3_mode = _解析h3模式(task) if skill["id"].startswith("h3-") else ""
        h3_duration = _解析h3时长(task) if h3_mode else 0.0
        if h3_mode:
            _检查h3图片数量(h3_mode, image_count)
        if image_count and not config["支持图片"]:
            raise RuntimeError("当前 API配置已关闭图片支持，请启用后重试，或使用纯文本任务。")
        validation_report = {
            "enabled": bool(H3格式自动校验),
            "executed": False,
            "valid": None,
            "mode": h3_mode,
            "duration": round(h3_duration, 2) if h3_mode else None,
            "image_count": image_count,
            "repair_attempts": 0,
            "initial_errors": [],
            "final_errors": [],
            "warnings": [],
        }
        if not h3_mode:
            validation_report["reason"] = "当前任务未识别为 H3 模式"
        elif not bool(H3格式自动校验):
            validation_report["reason"] = "H3格式自动校验已关闭"

        context_report = {
            "policy": "必读规则 + 自动选择 Reference",
            "skill_id": skill["id"],
            "background_color_input": background_color_report,
        }
        if skill["id"] in 直播礼物SKILL_IDS:
            selected_ids, route_report = _自动选择礼物references_api(client, skill, task, n_ctx, images)
            reference_paths, gift_context = _构建礼物资源(skill, task, selected_ids)
            context_report.update(gift_context)
            context_report["route"] = route_report
        elif skill["id"] == "h3-prompt-writing":
            reference_paths = _h3_reference(skill, task)
        else:
            reference_paths = _自动选择references_api(client, skill, task, n_ctx)
        if skill["id"] not in 直播礼物SKILL_IDS:
            context_report.update(
                {
                    "loaded_references": [
                        item.get("label") if isinstance(item, dict) else str(item) for item in reference_paths
                    ],
                    "injected_characters": sum(
                        len(str(item.get("content") or "")) if isinstance(item, dict) else len(str(item))
                        for item in reference_paths
                    ),
                }
            )

        system_text = _构建系统提示词(skill, reference_paths, settings["系统提示词"])
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
        if skill["id"] in 直播礼物SKILL_IDS and h3_mode:
            result_text, external_notice = _拆分礼物外部提示(result_text, h3_mode)
            if external_notice:
                print(f"[APIAgent API] 直播礼物外部提示：{external_notice}")
            result_text = 规范化低价h3硬约束(result_text, h3_mode, skill["id"], task)

        if h3_mode and bool(H3格式自动校验):
            result_text, errors, warnings = 校验h3提示词(
                result_text,
                h3_mode,
                h3_duration,
                image_count,
                h3_mode == "Ref2VA",
                skill["id"],
                task,
            )
            validation_report["executed"] = True
            validation_report["initial_errors"] = list(errors)
            attempts = 0
            while errors and attempts < int(自动修复次数):
                low_tier_fix = ""
                if skill["id"] == 低价直播礼物SKILL_ID:
                    color_match = re.search(
                        r"\[APIAGENT_GIFT_BG_COLOR=(#[0-9A-Fa-f]{6})\]",
                        task,
                        re.IGNORECASE,
                    )
                    color = color_match.group(1).upper() if color_match else ""
                    low_tier_fix = (
                        "\n\n低价硬格式：overall_soundscape 和 non_diegetic_music 的字段正文必须分别严格为 N/A，"
                        "不得追加解释。"
                    )
                    if color:
                        low_tier_fix += (
                            "在主描述字段中原样包含以下英文约束：\n"
                            f"The exact {color} background is a uniform solid-color, texture-free field that fills the entire frame. "
                            "Its hue, luminance, texture, and coverage remain unchanged from the first frame through the final frame."
                        )
                repair_task = (
                    f"{task}\n\n以下是上一次生成的 H3 提示词：\n{result_text}\n\n"
                    "格式校验发现以下错误：\n- " + "\n- ".join(errors)
                    + low_tier_fix
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
                if skill["id"] in 直播礼物SKILL_IDS:
                    result_text, external_notice = _拆分礼物外部提示(result_text, h3_mode)
                    if external_notice:
                        print(f"[APIAgent API] 直播礼物外部提示：{external_notice}")
                    result_text = 规范化低价h3硬约束(result_text, h3_mode, skill["id"], task)
                result_text, errors, warnings = 校验h3提示词(
                    result_text,
                    h3_mode,
                    h3_duration,
                    image_count,
                    h3_mode == "Ref2VA",
                    skill["id"],
                    task,
                )
                attempts += 1
            validation_report["repair_attempts"] = attempts
            validation_report["final_errors"] = list(errors)
            validation_report["warnings"] = list(warnings)
            validation_report["valid"] = not errors
            if errors:
                raise ValueError(
                    f"H3 提示词校验失败（自动修复 {attempts} 次后仍未通过）：" + "；".join(errors)
                )
            for warning in warnings:
                print(f"[APIAgent API] H3 校验提示：{warning}")

        _中断检查()
        return (
            result_text,
            client.summary()
            + "\n\n"
            + _格式化Skill上下文报告(context_report)
            + "\n\n"
            + _格式化H3校验报告(validation_report),
        )


class APIAgent图像SkillAPI单次执行:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "API配置": ("APIAGENT_API_CONFIG",),
                "skill加载器": ("APIAGENT_SKILL",),
                "任务": ("STRING", {"default": "", "multiline": True}),
                "最大生成token": (
                    "INT",
                    {
                        "default": 8192,
                        "min": 512,
                        "max": 32768,
                        "step": 512,
                        "tooltip": "结构化参考图分析和中英文提示词的总输出预算。",
                    },
                ),
            },
            "optional": {
                "参考图说明": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "可指定每张图的用途，例如：参考图1用于角色妆造，参考图2用于场景。留空时由模型判断。",
                    },
                ),
                "图片": ("IMAGE", {"tooltip": "参考图1；图片只作为主体、妆造、场景、材质、风格或构图参考。"}),
                "图片2": ("IMAGE", {"tooltip": "参考图2。"}),
                "图片3": ("IMAGE", {"tooltip": "参考图3。"}),
                "图片4": ("IMAGE", {"tooltip": "参考图4。"}),
                "图片5": ("IMAGE", {"tooltip": "参考图5。"}),
                "图片6": ("IMAGE", {"tooltip": "参考图6。"}),
                "图片7": ("IMAGE", {"tooltip": "参考图7。"}),
                "图片8": ("IMAGE", {"tooltip": "参考图8。"}),
                "图片9": ("IMAGE", {"tooltip": "参考图9；总数最多 9 张。"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("中文提示词", "英文提示词", "API运行信息")
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
        最大生成token=8192,
        参考图说明="",
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
            raise ValueError("图像 Skill API 单次执行的任务不能为空。")
        reference_note = str(参考图说明 or "").strip()
        images = _收集图片(图片, 图片2, 图片3, 图片4, 图片5, 图片6, 图片7, 图片8, 图片9)
        image_count = len(images)
        _检查参考图说明(reference_note, image_count)

        client = _远程API客户端(API配置)
        config = client.config
        if image_count and not config["支持图片"]:
            raise RuntimeError("当前 API配置已关闭图片支持，请启用后重试，或移除参考图片。")
        settings = _默认单次设置()
        settings["最大生成token"] = int(最大生成token)
        n_ctx = int(config["上下文长度"])
        selection_task = task + "\n\n当前执行节点要求选择 output_kind=bilingual_image_prompt 的直播礼物图像提示词 Skill。"
        skill = _选择skill_api(client, skill加载器, selection_task)
        if skill["id"] not in 直播礼物图像SKILL_IDS or skill.get("manifest", {}).get("output_kind") != "bilingual_image_prompt":
            raise ValueError(
                f"图像 Skill 单次执行节点不能执行 {skill['id']}；请连接构建器的图像Skill路由或选择图像提示词 Skill。"
            )

        selected_ids, route_report = _自动选择图像礼物references_api(
            client,
            skill,
            task,
            reference_note,
            n_ctx,
            images,
        )
        reference_paths, context_report = _构建图像礼物资源(skill, task, selected_ids)
        context_report.update(
            {
                "policy": "必读图像规则 + 自动选择 Reference",
                "skill_id": skill["id"],
                "reference_note": reference_note,
                "route": route_report,
            }
        )
        system_text = _构建系统提示词(skill, reference_paths, settings["系统提示词"])
        if skill["id"] == 低价直播礼物图像SKILL_ID:
            gift_price = _解析礼物价格(task)
            if gift_price <= 499:
                profile_instruction = (
                    "当前为 99–499 低价图像 Skill：最终中英文提示词只能描述居中的主体或主体组合，使用连续、均匀、无纹理的纯黑背景，"
                    "不得保留参考图或任务中的环境。中文必须逐字包含‘主体位于画面中央’和‘画面为纯黑色背景’；"
                    "英文必须逐字包含‘main subject centered in the frame’和‘pure black background’。"
                    "不得使用‘环境为/环境是/environment is’，不得描述建筑、远景、地平线、天气、场景空间或环境光源。"
                )
            else:
                profile_instruction = (
                    "当前为 500–999 低价图像 Skill：最终中英文提示词必须保持主体或主体组合居中，"
                    "中文必须逐字包含‘主体位于画面中央’，英文必须逐字包含‘main subject centered in the frame’。"
                    "不强制纯黑背景；可以继续使用黑底，也可以保留或构建一处服务主题的紧凑简单背景。"
                    "背景只能提供必要承托和氛围，不得扩展成复杂建筑群、宏大舞台、城市全景、深远地平线、多个地点、"
                    "拥挤群像或多层环境叙事，且不得让主体成为背景小元素。"
                )
        else:
            profile_instruction = (
                "当前为高价图像 Skill：如有可见人物，只允许胸像、半身、腰部以上、大腿以上、膝上或小腿以上近景，"
                "小腿是最大可见范围，脚部必须在画面外，每个可见人物都必须占据画面主要区域。"
                "即使任务或参考图要求全身，也必须改为小腿以上或更近裁切；禁止全身、从头到脚、A-pose、远景、宽景和背景小人物。"
                "中文必须明确合法近景裁切、‘人物占据画面主要区域’和‘脚部不入镜’；英文必须明确对应 close-up、"
                "‘occupies most of the frame’和‘feet out of frame’。无人画面不添加人物。"
            )
        generation_task = (
            f"{task}\n\n参考图用途说明：\n{reference_note or '未指定，由你根据每张参考图内容判断。'}\n\n"
            f"{profile_instruction}\n\n"
            "请先逐张完成参考图结构化分析，再融合成一组直播礼物图像提示词。图片只作软参考，不得解释为精确首帧、尾帧或逐像素复刻。"
            "只返回一个 JSON 对象，不要 Markdown、代码围栏或额外文字。JSON 必须使用以下结构：\n"
            '{"reference_analysis":[{"image_index":1,"declared_role":"","composition":"","lighting":"",'
            '"color":"","time_atmosphere":"","scene":"","props":"","people":""}],'
            '"fusion_strategy":"","zh_prompt":"","en_prompt":""}\n'
            f"当前共连接 {image_count} 张参考图。没有图片时 reference_analysis 必须为 []；"
            "有图片时必须按 1 到图片总数逐张分析且每个分析字段非空。中文和英文提示词都必须是单段纯文本，"
            "英文是中文设计的忠实翻译，并保持 w+style、w+girl、w+boy 触发词数量一致。"
        )
        budget_messages = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": generation_task, "images": [{}] * image_count},
        ]
        output_reserve, prompt_budget = _计算上下文预算(int(settings["最大生成token"]), n_ctx)
        required_tokens = _估算远程消息token数(budget_messages, image_count=image_count)
        if required_tokens > prompt_budget:
            raise ValueError(
                f"当前图像 Skill、规则、Reference、任务和图片估算需要 {required_tokens} tokens，"
                f"超过可用输入上下文 {prompt_budget}。请提高 API配置中的上下文长度。"
            )
        settings["最大生成token"] = output_reserve
        messages = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": _构建用户内容(generation_task, images, int(settings["最大边长"]))},
        ]
        print(f"[APIAgent API] 使用 {config['服务预设']} / {config['模型名称']}，输入约 {required_tokens} tokens。")
        result_text = _API推理(client, messages, settings)
        result, errors = _校验图像提示词结果(result_text, image_count, skill["id"], task)
        initial_errors = list(errors)
        repair_attempts = 0
        if errors:
            repair_task = (
                f"{generation_task}\n\n上一次返回：\n{result_text}\n\n校验错误：\n- "
                + "\n- ".join(errors)
                + "\n请修复全部错误，只返回完整 JSON 对象。"
            )
            repair_budget_messages = [
                {"role": "system", "content": system_text},
                {"role": "user", "content": repair_task, "images": [{}] * image_count},
            ]
            repair_tokens = _估算远程消息token数(repair_budget_messages, image_count=image_count)
            if repair_tokens > prompt_budget:
                raise ValueError("图像提示词格式错误且修复请求超出当前 API上下文：" + "；".join(errors))
            repair_messages = [
                {"role": "system", "content": system_text},
                {"role": "user", "content": _构建用户内容(repair_task, images, int(settings["最大边长"]))},
            ]
            result_text = _API推理(client, repair_messages, settings, stage="图像提示词修复")
            result, errors = _校验图像提示词结果(result_text, image_count, skill["id"], task)
            repair_attempts = 1
        if errors:
            raise ValueError("图像提示词校验失败（自动修复 1 次后仍未通过）：" + "；".join(errors))

        prompt_report = {
            "valid": True,
            "image_count": image_count,
            "reference_analysis": result["reference_analysis"],
            "fusion_strategy": result["fusion_strategy"],
            "repair_attempts": repair_attempts,
            "initial_errors": initial_errors,
            "final_errors": [],
        }
        _中断检查()
        return (
            result["zh_prompt"],
            result["en_prompt"],
            client.summary()
            + "\n\n"
            + _格式化Skill上下文报告(context_report)
            + "\n\n"
            + _格式化图像提示词报告(prompt_report),
        )
