# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""IR content_review 配置解析 — Pydantic 模型 + 旧格式兼容转换。"""

from typing import Optional

from pydantic import BaseModel


class ActionConfig(BaseModel):
    """单个审核动作配置"""
    enable: bool = True
    type: str = "filter"     # filter / replace / reply
    content: str = ""


class RuleActions(BaseModel):
    """一条规则的双通道动作"""
    input: Optional[ActionConfig] = None
    output: Optional[ActionConfig] = None


class Rule(BaseModel):
    """一条审核规则"""
    keywords: list[str]
    actions: RuleActions


class ContentReviewConfig(BaseModel):
    """content_review 新格式配置"""
    enabled: bool = False
    rules: list[Rule] = []


def normalize_content_review(raw: dict) -> dict:
    """将 content_review 配置统一转换为引擎消费的新格式。

    兼容两种输入：
    - 新格式：含 rules 字段，直接校验后返回
    - 旧格式：含 filter/replace/reply 平铺字段，转换为新格式

    注意：此函数仅负责"读取方向"的兼容，不负责"写回方向"的降级。
    新格式→旧格式的降级由编辑器/IR 管理层负责。
    """
    if not isinstance(raw, dict):
        return {"enabled": False, "rules": []}

    # 新格式：直接校验
    if "rules" in raw:
        validated = ContentReviewConfig.model_validate(raw)
        return validated.model_dump()

    # 旧格式：转换
    return _convert_legacy_format(raw)


def _convert_legacy_format(raw: dict) -> dict:
    """将旧格式 filter/replace/reply 平铺结构转换为新格式 rules 列表。"""
    rules = []

    # filter: 仅输出侧过滤
    filter_cfg = raw.get("filter", {})
    keywords_str = filter_cfg.get("keywords", "") if isinstance(filter_cfg, dict) else ""
    if keywords_str:
        rules.append({
            "keywords": [k.strip() for k in keywords_str.split(",") if k.strip()],
            "actions": {
                "output": {"enable": True, "type": "filter", "content": ""},
            },
        })

    # replace: 输出侧替换
    for item in raw.get("replace", []):
        if not isinstance(item, dict):
            continue
        kw = item.get("keywords", "")
        kw_list = (
            [k.strip() for k in kw.split(",") if k.strip()]
            if isinstance(kw, str)
            else kw
        )
        if kw_list:
            rules.append({
                "keywords": kw_list,
                "actions": {
                    "output": {
                        "enable": True,
                        "type": "replace",
                        "content": item.get("content") or item.get("replace", ""),
                    },
                },
            })

    # reply: 输入+输出双侧阻断
    for item in raw.get("reply", []):
        if not isinstance(item, dict):
            continue
        kw = item.get("keywords", "")
        kw_list = (
            [k.strip() for k in kw.split(",") if k.strip()]
            if isinstance(kw, str)
            else kw
        )
        if kw_list:
            rules.append({
                "keywords": kw_list,
                "actions": {
                    "input": {
                        "enable": True,
                        "type": "reply",
                        "content": item.get("content") or item.get("reply", ""),
                    },
                    "output": {
                        "enable": True,
                        "type": "reply",
                        "content": item.get("content") or item.get("reply", ""),
                    },
                },
            })

    return {"enabled": raw.get("enabled", False), "rules": rules}
