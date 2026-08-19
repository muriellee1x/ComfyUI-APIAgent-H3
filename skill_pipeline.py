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
直播礼物业务资料 = (
    "references/price-effect-system.md",
    "references/gift-story-reasoning.md",
    "references/effect-and-causality.md",
    "references/camera-transition-continuity.md",
    "references/subject-risk-modules.md",
)
直播礼物基础规范 = "references/h3-prompt-writing-base-en.txt"
直播礼物全参考规范 = "references/h3-prompt-writing-ref-en.txt"

无状态SKILL执行协议 = """
你正在通过 ComfyUI 的无状态 Skill 执行器工作。严格遵循当前 Skill 和已加载 reference，并遵守以下规则：
1. 本次调用必须在一轮内交付可直接传给下游节点的最终文本产物。不要提问，不要等待确认，不要输出选项或流程状态标记。
2. 如果 Skill 包含确认门或分阶段流程，把任务中已经提供的参数视为已确认。信息不足时按照下方“缺失信息策略”处理。
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
    marker = re.search(r"\[QWEN_TE_H3_MODE=(T2VA|I2VA|FL2VA|L2VA|Ref2VA)\]", text or "", re.IGNORECASE)
    if marker:
        value = marker.group(1)
        return "Ref2VA" if value.lower() == "ref2va" else value.upper()
    match = re.search(r"(?<![A-Za-z0-9])(Ref2VA|FL2VA|I2VA|L2VA|T2VA)(?![A-Za-z0-9])", text or "", re.IGNORECASE)
    if not match:
        return ""
    value = match.group(1)
    return "Ref2VA" if value.lower() == "ref2va" else value.upper()


def _解析h3时长(text: str) -> float:
    marker = re.search(r"\[QWEN_TE_H3_DURATION=([0-9]+(?:\.[0-9]+)?)\]", text or "", re.IGNORECASE)
    if marker:
        return float(marker.group(1))
    match = re.search(r"(?:有效时长|视频时长|duration)\s*[：:=]\s*([0-9]+(?:\.[0-9]+)?)", text or "", re.IGNORECASE)
    return float(match.group(1)) if match else 0.0


def _对齐h3时长(duration: float) -> tuple[int, float]:
    requested_frames = max(5, round(float(duration) * 24.0))
    aligned_frames = requested_frames + (5 - requested_frames % 17) % 17
    aligned_frames = min(aligned_frames, 3592)
    return aligned_frames, aligned_frames / 24.0


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
    definition_labels = re.findall(r"(?m)^[ \t]*(<(?:Subject|Picture|Video|Audio)\s+\d+>)[ \t]+", definitions)
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
        line_matches = re.findall(rf"(?m)^[ \t]*{re.escape(label)}(?:[ \t]*\([^\n]*\))?[ \t]*:[ \t]*([a-z_]+)[ \t]+-", retention)
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


def 校验h3提示词(text: str, mode: str, duration: float, image_count: int = 0, image_only: bool = False) -> tuple[str, list[str], list[str]]:
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
            unsupported_assets = sorted(set(re.findall(r"(?m)^[ \t]*(<(?:Video|Audio)\s+\d+>)[ \t]+", definitions)))
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
    return cleaned, errors, warnings


def _h3_reference(skill: dict, task: str) -> list[str]:
    mode = _解析h3模式(task)
    if not mode:
        raise ValueError("H3 Skill 单次执行需要明确 T2VA、I2VA、FL2VA、L2VA 或 Ref2VA 模式；建议连接 H3任务构建器。")
    relative_path = "references/ref-en.txt" if mode == "Ref2VA" else "references/base-en.txt"
    if relative_path not in skill["references"]:
        raise ValueError(f"H3 Skill 包不完整，缺少 {relative_path}。")
    return [relative_path]


def _礼物h3_references(skill: dict, task: str) -> list[str]:
    mode = _解析h3模式(task)
    if not mode:
        raise ValueError("直播礼物 Skill 需要明确 H3 模式；请连接“直播礼物任务构建器”或通用 H3任务构建器。")
    runtime_references = list(skill.get("runtime_references") or [])
    if runtime_references:
        missing = [path for path in runtime_references if path not in skill.get("references", [])]
        if missing:
            raise ValueError("直播礼物 Skill manifest 声明了不存在的 reference：" + "、".join(missing))
        return runtime_references
    paths = list(直播礼物业务资料) + [直播礼物基础规范]
    if mode == "Ref2VA":
        paths.append(直播礼物全参考规范)
    missing = [path for path in paths if path not in skill.get("references", [])]
    if missing:
        raise ValueError("直播礼物 Skill 包不完整，缺少：" + "、".join(missing))
    return paths


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
    raise ValueError("自动选择 Skill reference 失败；请把参考资料策略改为“加载全部”后重试。")


def _构建系统提示词(skill: dict, reference_paths: list[str], missing_policy: str, extra_system: str) -> str:
    if missing_policy == "信息不足时报错":
        missing_rule = "缺失信息策略：如果缺少完成最终产物不可替代的必要信息，只输出 QWEN_TE_INPUT_ERROR: 后接缺失项，不得继续生成。"
    else:
        missing_rule = "缺失信息策略：对未提供但可合理推断的参数采用保守默认值，直接完成最终产物，不要向用户确认。"
    parts = [str(extra_system or "").strip(), f"当前 Skill：{skill['name']} ({skill['id']})", f"===== {skill['skill_file']} =====\n{读取skill正文(skill)}"]
    for path in reference_paths:
        parts.append(f"===== reference: {path} =====\n{读取reference(skill, path)}")
    parts.extend((无状态SKILL执行协议, missing_rule))
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


def _识别h3输出模式(text: str) -> str:
    cleaned = _清理最终文本(text)
    if _字段匹配(cleaned, "subject_definitions"):
        return "Ref2VA"
    first_field_positions = [matches[0].start() for field in H3基础字段 if (matches := _字段匹配(cleaned, field))]
    header = cleaned[: min(first_field_positions)].strip() if first_field_positions else ""
    if header.startswith("For the target video, at 0.00 seconds"):
        return "I2VA"
    if header.startswith("How the reference pictures align") and "Picture 2" in header:
        return "FL2VA"
    if header.startswith("How the reference pictures align") and "Picture 1" in header:
        return "L2VA"
    if _字段匹配(cleaned, "integrated_multimodal_description"):
        return "T2VA"
    return ""


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
                        "min": 0,
                        "max": 3000,
                        "step": 1,
                        "tooltip": "0–999 自动路由到低价礼物 Skill；1000–3000 自动路由到高价礼物 Skill。",
                    },
                ),
                "创作需求": ("STRING", {"default": "", "multiline": True}),
                "参考图用途": (
                    ["普通参考素材（Ref2VA）", "无参考图（T2VA）", "精确首帧（I2VA）", "精确首尾帧（FL2VA）", "精确尾帧（L2VA）"],
                    {"default": "普通参考素材（Ref2VA）"},
                ),
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

    RETURN_TYPES = ("STRING", "INT", "FLOAT", "APIAGENT_SKILL")
    RETURN_NAMES = ("直播礼物H3任务", "H3帧数", "实际时长", "Skill路由")
    FUNCTION = "run"
    CATEGORY = "APIAgent/直播礼物"

    def run(self, 礼物名称, 礼物价格, 创作需求, 参考图用途, 视频时长, 画幅比例, 镜头结构, 声音与音乐, 额外约束):
        gift_name = str(礼物名称 or "").strip()
        if not gift_name:
            raise ValueError("礼物名称不能为空。")
        price = int(礼物价格)
        if not 0 <= price <= 3000:
            raise ValueError("直播礼物价格必须在 0–3000 抖币之间。")
        if price < 1000:
            skill_id = 低价直播礼物SKILL_ID
            profile = "LOW_COIN_GIFT"
        else:
            skill_id = 直播礼物SKILL_ID
            profile = "LIVE_GIFT"
        mode = {
            "普通参考素材（Ref2VA）": "Ref2VA",
            "无参考图（T2VA）": "T2VA",
            "精确首帧（I2VA）": "I2VA",
            "精确首尾帧（FL2VA）": "FL2VA",
            "精确尾帧（L2VA）": "L2VA",
        }[参考图用途]
        aligned_frames, actual_duration = _对齐h3时长(float(视频时长))
        image_rule = {
            "T2VA": "不连接参考图片。",
            "I2VA": "连接恰好 1 张图片，并把它作为 0.00 秒精确首帧。",
            "FL2VA": "按顺序连接恰好 2 张图片，分别作为精确首帧和精确尾帧。",
            "L2VA": "连接恰好 1 张图片，并把它作为视频结束时的精确尾帧。",
            "Ref2VA": "连接 1–9 张普通参考图片；图片提供主体、环境、材质、风格或构图语言，不把它们自动解释为精确首尾帧。",
        }[mode]
        parts = [
            f"[QWEN_TE_H3_PROFILE={profile}]",
            f"[QWEN_TE_SKILL_ID={skill_id}]",
            f"[QWEN_TE_H3_MODE={mode}]",
            f"[QWEN_TE_H3_DURATION={actual_duration:.2f}]",
            f"请执行当前连接的 {skill_id} Skill，并只输出可直接交给 MiniMax H3 的最终英文提示词。",
            f"礼物名称：{gift_name}",
            f"礼物价格：{price} 抖币",
            f"用户目标时长：{float(视频时长):.2f} 秒",
            f"H3 对齐帧数：{aligned_frames} 帧（24 fps）",
            f"目标视频有效时长：{actual_duration:.2f} 秒",
            f"画幅比例：{画幅比例}",
            f"镜头结构：{镜头结构}",
            f"参考图片规则：{image_rule}",
        ]
        if price < 99:
            parts.append(f"价格校准规则：保留用户输入价格 {price} 抖币，但效果规格按 99 抖币最低档执行。")
        request = str(创作需求 or "").strip()
        if request:
            parts.append(f"创作需求：\n{request}")
        audio = str(声音与音乐 or "").strip()
        parts.append(f"声音与音乐要求：\n{audio}" if audio else "声音与音乐要求：无音频；overall_soundscape 和 non_diegetic_music 均为 N/A。")
        constraints = str(额外约束 or "").strip()
        if constraints:
            parts.append(f"额外约束：\n{constraints}")
        return "\n\n".join(parts), aligned_frames, actual_duration, 构建skill选择(skill_id)


class APIAgentH3提示词校验:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "H3提示词": ("STRING", {"default": "", "multiline": True}),
                "模式": (["自动识别"] + list(H3模式), {"default": "自动识别"}),
                "视频时长": ("FLOAT", {"default": 6.0, "min": 0.1, "max": 3600.0, "step": 0.1}),
                "失败处理": (["报错停止工作流", "仅输出检查结果"], {"default": "报错停止工作流"}),
                "参考图片数量": ("INT", {"default": 0, "min": 0, "max": 9, "step": 1, "tooltip": "Ref2VA 可填写实际输入图片数；0 表示只校验文本结构。"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("规范化提示词", "检查报告JSON", "是否通过")
    FUNCTION = "run"
    CATEGORY = "APIAgent/Skill流水线"

    def run(self, H3提示词, 模式, 视频时长, 失败处理, 参考图片数量=0):
        resolved_mode = _识别h3输出模式(H3提示词) if 模式 == "自动识别" else 模式
        cleaned, errors, warnings = 校验h3提示词(H3提示词, resolved_mode, float(视频时长), int(参考图片数量))
        report = json.dumps(
            {"valid": not errors, "mode": resolved_mode, "duration": round(float(视频时长), 2), "image_count": int(参考图片数量), "errors": errors, "warnings": warnings},
            ensure_ascii=False,
            indent=2,
        )
        if errors and 失败处理 == "报错停止工作流":
            raise ValueError("H3 提示词校验失败：" + "；".join(errors))
        return cleaned, report, not errors
