#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
知识库适配器工厂 — 根据 connectorType 创建对应的适配器实例
"""

from typing import Dict, Type

from .base import KBServiceAdapter
from .general_kb_adapter import GeneralKBAdapter
from .koosearch_adapter import KooSearchAdapter
from .lakesearch_adapter import LakeSearchAdapter
from .openjiuwen_adapter import OpenJiuwenKBAdapter
from .ragflow_adapter import RagFlowAdapter


# 适配器注册表：connectorType → Adapter 类
# connectorType 来自 OBS 连接文件的 connectorId 字段。
# 大小写变体在 create() 方法中做大小写不敏感匹配。
# Custom 本质上是 LakeSearch，通过环境变量读取后转换成 API 端点。
# OpenJiuwen 使用 openjiuwen 本地 RAG pipeline（Milvus + Embedding API）。
_ADAPTER_REGISTRY: Dict[str, Type[KBServiceAdapter]] = {
    "LakeSearch": LakeSearchAdapter,
    "LakeSearchInside": LakeSearchAdapter,
    "KooSearch": KooSearchAdapter,
    "KooSearchInside": KooSearchAdapter,
    "Ragflow": RagFlowAdapter,
    "General": GeneralKBAdapter,
    "Custom": LakeSearchAdapter,
    "OpenJiuwen": OpenJiuwenKBAdapter,
}


class KBAdapterFactory:

    @staticmethod
    def create(connector_type: str) -> KBServiceAdapter:
        adapter_cls = _ADAPTER_REGISTRY.get(connector_type)
        if adapter_cls is not None:
            return adapter_cls()

        # 尝试大小写不敏感匹配
        lower_type = connector_type.lower()
        for key, cls in _ADAPTER_REGISTRY.items():
            if key.lower() == lower_type:
                return cls()

        raise ValueError(
            f"Unsupported connector type: {connector_type}. "
            f"Available types: {list(set(_ADAPTER_REGISTRY.values()))}"
        )

    @staticmethod
    def register(connector_type: str, adapter_cls: Type[KBServiceAdapter]) -> None:

        _ADAPTER_REGISTRY[connector_type] = adapter_cls

    @staticmethod
    def supported_types() -> list:
        return list(_ADAPTER_REGISTRY.keys())
