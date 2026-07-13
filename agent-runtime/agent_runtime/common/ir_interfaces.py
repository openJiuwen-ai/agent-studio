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


class StorageConfigError(AgentBuilderError):
    """存储配置异常 — 环境变量缺失或无效"""

    def __init__(self, msg: str = "", **kwargs):
        super().__init__(ExtensionStatusCode.STORAGE_CONFIG_ERROR, msg=msg, **kwargs)


class StorageReadError(AgentBuilderError):
    """存储读取异常 — 下载对象失败"""

    def __init__(self, msg: str = "", **kwargs):
        super().__init__(ExtensionStatusCode.STORAGE_READ_ERROR, msg=msg, **kwargs)


class StorageNotFoundError(StorageReadError):
    """存储对象不存在（S3 404/NoSuchKey 或本地文件缺失）— 区别于传输层读失败。

    继承 ``StorageReadError`` 以兼容既有 ``except StorageReadError`` 的调用方（404 仍被捕获）；
    上层（如 model_service.resolver）可按子类区分"未配置"（→None）与"OBS 不可达"（→读错误）。
    """

    def __init__(self, msg: str = "", **kwargs):
        super().__init__(msg=msg, **kwargs)


class ObjectStorageProvider(ABC):
    """对象存储提供者抽象类

    扩展时继承此类并实现 get_content()，然后通过
    WorkflowRunner 注入。
    """

    @abstractmethod
    async def get_content(self, object_key: str) -> str:
        """读取对象内容，返回 UTF-8 字符串

        Args:
            object_key: 对象 key（如 workflow/ir/xxx/xxx.json）

        Returns:
            str: 对象内容的 UTF-8 字符串

        Raises:
            StorageReadError: 读取失败
        """

    async def list_keys(self, prefix: str) -> list[str]:
        """列出指定前缀下的所有对象 key

        Args:
            prefix: 对象 key 前缀（如 "model-auth/auth/0/provider-id/"）

        Returns:
            list[str]: 匹配的对象 key 列表

        Note:
            默认实现返回空列表；子类可按需覆写。
        """
        return []


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
