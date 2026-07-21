#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
IR 相关接口定义 — 供 agentBuilder-engine workflow runner 使用的抽象契约。

实现类在 agentBuilder-engine 的 infrastructure 层提供：
- ObjectStorageProvider → agent_runtime.storage.object_storage
- ModelConfigProvider   → agent_runtime.common.model_providers
"""

from abc import ABC, abstractmethod
from typing import Optional

from agent_runtime.common.exception.errors import AgentBuilderError, ExtensionStatusCode
from openjiuwen.core.workflow.components.llm.llm_comp import LLMCompConfig

# Storage 异常与 ObjectStorageProvider 已迁移至共享包 ``storage``（agent_runtime /
# agent_builder 共用）。这里保留为别名，使 ``from agent_runtime.common.ir_interfaces
# import StorageNotFoundError`` 等既有引用继续可用（同一类对象）。
from storage.exceptions import (  # noqa: F401
    StorageConfigError,
    StorageNotFoundError,
    StorageReadError,
    StorageWriteError,
)
from storage.object_storage import ObjectStorageProvider  # noqa: F401


class ModelConfigProvider(ABC):
    """模型配置提供者接口"""

    @abstractmethod
    async def get_llm_config(
        self,
        ir_node: dict,
        global_config: Optional[dict] = None,
    ) -> LLMCompConfig:
        """从 IR 节点获取 LLM 组件配置

        Args:
            ir_node: IR 节点配置
            global_config: 全局模型配置

        Returns:
            LLMCompConfig: LLM 组件配置
        """
        pass


class KnowledgeBaseConfigProvider(ABC):
    """知识库配置提供者接口

    从 OBS 文件读取知识库连接配置（endpoint、auth 等），
    与 ModelConfigProvider 的设计模式对齐：IR 提供引用 ID，Provider 负责解析具体连接信息。
    """

    @abstractmethod
    async def get_kb_config(
        self,
        ir_node: dict,
        global_config: Optional[dict] = None,
    ) -> dict:
        """从 IR 节点获取知识库检索配置

        Args:
            ir_node: IR 节点配置，包含 connectionId、knowledgeBaseIds 等
            global_config: 全局配置

        Returns:
            dict: 知识库检索配置，包含:
                - connection: KBConnectionConfig 连接信息
                - knowledge_bases: list[KBReferenceConfig] 知识库列表
                - retrieval_params: dict 检索参数
        """
        pass
