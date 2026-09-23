#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _safe_env_float(key: str, default: str) -> float:
    """安全读取环境变量为 float，非法值回退默认值并告警。"""
    raw = os.environ.get(key, default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        logger.warning(
            "环境变量 %s 值非法(%r)，回退默认值 %s", key, raw, default,
        )
        return float(default)


# 阈值范围，从环境变量读取，与 M 侧 application-manager.yml 对齐
THRESHOLD_MIN = _safe_env_float("KNOWLEDGE_RECALL_THRESHOLD_MIN", "0")
THRESHOLD_MAX = _safe_env_float("KNOWLEDGE_RECALL_THRESHOLD_MAX", "1")
if THRESHOLD_MIN > THRESHOLD_MAX:
    logger.warning(
        "KNOWLEDGE_RECALL_THRESHOLD_MIN(%s) > MAX(%s)，已自动交换",
        THRESHOLD_MIN, THRESHOLD_MAX,
    )
    THRESHOLD_MIN, THRESHOLD_MAX = THRESHOLD_MAX, THRESHOLD_MIN


def clamp_threshold(value: float) -> float:
    """将阈值 clamp 到 [min, max] 范围内。"""
    if value > THRESHOLD_MAX:
        return THRESHOLD_MAX
    if value < THRESHOLD_MIN:
        return THRESHOLD_MIN
    return value


@dataclass
class KBSearchResult:
    """单条知识库检索结果。"""

    text: str = ""                              # 检索到的文本内容
    score: float = 0.0                          # 相关性分数
    source: str = ""                            # 来源知识库 ID（兼容旧字段，等同于 knowledge_base_id）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据
    knowledge_base_id: str = ""
    knowledge_base_type: str = ""               # INTERNAL / EXTERNAL
    file_id: str = ""
    document_name: str = ""
    subtitle: str = ""
    serial_number: int = 0                      # 每次请求从 1 自增
    retrieval_id: str = ""                      # 每次请求生成唯一 UUID
    type: str = "doc"                           # "doc" or "faq"


@dataclass
class DatasetSearchRequest:

    endpoint: str
    query: str
    dataset_ids: List[str]
    headers: Dict[str, Any]
    retrieval_params: Dict[str, Any] = field(default_factory=dict)
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SingleKBSearchRequest:

    endpoint: str
    project_id: str
    app_id: str
    repo_id: str
    query: str
    top_k: int
    headers: Dict[str, Any]
    search_mode: str = "doc"
    tags: Optional[List[str]] = None


class KBServiceAdapter(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        connection_config: dict,
        knowledge_bases: list,
        retrieval_params: dict,
    ) -> List[KBSearchResult]:

        pass
