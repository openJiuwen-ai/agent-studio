# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""规划链身份补透：IR 元数据 agent 名接到 layer 默认身份。

部署实证（多智能体控制器规划链）：装饰器真身 llm span 带 usage/TTFT 但缺
gen_ai.agent.name——ir_converter 只把 agent_id 喂进 AgentCoreModelLayer
（default_agent_id），agent 名仅从 extension 键取、无调用方回退；规划链
extension 不带名 → default_agent_name 为空 → handler 侧
`if info.get("agent_name")` 判空跳过 → 真身 span 无名。本文件钉死
「IR agentName → identifiers.agent_name → layer 默认名」接线与优先级：
extension 显式名 > IR 元数据名 > 双缺省空串（wire 不变）。
"""

import pytest

from jiuwen.serve.controllers.execution.ir_converter import (
    IRConverter,
    _LLMModelIdentifiers,
)

# 套件既有惯例：契约测试直接触达受保护成员，经 getattr 规避
# G.CLS.11（pylint pragma 对 CodeCheck 不生效）
_create_agent_core_llm_model = getattr(IRConverter, "_create_agent_core_llm_model")
_create_llm_model = getattr(IRConverter, "_create_llm_model")


def _fake_layer_cls(captured: dict):
    class _FakeLayer:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    return _FakeLayer


@pytest.fixture
def layer_wiring(monkeypatch):
    """替换 layer 构造与模型注册，隔离 provider 依赖，只看接线参数。"""
    captured: dict = {}
    import jiuwen.integration.agent_core_model_new as layer_mod

    monkeypatch.setattr(layer_mod, "AgentCoreModelLayer", _fake_layer_cls(captured))

    async def _no_register(model_id, model_configs):
        return None

    monkeypatch.setattr(IRConverter, "_register_agent_core_llm_model", _no_register)
    return captured


class TestAgentNameFallback:
    """agent 名回退链：extension > 调用方（IR 元数据）> 空。"""

    @pytest.mark.asyncio
    async def test_ir_agent_name_falls_back_to_layer(self, layer_wiring):
        await _create_agent_core_llm_model(
            {"modelId": "m1"},
            task_id="t1",
            agent_id="a1",
            conversation_id="c1",
            agent_name="规划智能体",
        )
        assert layer_wiring["default_agent_name"] == "规划智能体"
        assert layer_wiring["default_agent_id"] == "a1"

    @pytest.mark.asyncio
    async def test_extension_name_wins_over_ir_name(self, layer_wiring):
        await _create_agent_core_llm_model(
            {"modelId": "m1", "extension": {"agent_name": "扩展名"}},
            task_id="t1",
            agent_id="a1",
            agent_name="规划智能体",
        )
        assert layer_wiring["default_agent_name"] == "扩展名"

    @pytest.mark.asyncio
    async def test_both_absent_keeps_empty_wire(self, layer_wiring):
        await _create_agent_core_llm_model(
            {"modelId": "m1"},
            task_id="t1",
            agent_id="a1",
        )
        assert layer_wiring["default_agent_name"] == ""


class TestIdentifiersCarryAgentName:
    """identifiers 三件套扩名：新字段缺省空串，旧构造不变。"""

    @staticmethod
    def test_new_field_roundtrip():
        ids = _LLMModelIdentifiers(
            task_id="t",
            conversation_id="c",
            agent_id="a",
            agent_name="规划智能体",
        )
        assert ids.agent_name == "规划智能体"

    @staticmethod
    def test_legacy_construction_defaults_empty():
        ids = _LLMModelIdentifiers(task_id="t", conversation_id="c", agent_id="a")
        assert ids.agent_name == ""


class TestCreateLlmModelForwardsName:
    """_create_llm_model 中转：identifiers.agent_name 透传到 agent-core 分支。"""

    @pytest.mark.asyncio
    async def test_forwards_identifiers_agent_name(self, monkeypatch):
        captured = {}

        async def _fake_create(
            model_configs, task_id, agent_id, conversation_id="", agent_name=""
        ):
            captured.update(agent_id=agent_id, agent_name=agent_name)
            return object()

        monkeypatch.setattr(
            IRConverter, "_use_agent_core_model", lambda mc: True
        )
        monkeypatch.setattr(IRConverter, "_create_agent_core_llm_model", _fake_create)
        await _create_llm_model(
            {"modelId": "m"},
            cust_headers={},
            project_id="",
            identifiers=_LLMModelIdentifiers(
                task_id="t",
                conversation_id="c",
                agent_id="a1",
                agent_name="规划智能体",
            ),
        )
        assert captured == {"agent_id": "a1", "agent_name": "规划智能体"}
