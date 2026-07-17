#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""OBSModelConfigProvider 单元测试（薄配置版）。

``get_llm_config`` 不访问 OBS / cache，只构建 ``client_provider="studio"`` 的薄配置
（extra: model_service_id / auth_id / refresh）并透传超参数；真实解析在
``StudioModelClient.invoke`` 时由 ``model_service.resolver`` 完成（其测试见
tests/unit_tests/model_service/test_resolver.py）。本文件为纯测，无需 mock。
"""

import asyncio

import pytest
from agent_runtime.common.model_providers import OBSModelConfigProvider


def _make_ir_node(model_name="svc-123", auth_id="auth-1", hyperparams=None, extension=None):
    """构建 IR 节点。hyperparams → configs.model.hyperParameters。"""
    return {
        "configs": {
            "model": {
                "modelName": model_name,
                "hyperParameters": hyperparams or {},
                "extension": {"authId": auth_id, **(extension or {})},
            }
        }
    }


class TestOBSModelConfigProviderThin:
    """薄配置：产出 client_provider="studio" + extra 解析输入。"""

    @staticmethod
    def _run(coro):
        return asyncio.run(coro)

    def test_thin_config_basic(self):
        ir = _make_ir_node("svc-123", "auth-1", {"temperature": 0.7, "top_p": 0.9})
        cfg = self._run(OBSModelConfigProvider().get_llm_config(ir))
        mcc = cfg.model_client_config
        assert mcc.client_provider == "studio"
        assert mcc.api_key == "sk-placeholder"                 # 占位
        assert mcc.api_base == "https://studio-placeholder"    # 占位
        assert getattr(mcc, "model_service_id") == "svc-123"
        assert getattr(mcc, "auth_id") == "auth-1"
        assert getattr(mcc, "refresh") is False
        assert cfg.model_config.temperature == 0.7
        assert cfg.model_config.top_p == 0.9

    def test_pipe_delimited_model_name(self):
        ir = _make_ir_node("svc-123|dep-9")
        mcc = self._run(OBSModelConfigProvider().get_llm_config(ir)).model_client_config
        # pipe 切分 → 取第一段作 modelServiceId
        assert getattr(mcc, "model_service_id") == "svc-123"

    def test_missing_model_name_raises(self):
        ir = {"configs": {"model": {"hyperParameters": {}, "extension": {}}}}
        with pytest.raises(ValueError):
            self._run(OBSModelConfigProvider().get_llm_config(ir))

    def test_thinking_extra_body(self):
        ir = _make_ir_node("svc", hyperparams={"thinking": {"type": "enabled"}})
        cfg = self._run(OBSModelConfigProvider().get_llm_config(ir))
        assert cfg.model_config.extra_body == {"thinking": {"type": "enabled"}}

    def test_thinking_without_type_ignored(self):
        ir = _make_ir_node("svc", hyperparams={"thinking": {"foo": "bar"}})  # 无 type
        cfg = self._run(OBSModelConfigProvider().get_llm_config(ir))
        assert cfg.model_config.extra_body is None

    def test_frequency_penalty_propagated(self):
        ir = _make_ir_node("svc", hyperparams={"frequency_penalty": 0.5})
        cfg = self._run(OBSModelConfigProvider().get_llm_config(ir))
        assert cfg.model_config.frequency_penalty == 0.5

    def test_max_tokens_propagated(self):
        ir = _make_ir_node("svc", hyperparams={"max_tokens": 512})
        cfg = self._run(OBSModelConfigProvider().get_llm_config(ir))
        assert cfg.model_config.max_tokens == 512

    def test_refresh_from_extension(self):
        ir = _make_ir_node("svc", extension={"refresh": True})
        mcc = self._run(OBSModelConfigProvider().get_llm_config(ir)).model_client_config
        assert getattr(mcc, "refresh") is True

    def test_model_request_model_is_placeholder(self):
        # ModelRequestConfig.model 是占位（model_service_id），真实 model_name 由 resolver 在 invoke 覆盖
        ir = _make_ir_node("svc-7")
        cfg = self._run(OBSModelConfigProvider().get_llm_config(ir))
        assert cfg.model_config.model_name == "svc-7"
