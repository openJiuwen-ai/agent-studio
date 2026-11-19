# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""intent_detection._get_llm_instance 的 trace identity 会话来源单测。

静态图复用重构（54548700f）删除了实例属性 ``_session`` 的唯一写入点，
identity 读取点必须改从引擎执行上下文 ``current_component_exec()`` 取
（与 llm_chain.py:172 / questioner.py:1949 同款），否则组件实例上
残留的 ``self._session`` 读取在首调 LLM 时必然 AttributeError。
"""

import asyncio
from types import SimpleNamespace

import jiuwen.extension.workflow_node.intent_detection as intent_module
from jiuwen.extension.workflow_node.intent_detection import IntentDetection


def test_get_llm_instance_identity_from_exec_context(monkeypatch):
    """identity 的 session 实参须来自执行上下文而非实例属性 self._session。"""
    captured = {}

    async def fake_get_llm_config(conf):
        return SimpleNamespace(model_client_config={"mc": 1}, model_config={"cfg": 2})

    def fake_build_traced_model(model, session_id, identity):
        captured["identity"] = identity
        return "traced-model"

    def fake_resolve_identity(component, session):
        return ("identity-of", session)

    monkeypatch.setattr(
        "agent_runtime.common.model_adapters.adapt_intent_detection_config",
        lambda conf: conf,
    )
    monkeypatch.setattr(
        "jiuwen.serve.controllers.execution.ir_converter._get_model_config_provider",
        lambda: SimpleNamespace(get_llm_config=fake_get_llm_config),
    )
    monkeypatch.setattr(
        "agent_runtime.common.trace_compat.build_traced_model", fake_build_traced_model
    )
    monkeypatch.setattr(
        "agent_runtime.common.trace_compat.resolve_trace_identity", fake_resolve_identity
    )
    monkeypatch.setattr(intent_module, "Model", lambda **kwargs: "model-obj")
    monkeypatch.setattr(
        intent_module, "current_component_exec", lambda: ("exec-session", None, None)
    )

    # 重构后的真实组件实例不再持有 _session 属性；G.CLS.11：受保护成员经 getattr 访问
    bare = SimpleNamespace()
    get_llm_instance = getattr(IntentDetection, "_get_llm_instance")
    result = asyncio.run(get_llm_instance(bare, {"model": "t"}))

    assert result == "traced-model"
    assert captured["identity"] == ("identity-of", "exec-session")
