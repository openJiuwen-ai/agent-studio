# -*- coding: utf-8 -*-
"""内部请求目标枚举 — 区分 boundary 转发和下游 rename 的 Target

与 Java 侧 InternalTarget 枚举保持一致（ Schema 一致性）。
"""

from __future__ import annotations

from enum import Enum


class InternalTarget(Enum):
    """内部请求目标枚举"""

    # ── boundary 转发 ──
    #: manager→runtime 入站 boundary
    AGENT_RUNTIME_INBOUND = "AGENT_RUNTIME_INBOUND"
    #: manager→agent_builder 入站 boundary（前置）
    AGENT_BUILDER_INBOUND = "AGENT_BUILDER_INBOUND"

    # ── 核心必须启用集 ──
    #: LakeSearch 下游 rename
    LAKESEARCH = "LAKESEARCH"
    #: runtime LLM Chat 下游 rename
    RUNTIME_LLM_CHAT = "RUNTIME_LLM_CHAT"
    #: runtime MCP 外部服务调用下游 rename（同构，剥 cust- 前缀 + request-over-config）
    RUNTIME_MCP_CALL = "RUNTIME_MCP_CALL"
    #: runtime 知识库检索下游 rename（同构，剥 cust- 前缀 + request-over-config）
    RUNTIME_KB_CALL = "RUNTIME_KB_CALL"
    #: IR auth_keys forward-list 声明
    IR_AUTH_KEYS = "IR_AUTH_KEYS"

    # ── 条件启用集 ──
    #: runtime Search
    RUNTIME_SEARCH = "RUNTIME_SEARCH"
    #: Builder Chat
    BUILDER_LLM_CHAT = "BUILDER_LLM_CHAT"
    #: Builder Embedding
    BUILDER_MODEL_EMBEDDING = "BUILDER_MODEL_EMBEDDING"
    #: Builder Rerank
    BUILDER_MODEL_RERANK = "BUILDER_MODEL_RERANK"
    #: CUSTOM_APIKEY 探针
    MODEL_AUTH_CHECK = "MODEL_AUTH_CHECK"

    # ── 补充集（enabled=true 时） ──
    #: Memory 入站
    MEMORY_INBOUND = "MEMORY_INBOUND"
    #: Memory 内部 LLM
    MEMORY_LLM = "MEMORY_LLM"
