#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""IRModelConfigProvider thinking → extra_body 单元测试"""

# NOTE: These tests are TDD — the "enabled"/"disabled" tests are expected to FAIL
# until the thinking→extra_body implementation is added in a subsequent task.

import asyncio

import pytest

from agent_runtime.ir_config.model_config import IRModelConfigProvider


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """为所有测试设置最小环境变量，避免 Provider 抛异常"""
    monkeypatch.setenv("IR_LLM_API_KEY", "test_key")
    monkeypatch.setenv("MODEL_ROUTER_API", "https://test.api.example.com")


def _make_ir_node(thinking_config):
    """构建带 thinking 配置的 IR 节点"""
    hyper_params = {
        "temperature": 0.5,
        "top_p": 0.5,
    }
    if thinking_config is not None:
        hyper_params["thinking"] = thinking_config

    return {
        "id": "node_llm",
        "type": "jiuwen.LLMComponent",
        "configs": {
            "modelConfig": {
                "modelName": "test-model",
                "modelType": "LLM",
                "hyperParameters": hyper_params,
                "extension": {"authId": "test_auth"},
            },
        },
    }


class TestThinkingEnabled:
    """thinking.type = 'enabled' → extra_body 传递"""

    def test_llm_config_thinking_enabled(self):
        """get_llm_config: thinking=enabled 时 extra_body 包含 thinking"""
        ir_node = _make_ir_node({"type": "enabled"})
        provider = IRModelConfigProvider()

        result = asyncio.run(provider.get_llm_config(ir_node))

        model_config = result.model_config
        extra_body = getattr(model_config, "extra_body", None)
        assert extra_body is not None
        assert extra_body == {"thinking": {"type": "enabled"}}


class TestThinkingDisabled:
    """thinking.type = 'disabled' → extra_body 包含 disabled"""

    def test_llm_config_thinking_disabled(self):
        ir_node = _make_ir_node({"type": "disabled"})
        provider = IRModelConfigProvider()

        result = asyncio.run(provider.get_llm_config(ir_node))

        model_config = result.model_config
        extra_body = getattr(model_config, "extra_body", None)
        assert extra_body == {"thinking": {"type": "disabled"}}


class TestThinkingAbsent:
    """不配置 thinking → extra_body 为 None"""

    def test_llm_config_no_thinking(self):
        ir_node = _make_ir_node(None)
        provider = IRModelConfigProvider()

        result = asyncio.run(provider.get_llm_config(ir_node))

        model_config = result.model_config
        extra_body = getattr(model_config, "extra_body", None)
        assert extra_body is None


class TestThinkingInvalid:
    """thinking 格式异常 → 忽略，不传 extra_body"""

    def test_thinking_not_dict(self):
        """thinking 为字符串，忽略"""
        ir_node = _make_ir_node("enabled")
        provider = IRModelConfigProvider()

        result = asyncio.run(provider.get_llm_config(ir_node))

        extra_body = getattr(result.model_config, "extra_body", None)
        assert extra_body is None

    def test_thinking_no_type_key(self):
        """thinking 为 dict 但无 type 键，忽略"""
        ir_node = _make_ir_node({"foo": "bar"})
        provider = IRModelConfigProvider()

        result = asyncio.run(provider.get_llm_config(ir_node))

        extra_body = getattr(result.model_config, "extra_body", None)
        assert extra_body is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
