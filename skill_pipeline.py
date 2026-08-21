# -*- coding: utf-8 -*-
import base64
import io
import json
import re

from PIL import Image

from .skill_loader import 构建skill选择, 读取reference, 读取skill正文


H3模式 = ("T2VA", "I2VA", "FL2VA", "L2VA", "Ref2VA")
H3基础字段 = (
    "integrated_multimodal_description",
    "overall_soundscape",
    "non_diegetic_music",
)
H3全参考字段 = (
    "subject_definitions",
    "summary",
    "retention_analysis",
    "detailed_description",
    "overall_soundscape",
    "non_diegetic_music",
)

低价直播礼物SKILL_ID = "h3-low-coin-gift-director"
直播礼物SKILL_ID = "h3-live-gift-director"
直播礼物SKILL_IDS = {低价直播礼物SKILL_ID, 直播礼物SKILL_ID}
低价直播礼物图像SKILL_ID = "image-low-coin-gift-prompt-director"
直播礼物图像SKILL_ID = "image-live-gift-prompt-director"
直播礼物图像SKILL_IDS = {低价直播礼物图像SKILL_ID, 直播礼物图像SKILL_ID}
直播礼物情感 = ("趣味", "彰显", "应援", "惊喜")
直播礼物价效规则 = "rules/price-effect-system.md"
低价直播礼物价效配置 = "rules/price-effect-profile.json"
低价直播礼物背景规则 = "rules/constant-solid-background.md"
直播礼物情感规则 = "rules/emotion-rules.md"
直播礼物基础规范 = "rules/h3-prompt-writing-base-en.txt"
直播礼物全参考规范 = "rules/h3-prompt-writing-ref-en.txt"
直播礼物图像必读规则 = (
    直播礼物价效规则,
    "rules/color-style-rules.md",
    "rules/prompt-patterns.md",
    直播礼物情感规则,
    "rules/prompt-logic-audit.md",
)

无状态SKILL执行协议 = """
你正在通过 ComfyUI 的无状态 Skill 执行器工作。严格遵循当前 Skill 和已加载 reference，并遵守以下规则：
1. 本次调用必须在一轮内交付可直接传给下游节点的最终文本产物。不要提问，不要等待确认，不要输出选项或流程状态标记。
2. 如果 Skill 包含确认门或分阶段流程，把任务中已经提供的参数视为已确认。信息不足时遵循 Skill 自身的默认值和错误规则。
3. 已加载 reference 就是本次可用的完整参考资料。不要请求再次加载文件，也不要猜测未加载文件的内容。
4. Skill 提到画布、媒体生成、联网工具或外部 agent 时，只输出当前节点能够完成的文本产物、提示词或执行方案，不得声称已经调用外部能力。
5. 只输出最终产物本身，不要解释执行过程，不要使用 Markdown 代码围栏，不要追加任何执行器状态标签。
""".strip()


def _清洗think块文本(text: str) -> str:
    return re.sub(r"<think>[\s\S]*?</think>", "", str(text or ""), flags=re.IGNORECASE).strip()


def _计算上下文预算(max_tokens: int, n_ctx: int) -> tuple[int, int]:
    output_reserve = max(1, min(int(max_tokens), max(1, int(n_ctx) - 512)))
    prompt_budget = max(1, int(n_ctx) - output_reserve)
    return output_reserve, prompt_budget


def _批量图片索引转base64(image_tensor, index: int, 最大边长: int) -> str:
    if image_tensor is None:
        return ""
    array = image_tensor[int(index)].detach().cpu().numpy()
    array = (array.clip(0, 1) * 255).astype("uint8")
    pil = Image.fromarray(array)
    max_edge = max(128, int(最大边长))
    width, height = pil.size
    longest = max(width, height)
    if longest > max_edge:
        scale = max_edge / longest
        pil = pil.resize((max(1, round(width * scale)), max(1, round(height * scale))), Image.Resampling.LANCZOS)
    if pil.mode != "RGB":
        pil = pil.convert("RGB")
    buffer = io.BytesIO()
    pil.save(buffer, format="JPEG", quality=90, optimize=True, progressive=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _默认单次设置() -> dict:
    return {
        "系统提示词": "",
        "最大生成token": 4096,
        "温度": 0.7,
        "top_p": 0.9,
        "top_k": 20,
        "重复惩罚": 1.0,
        "频率惩罚": 0.0,
        "存在惩罚": 0.0,
        "seed": 0,
        "输出think块": False,
        "最大边长": 1024,
    }


def _解析h3模式(text: str) -> str:
    marker = re.search(r"\[(?:APIAGENT|QWEN_TE)_H3_MODE=(T2VA|I2VA|FL2VA|L2VA|Ref2VA)\]", text or "", re.IGNORECASE)
    if marker:
        value = marker.group(1)
        return "Ref2VA" if value.lower() == "ref2va" else value.upper()
    match = re.search(r"(?<![A-Za-z0-9])(Ref2VA|FL2VA|I2VA|L2VA|T2VA)(?![A-Za-z0-9])", text or "", re.IGNORECASE)
    if not match:
        return ""
    value = match.group(1)
    return "Ref2VA" if value.lower() == "ref2va" else value.upper()


def _解析h3时长(text: str) -> float:
    marker = re.search(r"\[(?:APIAGENT|QWEN_TE)_H3_DURATION=([0-9]+(?:\.[0-9]+)?)\]", text or "", re.IGNORECASE)
    if marker:
        return float(marker.group(1))
    match = re.search(r"(?:有效时长|视频时长|duration)\s*[：:=]\s*([0-9]+(?:\.[0-9]+)?)", text or "", re.IGNORECASE)
    return float(match.group(1)) if match else 0.0


def _对齐h3时长(duration: float) -> tuple[int, float]:
    requested_frames = max(5, round(float(duration) * 24.0))
    aligned_frames = requested_frames + (5 - requested_frames % 17) % 17
    aligned_frames = min(aligned_frames, 3592)
    return aligned_frames, aligned_frames / 24.0


def _解析礼物价格(text: str) -> int:
    marker = re.search(r"\[APIAGENT_GIFT_PRICE=(\d+)\]", text or "", re.IGNORECASE)
    if marker:
        return int(marker.group(1))
    match = re.search(r"礼物价格\s*[：:=]\s*(\d+)", text or "")
    return int(match.group(1)) if match else -1


def _解析礼物背景色(text: str) -> str:
    marker = re.search(r"\[APIAGENT_GIFT_BG_COLOR=(#[0-9A-Fa-f]{6})\]", text or "", re.IGNORECASE)
    return marker.group(1).upper() if marker else ""


def _解析礼物情感(text: str) -> str:
    marker = re.search(r"\[APIAGENT_GIFT_EMOTION=([^\]\r\n]+)\]", text or "", re.IGNORECASE)
    value = marker.group(1).strip() if marker else ""
    if not value:
        match = re.search(r"情感表达\s*[：:=]\s*([^\r\n]+)", text or "")
        value = match.group(1).strip() if match else ""
    return value if value in 直播礼物情感 else ""


def _解析礼物画幅(text: str) -> str:
    marker = re.search(r"\[APIAGENT_GIFT_ASPECT=([^\]\r\n]+)\]", text or "", re.IGNORECASE)
    if marker:
        return marker.group(1).strip()
    match = re.search(r"(?:有效画幅比例|画幅比例)\s*[：:=]\s*([^\s\r\n]+)", text or "")
    return match.group(1).strip() if match else ""


def _解析礼物镜头数(text: str) -> int:
    marker = re.search(r"\[APIAGENT_GIFT_SHOTS=(\d+)\]", text or "", re.IGNORECASE)
    return int(marker.group(1)) if marker else 0


def _礼物有效规格(price: int, requested_duration: float) -> tuple[int, float]:
    if 99 <= price <= 299:
        return 73, 73 / 24.0
    if 300 <= price <= 999:
        return 90, 90 / 24.0
    return _对齐h3时长(requested_duration)


def _清理最终文本(text: str) -> str:
    cleaned = _清洗think块文本(str(text or "")).replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n").strip()
    cleaned = re.sub(r"\s*<qwen_te_state>\s*\{[\s\S]*?\}\s*</qwen_te_state>\s*$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"<(/?)d>", lambda match: f"<{match.group(1)}d>", cleaned, flags=re.IGNORECASE)
    lines = cleaned.splitlines()
    if len(lines) >= 2 and re.fullmatch(r"\s*```(?:text|markdown|md)?\s*", lines[0], re.IGNORECASE) and re.fullmatch(r"\s*```\s*", lines[-1]):
        cleaned = "\n".join(lines[1:-1]).strip()
    field_names = "|".join(re.escape(name) for name in set(H3基础字段 + H3全参考字段))
    cleaned = re.sub(rf"(?m)^[ \t]*\*\*({field_names})\*\*[ \t]*:", r"\1:", cleaned)
    cleaned = re.sub(rf"(?m)^[ \t]*\*\*({field_names})[ \t]*:\*\*", r"\1:", cleaned)
    cleaned = re.sub(rf"(?m)^[ \t]*`({field_names})`[ \t]*:", r"\1:", cleaned)
    cleaned = re.sub(rf"(?m)^[ \t]*#{{1,6}}[ \t]+({field_names})[ \t]*:", r"\1:", cleaned)
    return cleaned


def _字段匹配(text: str, field: str) -> list[re.Match]:
    return list(re.finditer(rf"(?m)^[ \t]*{re.escape(field)}[ \t]*:", text))


def _字段正文(text: str, field: str, fields: tuple[str, ...]) -> str:
    matches = _字段匹配(text, field)
    if len(matches) != 1:
        return ""
    start = matches[0].end()
    ends = []
    for other in fields:
        if other == field:
            continue
        for match in _字段匹配(text, other):
            if match.start() > start:
                ends.append(match.start())
    end = min(ends) if ends else len(text)
    return text[start:end].strip()


def _替换字段正文(text: str, field: str, fields: tuple[str, ...], body: str) -> str:
    matches = _字段匹配(text, field)
    if len(matches) != 1:
        return text
    start = matches[0].end()
    ends = []
    for other in fields:
        if other == field:
            continue
        for match in _字段匹配(text, other):
            if match.start() > start:
                ends.append(match.start())
    end = min(ends) if ends else len(text)
    prefix = text[:start].rstrip()
    suffix = text[end:].lstrip("\n")
    replacement = f"{prefix}\n{str(body).strip()}"
    if suffix:
        replacement += f"\n\n{suffix}"
    return replacement.strip()


def 规范化低价h3硬约束(text: str, mode: str, skill_id: str, task: str) -> str:
    """Apply mechanical low-tier delivery invariants without rewriting creative content."""
    cleaned = _清理最终文本(text)
    if skill_id != 低价直播礼物SKILL_ID:
        return cleaned
    normalized_mode = "Ref2VA" if str(mode).lower() == "ref2va" else str(mode).upper()
    if normalized_mode not in H3模式:
        return cleaned

    fields = H3全参考字段 if normalized_mode == "Ref2VA" else H3基础字段
    for field in ("overall_soundscape", "non_diegetic_music"):
        cleaned = _替换字段正文(cleaned, field, fields, "N/A")

    background_color = _解析礼物背景色(task)
    if not background_color:
        return cleaned
    description_field = "detailed_description" if normalized_mode == "Ref2VA" else "integrated_multimodal_description"
    description = _字段正文(cleaned, description_field, fields)
    if not description:
        return cleaned
    invariant = (
        f"The exact {background_color} background is a uniform solid-color, texture-free field that fills the entire frame. "
        "Its hue, luminance, texture, and coverage remain unchanged from the first frame through the final frame."
    )
    if invariant not in description:
        cleaned = _替换字段正文(cleaned, description_field, fields, f"{description.rstrip()}\n{invariant}")
    return cleaned


def _检查字段(text: str, fields: tuple[str, ...], errors: list[str]) -> None:
    positions = []
    for field in fields:
        matches = _字段匹配(text, field)
        if not matches:
            errors.append(f"缺少字段 {field}:")
            continue
        if len(matches) > 1:
            errors.append(f"字段 {field}: 重复出现 {len(matches)} 次")
            continue
        positions.append((field, matches[0].start()))
        if not _字段正文(text, field, fields):
            errors.append(f"字段 {field}: 内容为空")
    if len(positions) == len(fields) and [name for name, _ in sorted(positions, key=lambda item: item[1])] != list(fields):
        errors.append("字段顺序不符合 H3 规范")


def _检查镜头(description: str, duration: float, errors: list[str]) -> int:
    markers = list(re.finditer(r"\[Shot\s+(\d+)\]", description, re.IGNORECASE))
    if not markers:
        errors.append("描述中缺少 [Shot 1]")
        return 1
    if int(markers[0].group(1)) != 1:
        errors.append("描述中的第一个镜头标记必须是 [Shot 1]")

    first_shot = markers[0] if int(markers[0].group(1)) == 1 else None
    timed_entries = list(re.finditer(r"\[Shot\s+(\d+)\]\s+At\s+(\d{2}):(\d{2}(?:\.\d{3}))", description, re.IGNORECASE))
    entries = []
    captured_starts = {first_shot.start()} if first_shot is not None else set()
    for match in timed_entries:
        number = int(match.group(1))
        captured_starts.add(match.start())
        if number == 1:
            errors.append("[Shot 1] 不应带切点时间")
            continue
        entries.append(match)

    numbers = ([1] if first_shot is not None else []) + [int(match.group(1)) for match in entries]
    if not numbers:
        return 1
    expected = list(range(1, max(numbers) + 1))
    if numbers != expected:
        errors.append(f"镜头编号必须从 1 连续且各出现一次，当前为 {numbers}")

    actual_numbers = set(numbers)
    for marker in markers:
        number = int(marker.group(1))
        if marker.start() not in captured_starts and number not in actual_numbers:
            errors.append(f"[Shot {number}] 缺少 At MM:SS.mmm 切点时间")

    previous_time = 0.0
    for match in entries:
        number = int(match.group(1))
        minute_text, second_text = match.group(2), match.group(3)
        seconds = float(second_text)
        if seconds >= 60:
            errors.append(f"[Shot {number}] 的秒数必须小于 60，当前为 {second_text}")
        cut_time = int(minute_text) * 60 + seconds
        if cut_time <= previous_time:
            errors.append(f"[Shot {number}] 的切点时间没有严格递增")
        if duration > 0 and cut_time >= duration:
            errors.append(f"[Shot {number}] 的切点 {cut_time:.3f}s 必须小于视频时长 {duration:.2f}s")
        previous_time = cut_time
    return max(numbers)


def _检查关键帧首行(text: str, mode: str, duration: float, final_shot: int, fields: tuple[str, ...], errors: list[str]) -> None:
    first_field_positions = [matches[0].start() for field in fields if (matches := _字段匹配(text, field))]
    header = text[: min(first_field_positions)].strip() if first_field_positions else ""
    duration_text = f"{duration:.2f}"
    if mode == "T2VA":
        if header:
            errors.append("T2VA 必须直接从 integrated_multimodal_description 开始，不能添加图片对齐首行")
        return
    if duration <= 0:
        errors.append("无法校验关键帧端点：未提供有效视频时长")
        return
    if mode == "I2VA":
        expected = "For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced."
    elif mode == "FL2VA":
        expected = (
            "How the reference pictures align with the target video — "
            f"Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot {final_shot}) aligns with the {duration_text}-second mark of the target video."
        )
    else:
        expected = (
            "How the reference pictures align with the target video — "
            f"<Picture 1> (from [Shot {final_shot}]) aligns with the {duration_text}-second mark of the target video."
        )
    if header != expected:
        errors.append(f"{mode} 的图片对齐首行不符合固定格式；期望：{expected}")


def _检查ref标签(text: str, fields: tuple[str, ...], errors: list[str]) -> None:
    definitions = _字段正文(text, "subject_definitions", fields)
    retention = _字段正文(text, "retention_analysis", fields)
    definition_labels = [
        re.sub(r"\s+", " ", match.group(1))
        for match in re.finditer(
            r"(?im)^\s*(<(?:Subject|Picture|Video|Audio)\s+\d+>)(?=\s|[:：])",
            definitions,
        )
    ]
    defined = set(definition_labels)
    if not defined:
        errors.append("subject_definitions 中没有可识别的引用定义")
        return
    duplicate_definitions = sorted(label for label in defined if definition_labels.count(label) > 1)
    if duplicate_definitions:
        errors.append("subject_definitions 中存在重复定义：" + "、".join(duplicate_definitions))

    invalid_labels = sorted(
        {
            match.group(0)
            for match in re.finditer(r"<(?:Subject|Picture|Video|Audio)\s+(-?\d+)>", text)
            if int(match.group(1)) < 1
        }
    )
    if invalid_labels:
        errors.append("引用标签编号必须从 1 开始，不能使用：" + "、".join(invalid_labels))
    definition_subjects = set(re.findall(r"<Subject\s+\d+>", definitions))
    undefined_definition_subjects = sorted(definition_subjects - defined)
    if undefined_definition_subjects:
        errors.append("subject_definitions 内引用了未定义 Subject：" + "、".join(undefined_definition_subjects))

    text_without_definitions = text.replace(definitions, "", 1)
    used = set(re.findall(r"<(?:Subject|Picture|Video|Audio)\s+\d+>", text_without_definitions))
    unresolved = sorted(used - defined)
    if unresolved:
        errors.append("存在未定义的引用标签：" + "、".join(unresolved))

    visual_markers = ("fully_preserved", "partially_preserved", "attribute_transfer", "weak_reference")
    audio_markers = ("fully_copy", "partially_copy", "reference", "weak_reference")
    for label in sorted(defined):
        line_matches = re.findall(
            rf"(?im)^\s*{re.escape(label)}(?:\s*\([^\n]*\))?\s*[:：]\s*([a-z_]+)\b",
            retention,
        )
        if not line_matches:
            errors.append(f"retention_analysis 缺少 {label} 的关系行")
            continue
        if len(line_matches) > 1:
            errors.append(f"retention_analysis 中 {label} 重复出现 {len(line_matches)} 次")
            continue
        marker = line_matches[0]
        allowed = audio_markers if label.startswith("<Audio") else visual_markers
        if marker not in allowed:
            errors.append(f"{label} 使用了无效关系标记 {marker}")


def _检查礼物profile(
    text: str,
    mode: str,
    duration: float,
    skill_id: str,
    task: str,
    fields: tuple[str, ...],
    description: str,
    errors: list[str],
) -> None:
    if skill_id not in 直播礼物SKILL_IDS:
        return
    price = _解析礼物价格(task)
    if skill_id == 直播礼物SKILL_ID:
        if not 1000 <= price <= 3000:
            errors.append(f"高价直播礼物价格必须在 1000–3000，当前为 {price}")
        expected_shots = _解析礼物镜头数(task)
        actual_shots = [int(number) for number in re.findall(r"\[Shot\s+(\d+)\]", description, re.IGNORECASE)]
        if expected_shots and actual_shots != list(range(1, expected_shots + 1)):
            errors.append(f"任务要求 {expected_shots} 个镜头，当前镜头编号为 {actual_shots or '无'}")
        return

    if not 99 <= price <= 999:
        errors.append(f"低价直播礼物价格必须在 99–999，当前为 {price}")
        return
    expected_frames = 73 if price <= 299 else 90
    expected_duration = expected_frames / 24.0
    if abs(float(duration) - expected_duration) > 0.02:
        errors.append(
            f"低价礼物 {price} 抖币必须使用 {expected_frames} 帧/{expected_duration:.2f} 秒，当前任务时长为 {duration:.2f} 秒"
        )

    shot_numbers = [int(number) for number in re.findall(r"\[Shot\s+(\d+)\]", description, re.IGNORECASE)]
    if shot_numbers != [1]:
        errors.append(f"低价礼物必须且只能包含一个 [Shot 1]，当前为 {shot_numbers or '无'}")
    cut_terms = re.compile(
        r"\b(?:camera|shot)\s+(?:cuts|switches|changes|transitions)\s+to\b|"
        r"\bhard cut\b|\bcross[- ]dissolve\b|\bhidden cut\b|\bmatch cut\b",
        re.IGNORECASE,
    )
    if cut_terms.search(description):
        errors.append("低价礼物不得包含剪切或转场描述")

    for field in ("overall_soundscape", "non_diegetic_music"):
        if _字段正文(text, field, fields).strip() != "N/A":
            errors.append(f"低价礼物的 {field}: 必须严格为 N/A")
    if re.search(r"<Audio\s+\d+>|\(S\d+(?:,S\d+)*\)|<d>[\s\S]*?</d>", text, re.IGNORECASE):
        errors.append("低价礼物不得定义音频引用、说话人或对白")

    aspect = _解析礼物画幅(task)
    if aspect not in ("1:1", "4:3"):
        errors.append(f"低价礼物有效画幅只能是 1:1 或 4:3，当前为 {aspect or '未指定'}")
    elif not re.search(
        r"(?<!\d)" + re.escape(aspect).replace(":", r"\s*:\s*") + r"(?!\d)",
        description,
    ):
        errors.append(f"低价礼物提示词必须明确写出 {aspect} 画幅")

    background_color = _解析礼物背景色(task)
    if price < 500 and not background_color:
        errors.append("99–499 低价礼物任务缺少固定背景色标记")

    if background_color:
        required_color_fields = (
            ("subject_definitions", "summary", "retention_analysis", "detailed_description")
            if mode == "Ref2VA"
            else ("integrated_multimodal_description",)
        )
        for field in required_color_fields:
            body = _字段正文(text, field, fields)
            if background_color not in body:
                errors.append(f"固定背景色 {background_color} 必须出现在 {field} 中")

        solid = re.search(
            r"\b(?:solid(?:-| )color(?:ed)?|solid background|solid field|single-color|uniform color field|uniform solid)\b",
            description,
            re.IGNORECASE,
        )
        full_frame = re.search(
            r"\b(?:full[- ]frame|entire frame|every pixel|full coverage|fills? the frame)\b",
            description,
            re.IGNORECASE,
        )
        stable = re.search(
            r"(?:background|field).{0,180}(?:remains?|stays?|keeps?|constant|unchanged|identical).{0,180}"
            r"(?:throughout|entire|every frame|all frames|first frame|last frame|full video)|"
            r"(?:hue|luminance).{0,120}(?:constant|unchanged)",
            description,
            re.IGNORECASE | re.DOTALL,
        )
        texture_stable = re.search(
            r"\btexture[- ]free\b|\btexture.{0,80}(?:constant|unchanged|uniform)\b",
            description,
            re.IGNORECASE | re.DOTALL,
        )
        if not solid:
            errors.append(f"启用固定背景色 {background_color} 时必须明确使用均匀纯色背景")
        if not full_frame:
            errors.append(f"启用固定背景色 {background_color} 时必须明确背景覆盖全画面")
        if not stable:
            errors.append(f"启用固定背景色 {background_color} 时必须明确背景从首帧到末帧保持不变")
        if not texture_stable:
            errors.append(f"启用固定背景色 {background_color} 时必须明确背景无纹理或纹理保持不变")

        background_segments = [
            segment
            for segment in re.split(r"[\n.;]", text)
            if re.search(r"\b(?:background|field)\b", segment, re.IGNORECASE)
        ]
        conflicting_hex = sorted(
            {
                value.upper()
                for segment in background_segments
                for value in re.findall(r"#[0-9A-Fa-f]{6}\b", segment)
                if value.upper() != background_color
            }
        )
        if conflicting_hex:
            errors.append("背景描述包含与固定色冲突的色值：" + "、".join(conflicting_hex))
        if re.search(
            r"(?:gradient|textured|patterned)\s+(?:background|field)|"
            r"(?:background|field).{0,100}(?:gradient|recolor|changes? color|color shift|lighting change|luminance change)",
            description,
            re.IGNORECASE | re.DOTALL,
        ):
            errors.append("固定纯色背景不得包含渐变、纹理、重染或亮度变化")


def 校验h3提示词(
    text: str,
    mode: str,
    duration: float,
    image_count: int = 0,
    image_only: bool = False,
    skill_id: str = "",
    task: str = "",
) -> tuple[str, list[str], list[str]]:
    cleaned = _清理最终文本(text)
    normalized_mode = "Ref2VA" if str(mode).lower() == "ref2va" else str(mode).upper()
    errors = []
    warnings = []
    if normalized_mode not in H3模式:
        return cleaned, [f"未知 H3 模式：{mode}"], warnings

    fields = H3全参考字段 if normalized_mode == "Ref2VA" else H3基础字段
    _检查字段(cleaned, fields, errors)
    unexpected_fields = ("integrated_multimodal_description",) if normalized_mode == "Ref2VA" else H3全参考字段[:4]
    for field in unexpected_fields:
        if _字段匹配(cleaned, field):
            errors.append(f"{normalized_mode} 不应包含其他 H3 模式字段 {field}:")
    if re.search(r"(?im)(?:^|\s)--wm\s+false(?:\s|$)", cleaned):
        errors.append("H3 提示词不得包含 --wm false")
    description_field = "detailed_description" if normalized_mode == "Ref2VA" else "integrated_multimodal_description"
    description = _字段正文(cleaned, description_field, fields)
    final_shot = _检查镜头(description, float(duration), errors) if description else 1

    if normalized_mode == "Ref2VA":
        _检查ref标签(cleaned, fields, errors)
        summary = _字段正文(cleaned, "summary", fields)
        summary_prefix = re.match(r"^\[([^\]]+)\]", summary)
        allowed_task_types = {
            "keyframe completion",
            "reference generation",
            "video editing",
            "video continuation",
            "audio reuse",
            "audio reference",
        }
        if not summary_prefix:
            errors.append("summary 缺少方括号任务类型前缀")
        else:
            task_types = {part.strip() for part in summary_prefix.group(1).split("+")}
            invalid_types = sorted(task_types - allowed_task_types)
            if invalid_types:
                errors.append("summary 包含无效任务类型：" + "、".join(invalid_types))
        definitions = _字段正文(cleaned, "subject_definitions", fields)
        if image_only:
            unsupported_assets = sorted(
                set(re.findall(r"(?im)^\s*(<(?:Video|Audio)\s+\d+>)(?=\s|[:：])", definitions))
            )
            if unsupported_assets:
                errors.append("当前 Skill 执行器只接收图片，不能定义未输入的资产：" + "、".join(unsupported_assets))
        if image_count > 0:
            missing_pictures = [f"<Picture {index}>" for index in range(1, image_count + 1) if f"<Picture {index}>" not in definitions]
            if missing_pictures:
                errors.append("以下输入图片未在 subject_definitions 中引用：" + "、".join(missing_pictures))
            picture_numbers = [int(value) for value in re.findall(r"<Picture\s+(\d+)>", cleaned)]
            overflow = sorted({value for value in picture_numbers if value > image_count})
            if overflow:
                errors.append("提示词引用了不存在的输入图片：" + "、".join(f"<Picture {value}>" for value in overflow))
        first_field_positions = [matches[0].start() for field in fields if (matches := _字段匹配(cleaned, field))]
        if first_field_positions:
            prefix = cleaned[: min(first_field_positions)].strip()
            if prefix.startswith(("For the target video,", "How the reference pictures align")):
                errors.append("Ref2VA 不得包含基础模式的图片对齐首行")
            elif prefix:
                warnings.append("Ref2VA 在 subject_definitions 前包含额外前言")
        word_count = len(re.findall(r"\b[A-Za-z]+(?:[-'][A-Za-z]+)*\b", description))
        if description and not 250 <= word_count <= 700:
            warnings.append(f"detailed_description 当前约 {word_count} 个英文词，建议生成任务保持充分细节")
    else:
        _检查关键帧首行(cleaned, normalized_mode, float(duration), final_shot, fields, errors)

    dialogue_open_count = cleaned.count("<d>")
    dialogue_close_count = cleaned.count("</d>")
    if dialogue_open_count != dialogue_close_count:
        errors.append("<d> 对话标签未成对闭合")
    elif dialogue_open_count:
        dialogue_blocks = re.findall(r"<d>(.*?)</d>", cleaned, re.DOTALL)
        if len(dialogue_blocks) != dialogue_open_count:
            errors.append("<d> 对话标签存在嵌套或结构错误")
        for block in dialogue_blocks:
            if not re.match(r"^\[[A-Za-z][A-Za-z -]{1,30}\]\s*\S", block.strip()):
                errors.append("每个 <d> 对话块必须以 [Language] 标签开头并包含原文")
                break
    _检查礼物profile(cleaned, normalized_mode, duration, skill_id, task, fields, description, errors)
    return cleaned, errors, warnings


def _h3_reference(skill: dict, task: str) -> list[str]:
    mode = _解析h3模式(task)
    if not mode:
        raise ValueError("H3 Skill 单次执行需要明确 T2VA、I2VA、FL2VA、L2VA 或 Ref2VA 模式；建议连接 H3任务构建器。")
    relative_path = "references/ref-en.txt" if mode == "Ref2VA" else "references/base-en.txt"
    if relative_path not in skill["references"]:
        raise ValueError(f"H3 Skill 包不完整，缺少 {relative_path}。")
    return [relative_path]


def _提取markdown章节(text: str, title: str) -> str:
    lines = str(text or "").splitlines()
    start = -1
    level = 0
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match and match.group(2).strip() == str(title).strip():
            start = index
            level = len(match.group(1))
            break
    if start < 0:
        raise ValueError(f"Registry 声明的 Markdown 章节不存在：{title}")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        match = re.match(r"^(#{1,6})\s+", lines[index])
        if match and len(match.group(1)) <= level:
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def _提取情感规则(text: str, emotion: str) -> str:
    section = _提取markdown章节(text, emotion)
    match = re.search(r"(?m)^##\s+", text)
    preamble = text[: match.start()].rstrip() if match else text.rstrip()
    return f"{preamble}\n\n{section}".strip()


def _礼物registry条目(skill: dict) -> list[dict]:
    registry = skill.get("registry") or {}
    entries = registry.get("entries") or []
    if not isinstance(entries, list):
        raise ValueError(f"{skill['id']}/registry.json 的 entries 必须是数组。")
    normalized = []
    seen = set()
    evaluation_only = set(skill.get("evaluation_only_references") or [])
    for raw in entries:
        if not isinstance(raw, dict):
            raise ValueError(f"{skill['id']}/registry.json 包含非对象条目。")
        entry_id = str(raw.get("id") or "").strip()
        path = str(raw.get("path") or "").replace("\\", "/").strip("/")
        sections = raw.get("sections") or []
        requires = raw.get("requires") or []
        if not entry_id or entry_id in seen:
            raise ValueError(f"{skill['id']}/registry.json 包含空 ID 或重复 ID：{entry_id or '<空>'}")
        if path not in skill.get("references", []) or path in evaluation_only:
            raise ValueError(f"Registry 条目 {entry_id} 指向不可运行的 reference：{path}")
        if not isinstance(sections, list) or not all(isinstance(item, str) and item.strip() for item in sections):
            raise ValueError(f"Registry 条目 {entry_id} 的 sections 必须是非空字符串数组。")
        if not isinstance(requires, list) or not all(isinstance(item, str) for item in requires):
            raise ValueError(f"Registry 条目 {entry_id} 的 requires 必须是字符串数组。")
        item = dict(raw)
        item.update(
            {
                "id": entry_id,
                "path": path,
                "sections": [section.strip() for section in sections],
                "requires": [required.strip() for required in requires if required.strip()],
                "priority": int(raw.get("priority") or 100),
            }
        )
        normalized.append(item)
        seen.add(entry_id)
    valid_ids = {entry["id"] for entry in normalized}
    for entry in normalized:
        missing = [item for item in entry["requires"] if item not in valid_ids]
        if missing:
            raise ValueError(f"Registry 条目 {entry['id']} 依赖不存在的 ID：{'、'.join(missing)}")
    return sorted(normalized, key=lambda item: (item["priority"], item["id"]))


def _礼物registry摘要(skill: dict) -> str:
    lines = []
    for entry in _礼物registry条目(skill):
        lines.extend(
            (
                f"- id: {entry['id']}",
                f"  summary: {entry.get('summary') or ''}",
                f"  use_when: {entry.get('use_when') or ''}",
                f"  avoid_when: {entry.get('avoid_when') or ''}",
                f"  requires: {json.dumps(entry['requires'], ensure_ascii=False)}",
            )
        )
    return "\n".join(lines)


def _解析礼物registry选择(text: str, skill: dict) -> list[str]:
    cleaned = _清洗think块文本(text).strip()
    lines = cleaned.splitlines()
    if len(lines) >= 2 and re.fullmatch(r"```(?:json|text)?", lines[0].strip(), re.IGNORECASE) and lines[-1].strip() == "```":
        cleaned = "\n".join(lines[1:-1]).strip()
    value = None
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*?\]", cleaned)
        if match:
            try:
                value = json.loads(match.group(0))
            except json.JSONDecodeError:
                value = None
    if isinstance(value, dict):
        for key in ("selected", "references", "selected_references", "ids"):
            if key in value:
                value = value[key]
                break
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("Reference 路由结果必须包含一个字符串数组。")
    allowed = {entry["id"] for entry in _礼物registry条目(skill)}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError("Reference 路由返回了未知 ID：" + "、".join(unknown))
    return list(dict.fromkeys(value))


def _礼物全部reference_ids(skill: dict) -> list[str]:
    return [entry["id"] for entry in _礼物registry条目(skill)]


def _展开礼物registry依赖(skill: dict, selected_ids: list[str]) -> list[dict]:
    entries = _礼物registry条目(skill)
    by_id = {entry["id"]: entry for entry in entries}
    selected = set(selected_ids)
    pending = list(selected_ids)
    while pending:
        current = pending.pop()
        if current not in by_id:
            raise ValueError(f"未知 Reference registry ID：{current}")
        for required in by_id[current]["requires"]:
            if required not in selected:
                selected.add(required)
                pending.append(required)
    return [entry for entry in entries if entry["id"] in selected]


def _构建礼物资源(skill: dict, task: str, selected_ids: list[str] | None = None) -> tuple[list[dict], dict]:
    mode = _解析h3模式(task)
    if not mode:
        raise ValueError("直播礼物 Skill 需要明确 H3 模式；请连接直播礼物任务构建器。")
    price = _解析礼物价格(task)
    if skill["id"] == 低价直播礼物SKILL_ID and not 99 <= price <= 999:
        raise ValueError(f"低价直播礼物 Skill 只接受 99–999 抖币，当前为 {price}。")
    if skill["id"] == 直播礼物SKILL_ID and not 1000 <= price <= 3000:
        raise ValueError(f"高价直播礼物 Skill 只接受 1000–3000 抖币，当前为 {price}。")
    emotion = _解析礼物情感(task) or "趣味"
    format_paths = [直播礼物基础规范]
    if mode == "Ref2VA":
        format_paths.append(直播礼物全参考规范)
    format_paths.append(直播礼物情感规则)
    hard_rule_paths = [直播礼物价效规则]
    if skill["id"] == 低价直播礼物SKILL_ID:
        hard_rule_paths.append(低价直播礼物价效配置)
        if _解析礼物背景色(task):
            hard_rule_paths.append(低价直播礼物背景规则)
    mandatory_paths = format_paths + hard_rule_paths
    missing = [path for path in mandatory_paths if path not in skill.get("rules", [])]
    if missing:
        raise ValueError("直播礼物 Skill 包缺少必读规则：" + "、".join(missing))

    resources = []
    for path in format_paths:
        content = 读取reference(skill, path)
        label = path
        if path == 直播礼物情感规则:
            content = _提取情感规则(content, emotion)
            label = f"{path}#{emotion}"
        resources.append({"kind": "rule", "label": label, "path": path, "content": content})

    expanded_entries = _展开礼物registry依赖(skill, list(selected_ids or []))
    for entry in expanded_entries:
        source = 读取reference(skill, entry["path"])
        sections = [_提取markdown章节(source, title) for title in entry["sections"]]
        resources.append(
            {
                "kind": "reference",
                "id": entry["id"],
                "label": f"{entry['path']}#{entry['id']}",
                "path": entry["path"],
                "sections": list(entry["sections"]),
                "content": "\n\n".join(sections),
            }
        )
    # Put deterministic price/background contracts after optional references so they have final precedence.
    for path in hard_rule_paths:
        resources.append(
            {
                "kind": "rule",
                "label": path,
                "path": path,
                "content": 读取reference(skill, path),
            }
        )
    report = {
        "price": price,
        "mode": mode,
        "emotion": emotion,
        "background_color": _解析礼物背景色(task) or None,
        "mandatory_rules": [item["label"] for item in resources if item["kind"] == "rule"],
        "selected_references": [entry["id"] for entry in expanded_entries],
        "injected_characters": sum(len(item["content"]) for item in resources),
    }
    return resources, report


def _构建图像礼物资源(skill: dict, task: str, selected_ids: list[str] | None = None) -> tuple[list[dict], dict]:
    price = _解析礼物价格(task)
    if skill["id"] == 低价直播礼物图像SKILL_ID and not 99 <= price <= 999:
        raise ValueError(f"低价直播礼物图像 Skill 只接受 99–999 抖币，当前为 {price}。")
    if skill["id"] == 直播礼物图像SKILL_ID and not 1000 <= price <= 3000:
        raise ValueError(f"直播礼物图像 Skill 只接受 1000–3000 抖币，当前为 {price}。")
    if skill["id"] not in 直播礼物图像SKILL_IDS:
        raise ValueError(f"当前 Skill 不是直播礼物图像提示词 Skill：{skill['id']}。")

    emotion = _解析礼物情感(task) or "趣味"
    missing = [path for path in 直播礼物图像必读规则 if path not in skill.get("rules", [])]
    if missing:
        raise ValueError("直播礼物图像 Skill 包缺少必读规则：" + "、".join(missing))

    resources = []
    for path in 直播礼物图像必读规则:
        content = 读取reference(skill, path)
        label = path
        if path == 直播礼物情感规则:
            content = _提取情感规则(content, emotion)
            label = f"{path}#{emotion}"
        resources.append({"kind": "rule", "label": label, "path": path, "content": content})

    expanded_entries = _展开礼物registry依赖(skill, list(selected_ids or []))
    for entry in expanded_entries:
        source = 读取reference(skill, entry["path"])
        sections = [_提取markdown章节(source, title) for title in entry["sections"]]
        resources.append(
            {
                "kind": "reference",
                "id": entry["id"],
                "label": f"{entry['path']}#{entry['id']}",
                "path": entry["path"],
                "sections": list(entry["sections"]),
                "content": "\n\n".join(sections),
            }
        )
    report = {
        "price": price,
        "emotion": emotion,
        "mandatory_rules": [item["label"] for item in resources if item["kind"] == "rule"],
        "selected_references": [entry["id"] for entry in expanded_entries],
        "injected_characters": sum(len(item["content"]) for item in resources),
    }
    return resources, report


def _拆分礼物外部提示(text: str, mode: str) -> tuple[str, str]:
    cleaned = _清理最终文本(text)
    if mode == "Ref2VA":
        marker = _字段匹配(cleaned, "subject_definitions")
        start = marker[0].start() if marker else -1
    elif mode == "T2VA":
        marker = _字段匹配(cleaned, "integrated_multimodal_description")
        start = marker[0].start() if marker else -1
    elif mode == "I2VA":
        start = cleaned.find("For the target video,")
    else:
        start = cleaned.find("How the reference pictures align")
    if start <= 0:
        return cleaned, ""
    return cleaned[start:].strip(), cleaned[:start].strip()


def _解析reference选择(text: str, allowed: list[str]) -> list[str]:
    cleaned = _清洗think块文本(text).strip()
    match = re.search(r"\[[\s\S]*?\]", cleaned)
    if match:
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError:
            value = None
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str) and item in allowed]
    selected = [path for path in allowed if path in cleaned]
    if selected:
        return selected
    raise ValueError("自动选择 Skill reference 失败；API 未返回有效的 reference 路径数组。")


def _构建系统提示词(skill: dict, reference_paths: list, extra_system: str) -> str:
    parts = [str(extra_system or "").strip(), f"当前 Skill：{skill['name']} ({skill['id']})", f"===== {skill['skill_file']} =====\n{读取skill正文(skill)}"]
    for resource in reference_paths:
        if isinstance(resource, dict):
            kind = str(resource.get("kind") or "reference")
            label = str(resource.get("label") or resource.get("path") or "resource")
            content = str(resource.get("content") or "")
            parts.append(f"===== {kind}: {label} =====\n{content}")
        else:
            path = str(resource)
            parts.append(f"===== reference: {path} =====\n{读取reference(skill, path)}")
    parts.append(无状态SKILL执行协议)
    return "\n\n".join(part for part in parts if part)


def _收集图片(*image_sources) -> list[tuple[object, int]]:
    images = []
    for source in image_sources:
        if source is None:
            continue
        images.extend((source, index) for index in range(int(source.shape[0])))
    if len(images) > 9:
        raise ValueError(f"Skill 单次执行最多支持 9 张图片，当前共 {len(images)} 张。")
    return images


def _构建用户内容(task: str, images: list[tuple[object, int]], max_edge: int):
    if not images:
        return task
    content = [{"type": "text", "text": task}]
    for image_source, index in images:
        image_base64 = _批量图片索引转base64(image_source, index, max_edge)
        if image_base64:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}})
    return content


def _检查h3图片数量(mode: str, count: int) -> None:
    expected = {
        "T2VA": (0, 0, "T2VA 不使用参考图片"),
        "I2VA": (1, 1, "I2VA 需要恰好 1 张首帧图片"),
        "FL2VA": (2, 2, "FL2VA 需要恰好 2 张首尾帧图片"),
        "L2VA": (1, 1, "L2VA 需要恰好 1 张尾帧图片"),
        "Ref2VA": (1, 9, "Ref2VA 需要 1 到 9 张参考图片"),
    }
    minimum, maximum, message = expected[mode]
    if count < minimum or (maximum is not None and count > maximum):
        raise ValueError(f"{message}，当前共连接 {count} 张。请按引用顺序连接独立图片口，或把批次接入第一个图片口。")


class APIAgent直播礼物任务构建器:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "礼物名称": ("STRING", {"default": ""}),
                "礼物价格": (
                    "INT",
                    {
                        "default": 2000,
                        "min": 99,
                        "max": 3000,
                        "step": 1,
                        "tooltip": "99–999 自动路由到低价礼物 Skill；1000–3000 自动路由到高价礼物 Skill。",
                    },
                ),
                "创作需求": ("STRING", {"default": "", "multiline": True}),
                "参考图用途": (
                    ["普通参考素材（Ref2VA）", "无参考图（T2VA）", "精确首帧（I2VA）", "精确首尾帧（FL2VA）", "精确尾帧（L2VA）"],
                    {"default": "普通参考素材（Ref2VA）"},
                ),
                "情感表达": (list(直播礼物情感), {"default": "趣味"}),
                "视频时长": ("FLOAT", {"default": 5.0, "min": 0.1, "max": 149.0, "step": 0.1}),
                "画幅比例": (["1:1", "9:16", "16:9", "4:3", "3:4"], {"default": "1:1"}),
                "镜头结构": (["自动决定", "单镜头", "双镜头", "三镜头"], {"default": "自动决定"}),
                "声音与音乐": (
                    "STRING",
                    {"default": "", "multiline": True, "tooltip": "留空时按礼物 Skill 默认输出两个 N/A 音频字段。"},
                ),
                "额外约束": ("STRING", {"default": "", "multiline": True}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "FLOAT", "APIAGENT_SKILL", "APIAGENT_SKILL", "INT")
    RETURN_NAMES = ("直播礼物H3任务", "H3帧数", "实际时长", "图像Skill路由", "视频Skill路由", "礼物价格")
    FUNCTION = "run"
    CATEGORY = "APIAgent/直播礼物"

    def run(self, 礼物名称, 礼物价格, 创作需求, 参考图用途, 情感表达, 视频时长, 画幅比例, 镜头结构, 声音与音乐, 额外约束):
        gift_name = str(礼物名称 or "").strip()
        if not gift_name:
            raise ValueError("礼物名称不能为空。")
        price = int(礼物价格)
        if not 99 <= price <= 3000:
            raise ValueError("直播礼物价格必须在 99–3000 抖币之间。")
        emotion = str(情感表达 or "").strip()
        if emotion not in 直播礼物情感:
            raise ValueError("情感表达必须是：" + "、".join(直播礼物情感))
        if price < 1000:
            skill_id = 低价直播礼物SKILL_ID
            image_skill_id = 低价直播礼物图像SKILL_ID
            profile = "LOW_COIN_GIFT"
        else:
            skill_id = 直播礼物SKILL_ID
            image_skill_id = 直播礼物图像SKILL_ID
            profile = "LIVE_GIFT"
        mode = {
            "普通参考素材（Ref2VA）": "Ref2VA",
            "无参考图（T2VA）": "T2VA",
            "精确首帧（I2VA）": "I2VA",
            "精确首尾帧（FL2VA）": "FL2VA",
            "精确尾帧（L2VA）": "L2VA",
        }[参考图用途]
        image_rule = {
            "T2VA": "不连接参考图片。",
            "I2VA": "连接恰好 1 张图片，并把它作为 0.00 秒精确首帧。",
            "FL2VA": "按顺序连接恰好 2 张图片，分别作为精确首帧和精确尾帧。",
            "L2VA": "连接恰好 1 张图片，并把它作为视频结束时的精确尾帧。",
            "Ref2VA": "连接 1–9 张普通参考图片；图片提供主体、环境、材质、风格或构图语言，不把它们自动解释为精确首尾帧。",
        }[mode]
        requested_duration = float(视频时长)
        aligned_frames, actual_duration = _礼物有效规格(price, requested_duration)
        requested_aspect = str(画幅比例)
        requested_shots = str(镜头结构)
        requested_audio = str(声音与音乐 or "").strip()
        if price < 1000:
            effective_aspect = requested_aspect if requested_aspect in ("1:1", "4:3") else "1:1"
            effective_shots = 1
            effective_audio = "N/A"
        else:
            effective_aspect = requested_aspect
            effective_shots = {"单镜头": 1, "双镜头": 2, "三镜头": 3}.get(requested_shots, 0)
            effective_audio = requested_audio or "N/A"
        parts = [
            f"[APIAGENT_H3_PROFILE={profile}]",
            f"[APIAGENT_SKILL_ID={skill_id}]",
            f"[APIAGENT_VIDEO_SKILL_ID={skill_id}]",
            f"[APIAGENT_IMAGE_SKILL_ID={image_skill_id}]",
            f"[APIAGENT_H3_MODE={mode}]",
            f"[APIAGENT_H3_DURATION={actual_duration:.2f}]",
            f"[APIAGENT_GIFT_PRICE={price}]",
            f"[APIAGENT_GIFT_EMOTION={emotion}]",
            f"[APIAGENT_GIFT_ASPECT={effective_aspect}]",
            f"[APIAGENT_GIFT_SHOTS={effective_shots}]",
            "请执行当前节点实际连接的 Skill；视频 Skill 输出 MiniMax H3 英文提示词，图像 Skill 输出同一礼物设计的中英文图像提示词。",
            f"礼物名称：{gift_name}",
            f"礼物价格：{price} 抖币",
            f"参考用途（H3 模式）：{mode}",
            f"情感表达：{emotion}",
            f"用户目标时长：{requested_duration:.2f} 秒",
            f"H3 对齐帧数：{aligned_frames} 帧（24 fps）",
            f"目标视频有效时长：{actual_duration:.2f} 秒",
            f"用户画幅比例：{requested_aspect}",
            f"有效画幅比例：{effective_aspect}",
            f"用户镜头结构：{requested_shots}",
            f"有效镜头结构：{'单镜头' if effective_shots == 1 else requested_shots}",
            f"参考图片规则：{image_rule}",
        ]
        if price < 1000:
            parts.append(
                "低价硬性规格：价效规范优先于冲突的用户时长、镜头、声音和画幅要求；"
                f"最终使用 {aligned_frames} 帧/{actual_duration:.2f} 秒、单镜头、{effective_aspect}、静音。"
            )
            conflicts = []
            if abs(requested_duration - actual_duration) > 0.02:
                conflicts.append(f"用户时长 {requested_duration:.2f} 秒")
            if requested_shots not in ("自动决定", "单镜头"):
                conflicts.append(f"用户镜头结构 {requested_shots}")
            if requested_aspect != effective_aspect:
                conflicts.append(f"用户画幅 {requested_aspect}")
            if requested_audio:
                conflicts.append("用户声音与音乐要求")
            if conflicts:
                parts.append("需要按低价硬性规格覆盖的原始要求：" + "、".join(conflicts) + "。")
        request = str(创作需求 or "").strip()
        if request:
            parts.append(f"创作需求：\n{request}")
        if price < 1000:
            parts.append("有效声音与音乐要求：无音频；overall_soundscape 和 non_diegetic_music 均严格为 N/A。")
            if requested_audio:
                parts.append(f"用户原始声音与音乐要求（因低价硬性规格不执行）：\n{requested_audio}")
        else:
            parts.append(
                f"声音与音乐要求：\n{effective_audio}"
                if effective_audio != "N/A"
                else "声音与音乐要求：无音频；overall_soundscape 和 non_diegetic_music 均为 N/A。"
            )
        constraints = str(额外约束 or "").strip()
        if constraints:
            parts.append(f"额外约束：\n{constraints}")
        return (
            "\n\n".join(parts),
            aligned_frames,
            actual_duration,
            构建skill选择(image_skill_id),
            构建skill选择(skill_id),
            price,
        )
