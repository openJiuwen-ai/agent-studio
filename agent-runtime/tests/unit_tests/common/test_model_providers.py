#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""IRModelConfigProvider (model_providers 副本) thinking → extra_body 单元测试"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from agent_runtime.common.model_providers import IRModelConfigProvider


def _make_ir_node(thinking_config, hyper_params_override=None):
    """构建带 thinking 配置的 IR 节点"""
    hyper_params = {}
    if thinking_config is not None:
        hyper_params["thinking"] = thinking_config
    if hyper_params_override:
        hyper_params.update(hyper_params_override)

    return {
        "id": "node_llm",
        "type": "jiuwen.LLMComponent",
        "configs": {
            "model": {
                "modelName": "test-model",
                "modelType": "LLM",
                "hyperParameters": hyper_params,
                "extension": {"authId": "test_auth"},
            },
        },
    }


def _call_provider(ir_node):
    """统一调用 IRModelConfigProvider 并返回结果"""
    provider = IRModelConfigProvider()
    mock_settings = MagicMock()
    mock_settings.llm.api_key = "sk-placeholder"
    mock_settings.llm.api_base = "https://api.openai.com/v1"
    mock_settings.llm.model_name = "test-model"
    mock_settings.llm.temperature = 0.5
    mock_settings.llm.top_p = 0.5
    mock_settings.llm.timeout = 900.0
    mock_settings.llm.ssl_verify = False
    with patch("agent_runtime.common.model_providers._request_ctx") as mock_ctx, \
         patch("agent_runtime.common.model_providers.settings", mock_settings):
        mock_ctx_instance = MagicMock()
        mock_ctx_instance.headers = {"X-Auth-Token": "test_token"}
        mock_ctx.get.return_value = mock_ctx_instance
        return asyncio.run(provider.get_llm_config(ir_node))


class TestThinkingEnabled:
    """thinking.type = 'enabled' → extra_body 传递"""

    def test_thinking_enabled(self):
        ir_node = _make_ir_node({"type": "enabled"})
        result = _call_provider(ir_node)

        extra_body = getattr(result.model_config, "extra_body", None)
        assert extra_body is not None
        assert extra_body == {"thinking": {"type": "enabled"}}


class TestThinkingAbsent:
    """不配置 thinking → extra_body 为 None"""

    def test_no_thinking(self):
        ir_node = _make_ir_node(None)
        result = _call_provider(ir_node)

        extra_body = getattr(result.model_config, "extra_body", None)
        assert extra_body is None


class TestHyperParametersPropagation:
    """验证 hyperParameters 中的 max_tokens 和 frequency_penalty 正确传递到 ModelRequestConfig"""

    def test_max_tokens_propagated(self):
        """max_tokens 从 IR hyperParameters 传递到 ModelRequestConfig"""
        ir_node = _make_ir_node(None, {"max_tokens": 4096, "temperature": 0.2, "top_p": 0.6})
        result = _call_provider(ir_node)

        assert result.model_config.max_tokens == 4096

    def test_frequency_penalty_propagated(self):
        """frequency_penalty 从 IR hyperParameters 通过 extra="allow" 传递到 ModelRequestConfig"""
        ir_node = _make_ir_node(None, {"frequency_penalty": -1, "temperature": 0.2, "top_p": 0.6})
        result = _call_provider(ir_node)

        # frequency_penalty 通过 extra="allow" 机制存储在 ModelRequestConfig
        assert getattr(result.model_config, "frequency_penalty", None) == -1

    def test_all_hyper_parameters_propagated(self):
        """所有 IR hyperParameters（top_p, temperature, max_tokens, frequency_penalty）同时传递"""
        ir_node = _make_ir_node(
            None,
            {"top_p": 0.6, "temperature": 0.2, "max_tokens": 4096, "frequency_penalty": -1},
        )
        result = _call_provider(ir_node)

        assert result.model_config.temperature == 0.2
        assert result.model_config.top_p == 0.6
        assert result.model_config.max_tokens == 4096
        assert getattr(result.model_config, "frequency_penalty", None) == -1

    def test_max_tokens_absent(self):
        """IR 中没有 max_tokens → ModelRequestConfig.max_tokens 为 None"""
        ir_node = _make_ir_node(None, {"temperature": 0.5, "top_p": 0.9})
        result = _call_provider(ir_node)

        assert result.model_config.max_tokens is None

    def test_frequency_penalty_absent(self):
        """IR 中没有 frequency_penalty → ModelRequestConfig 无 frequency_penalty 字段"""
        ir_node = _make_ir_node(None, {"temperature": 0.5, "top_p": 0.9})
        result = _call_provider(ir_node)

        # 额外字段不存在时不应有 frequency_penalty
        assert getattr(result.model_config, "frequency_penalty", None) is None

    def test_max_tokens_and_frequency_penalty_in_request_params(self):
        """max_tokens 和 frequency_penalty 应出现在 model_dump 输出中（即会传递到 API 请求）"""
        ir_node = _make_ir_node(
            None,
            {"top_p": 0.6, "temperature": 0.2, "max_tokens": 4096, "frequency_penalty": -1},
        )
        result = _call_provider(ir_node)

        dumped = result.model_config.model_dump(exclude_none=True)
        assert "max_tokens" in dumped
        assert dumped["max_tokens"] == 4096
        assert "frequency_penalty" in dumped
        assert dumped["frequency_penalty"] == -1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
