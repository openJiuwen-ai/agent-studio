#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
知识库检索适配器 — HTTP API 方式调用外部知识库服务

提供统一的检索接口，屏蔽不同知识库服务（LakeSearch、KooSearch、RagFlow 等）的 API 差异。
所有适配器只负责 HTTP API 调用，不涉及 Embedding / VectorStore / LLM。
"""

from .base import KBServiceAdapter, KBSearchResult
from .factory import KBAdapterFactory
from .general_kb_adapter import GeneralKBAdapter
from .koosearch_adapter import KooSearchAdapter
from .lakesearch_adapter import LakeSearchAdapter
from .openjiuwen_adapter import OpenJiuwenKBAdapter
from .ragflow_adapter import RagFlowAdapter

__all__ = [
    "KBServiceAdapter",
    "KBSearchResult",
    "GeneralKBAdapter",
    "KooSearchAdapter",
    "LakeSearchAdapter",
    "OpenJiuwenKBAdapter",
    "RagFlowAdapter",
    "KBAdapterFactory",
]
