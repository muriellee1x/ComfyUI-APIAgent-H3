# -*- coding: utf-8 -*-
"""
ComfyUI API Skill/H3 插件
"""

from .skill_loader import APIAgentSkill加载器
from .skill_pipeline import APIAgent直播礼物任务构建器
from .api_pipeline import APIAgentAPI配置, APIAgentSkillAPI单次执行, APIAgent图像SkillAPI单次执行

NODE_CLASS_MAPPINGS = {
    "APIAgent_SkillLoader": APIAgentSkill加载器,
    "APIAgent_LiveGiftTaskBuilder": APIAgent直播礼物任务构建器,
    "APIAgent_OpenAIAPIConfig": APIAgentAPI配置,
    "APIAgent_SkillSingleRunAPI": APIAgentSkillAPI单次执行,
    "APIAgent_ImageSkillSingleRunAPI": APIAgent图像SkillAPI单次执行,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "APIAgent_SkillLoader": "APIAgent Skill加载器",
    "APIAgent_LiveGiftTaskBuilder": "APIAgent 直播礼物任务构建器",
    "APIAgent_OpenAIAPIConfig": "APIAgent API配置",
    "APIAgent_SkillSingleRunAPI": "APIAgent Skill单次执行",
    "APIAgent_ImageSkillSingleRunAPI": "APIAgent 图像Skill单次执行",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
