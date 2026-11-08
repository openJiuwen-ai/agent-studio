# -*- coding: UTF-8 -*-
"""create_trace_manager 模型身份单测（桥 span 的 class_name 语义）。

OTel 双写桥的 instance_info.class_name 会被 core handler 当模型名消费
（span 名 llm.<class_name>、gen_ai.request.model）；core decorator 路径
同键装的是探针解析出的模型名（decorate_model_with_trace）。agent-core
分支的 llm 是 AgentCoreModelLayer 包装类，类名对模型身份无意义，此前
桥 span 的 request.model 因此是类名。本文件锁住解析优先级：显示名
（model_display_name，OBS 网关下随 AgentCoreModelLayer 携带的人读名，
与 core 显示名线同向）→ model_name（网关生态下为 model_id）→ Python
类名；instance_attributes.model 维持 model_id 原语义（缺名 "undefined"）
供 insight 记账身份，不随显示名改写。
"""

import pytest

from jiuwen.planner.common import stream_post_utils as spu


class _LayerLike:
    """模拟 AgentCoreModelLayer：仅暴露 model_name（可选 model_display_name）的包装形态。"""

    def __init__(self, model_name=None, model_display_name=None):
        if model_name is not None:
            self.model_name = model_name
        if model_display_name is not None:
            self.model_display_name = model_display_name


class _FactoryLike:
    """模拟 legacy 工厂产出：不暴露 model_name 属性。"""


class TestCreateTraceManagerModelIdentity:
    @pytest.fixture
    def captured(self, monkeypatch):
        """打桩 generate_manager，捕获透传的 instance_info。"""
        calls = {}

        def _fake_generate_manager(trace_handlers, instance_info):
            calls["trace_handlers"] = trace_handlers
            calls["instance_info"] = instance_info
            return object()

        monkeypatch.setattr(
            spu.TraceManager, "generate_manager", _fake_generate_manager
        )
        return calls

    @staticmethod
    def test_model_name_present_uses_real_name(captured):
        """有真实 model_name：class_name 装模型名，不再是包装类类名。"""
        spu.create_trace_manager(_LayerLike("qwen3-max"), [], ["h"])
        info = captured["instance_info"]
        assert info["class_name"] == "qwen3-max"
        assert info["instance_attributes"]["model"] == "qwen3-max"

    @staticmethod
    def test_model_name_missing_falls_back_to_class(captured):
        """无 model_name 属性：class_name 退类名；insight 侧 model 保持 "undefined"。"""
        spu.create_trace_manager(_FactoryLike(), [], ["h"])
        info = captured["instance_info"]
        assert info["class_name"] == "_FactoryLike"
        assert info["instance_attributes"]["model"] == "undefined"

    @staticmethod
    def test_model_name_empty_falls_back_to_class(captured):
        """model_name 为空串：视为缺名退类名，不产出空模型身份。"""
        spu.create_trace_manager(_LayerLike(""), [], ["h"])
        info = captured["instance_info"]
        assert info["class_name"] == "_LayerLike"
        assert info["instance_attributes"]["model"] == ""

    @staticmethod
    def test_display_name_wins_over_model_id(captured):
        """显示名优先：class_name 装人读名；insight 侧 model 保持 model_id。"""
        spu.create_trace_manager(
            _LayerLike("3f2b8c1e-uuid", model_display_name="DeepSeek-V3"), [], ["h"]
        )
        info = captured["instance_info"]
        assert info["class_name"] == "DeepSeek-V3"
        assert info["instance_attributes"]["model"] == "3f2b8c1e-uuid"

    @staticmethod
    def test_display_name_empty_keeps_model_id(captured):
        """显示名为空串（provider 无此字段）：回退 model_id，行为与未加字段前一致。"""
        spu.create_trace_manager(
            _LayerLike("qwen3-max", model_display_name=""), [], ["h"]
        )
        info = captured["instance_info"]
        assert info["class_name"] == "qwen3-max"
        assert info["instance_attributes"]["model"] == "qwen3-max"

    @staticmethod
    def test_legacy_layer_without_display_attr_unchanged(captured):
        """不带 model_display_name 属性的旧形态 llm：解析路径与改动前逐字节一致。"""
        spu.create_trace_manager(_LayerLike("qwen3-max"), [], ["h"])
        info = captured["instance_info"]
        assert info["class_name"] == "qwen3-max"
        assert info["instance_attributes"]["model"] == "qwen3-max"


class TestAgentCoreModelLayerDisplayName:
    """AgentCoreModelLayer 的 model_display_name 字段落位与默认值。"""

    def test_field_defaults_to_empty(self):
        from jiuwen.integration.agent_core_model_new import AgentCoreModelLayer

        layer = AgentCoreModelLayer(default_model_id="3f2b8c1e-uuid")
        assert layer.model_display_name == ""
        assert layer.model_name == "3f2b8c1e-uuid"

    def test_field_stored_normalized(self):
        from jiuwen.integration.agent_core_model_new import AgentCoreModelLayer

        layer = AgentCoreModelLayer(
            default_model_id="3f2b8c1e-uuid", model_display_name="DeepSeek-V3"
        )
        assert layer.model_display_name == "DeepSeek-V3"
        # 显示名不参与 model_name：legacy 调用方（prompt 模板选择等）不受影响。
        assert layer.model_name == "3f2b8c1e-uuid"
