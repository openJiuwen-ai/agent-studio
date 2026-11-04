# -*- coding: UTF-8 -*-
"""jiuwen.LLMReAct 节点转换单测：字段映射 + 图构建。"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jiuwen.serve.controllers.execution.ir_converter import _convert_llm_react_node

FIXTURE = os.path.join(
    os.path.dirname(__file__), "..", "..", "resource", "ir_file", "llm_react_amap.json"
)


def _load_agent_configs():
    with open(FIXTURE, encoding="utf-8") as f:
        ir = json.load(f)
    for c in ir["components"]:
        if c["type"] == "jiuwen.LLMReAct":
            return c["configs"], c["id"]
    raise AssertionError("fixture missing jiuwen.LLMReAct node")


class TestConvertLlmReactNode:
    @pytest.mark.asyncio
    async def test_field_mapping(self):
        """完整字段映射：systemPrompt/maxIteration/model/plugins。"""
        configs, node_id = _load_agent_configs()

        mock_llm_comp_config = MagicMock()
        mock_model = MagicMock()
        mock_provider = AsyncMock()
        mock_provider.get_llm_config = AsyncMock(return_value=mock_llm_comp_config)
        mock_tool = MagicMock()
        mock_tool.card.name = "Gaud_Map"

        with patch(
            "jiuwen.serve.controllers.execution.ir_converter._get_model_config_provider",
            return_value=mock_provider,
        ), patch(
            "jiuwen.extension.wrapper.restful_api_loader.load_restful_api_from_ir",
            return_value="tool_id_1",
        ), patch(
            # 遥测装饰与 core 能力态耦合（能装饰时注入 _TraceProxy）：字段映射
            # 测试只关心映射，透传解耦；装饰接线由 AST 契约测试钉住
            "agent_runtime.common.trace_compat.build_traced_model",
            side_effect=lambda model, **kwargs: model,
        ), patch(
            "openjiuwen.core.foundation.llm.Model", return_value=mock_model
        ) as mock_model_cls, patch(
            "openjiuwen.core.runner.Runner"
        ) as mock_runner_cls, patch(
            "jiuwen.serve.controllers.execution.ir_converter.FlowAgent"
        ) as mock_flow_agent_cls:
            mock_runner_cls.resource_mgr.get_tool = MagicMock(return_value=mock_tool)

            agent = await _convert_llm_react_node(configs, node_id)

        # model 走 provider + Model
        mock_provider.get_llm_config.assert_called_once()
        mock_model_cls.assert_called_once()

        mock_flow_agent_cls.assert_called_once()
        flow_agent_args = mock_flow_agent_cls.call_args.kwargs
        flow_agent_config = flow_agent_args["config"]

        # FlowAgentConfig 字段
        assert flow_agent_config.system_prompt == "{{user_query}}"
        assert flow_agent_config.max_iteration == 9

        # tools + model 注入
        assert flow_agent_args["tools"] == [mock_tool]
        assert flow_agent_args["model"] is mock_model
        assert agent is mock_flow_agent_cls.return_value

    @pytest.mark.asyncio
    async def test_minimal_config_defaults(self):
        """最小配置：缺 maxIteration→默认 9，无 plugins→空 tools。"""
        configs = {
            "systemPrompt": "",
            "model": {
                "modelName": "m",
                "extension": {"authId": "a"},
                "modelType": "LLM",
            },
        }
        mock_provider = AsyncMock()
        mock_provider.get_llm_config = AsyncMock(return_value=MagicMock())

        with patch(
            "jiuwen.serve.controllers.execution.ir_converter._get_model_config_provider",
            return_value=mock_provider,
        ), patch(
            "openjiuwen.core.foundation.llm.Model", return_value=MagicMock()
        ), patch(
            "jiuwen.serve.controllers.execution.ir_converter.FlowAgent"
        ) as mock_flow_agent_cls:
            await _convert_llm_react_node(configs, "n1")

        flow_agent_args = mock_flow_agent_cls.call_args.kwargs
        assert flow_agent_args["config"].max_iteration == 9
        assert flow_agent_args["tools"] == []

    @pytest.mark.asyncio
    async def test_plugin_load_failure_skipped(self):
        """单个 plugin 加载失败 → 跳过，不中断；其余正常。"""
        configs = {
            "systemPrompt": "x",
            "model": {
                "modelName": "m",
                "extension": {"authId": "a"},
                "modelType": "LLM",
            },
            "plugins": [
                {
                    "name": "bad",
                    "id": "bad_id",
                    "url": "http://x",
                    "method": "GET",
                    "auth": {},
                    "arguments": [],
                    "response": [],
                    "pluginDependency": {
                        "paramsWrapper": {
                            "outputList": False,
                            "inputList": False,
                        }
                    },
                },
                {
                    "name": "good",
                    "id": "good_id",
                    "url": "http://y",
                    "method": "GET",
                    "auth": {},
                    "arguments": [],
                    "response": [],
                    "pluginDependency": {
                        "paramsWrapper": {
                            "outputList": False,
                            "inputList": False,
                        }
                    },
                },
            ],
        }
        mock_provider = AsyncMock()
        mock_provider.get_llm_config = AsyncMock(return_value=MagicMock())
        mock_tool_good = MagicMock()
        mock_tool_good.card.name = "good"

        call_count = {"n": 0}

        def fake_load(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("plugin bad fails")
            return "good_tool_id"

        with patch(
            "jiuwen.serve.controllers.execution.ir_converter._get_model_config_provider",
            return_value=mock_provider,
        ), patch("openjiuwen.core.foundation.llm.Model", return_value=MagicMock()), patch(
            "openjiuwen.core.runner.Runner"
        ) as mock_runner_cls, patch(
            "jiuwen.serve.controllers.execution.ir_converter.FlowAgent"
        ) as mock_flow_agent_cls:
            # patch load_restful_api_from_ir via the module it's used in
            with patch(
                "jiuwen.extension.wrapper.restful_api_loader.load_restful_api_from_ir",
                side_effect=fake_load,
            ):
                mock_runner_cls.resource_mgr.get_tool = MagicMock(return_value=mock_tool_good)
                await _convert_llm_react_node(configs, "n1")

        # bad 被跳过，good 保留
        assert mock_flow_agent_cls.call_args.kwargs["tools"] == [mock_tool_good]


class TestLlmReactInWorkflow:
    @pytest.mark.asyncio
    async def test_create_component_does_not_raise_unsupported(self):
        """含 jiuwen.LLMReAct 的节点经 _create_component 不再抛 unsupported。"""
        from jiuwen.serve.controllers.execution.ir_converter import IRConverter
        from jiuwen.extension.workflow_node.flow_agent import FlowAgent

        with open(FIXTURE, encoding="utf-8") as f:
            ir = json.load(f)
        agent_node = next(c for c in ir["components"] if c["type"] == "jiuwen.LLMReAct")

        mock_provider = AsyncMock()
        mock_provider.get_llm_config = AsyncMock(return_value=MagicMock())

        with patch(
            "jiuwen.serve.controllers.execution.ir_converter._get_model_config_provider",
            return_value=mock_provider,
        ), patch("openjiuwen.core.foundation.llm.Model", return_value=MagicMock()), patch(
            "openjiuwen.core.runner.Runner"
        ) as mock_runner_cls, patch(
            "jiuwen.extension.wrapper.restful_api_loader.load_restful_api_from_ir",
            return_value="Gaud_Map",
        ):
            mock_tool = MagicMock()
            mock_tool.card.name = "Gaud_Map"
            mock_runner_cls.resource_mgr.get_tool = MagicMock(return_value=mock_tool)

            component_info = await IRConverter.create_single_component(
                ir, agent_node["id"]
            )

        # 不抛 "unsupported workflow component type for openjiuwen workflow: jiuwen.LLMReAct"
        assert isinstance(component_info.component, FlowAgent)
        assert component_info.node_type == "jiuwen.LLMReAct"


class TestTraceIdentityChannel:
    """业务身份经模块级 ContextVar 传递（不新增 _create_component 形参）。

    契约：_create_component 的签名必须保持向后兼容——大量存量测试（含外部
    在途分支）按旧签名 mock 它，任何新增 kwarg 都会令其 TypeError（CI 实证
    过一次）。身份改由 _TRACE_IDENTITY 通道传入，对 mock 完全透明。
    """

    def test_create_component_signature_has_no_identity_kwarg(self):
        """签名契约：不得出现 identity 相关形参。"""
        import inspect

        from jiuwen.serve.controllers.execution.ir_converter import IRConverter

        params = inspect.signature(IRConverter._create_component).parameters
        assert "trace_identity" not in params, (
            "_create_component 不得新增 identity 形参：存量 mock 按旧签名定义，"
            "新增 kwarg 会令其 TypeError（改用 _TRACE_IDENTITY ContextVar）"
        )

    @pytest.mark.asyncio
    async def test_identity_flows_via_context_var_to_react_model(self):
        """ContextVar 置值 → react 分支构建 model 时身份送达 build_traced_model。"""
        from jiuwen.serve.controllers.execution.ir_converter import (
            IRConverter,
            _TRACE_IDENTITY,
        )

        with open(FIXTURE, encoding="utf-8") as f:
            ir = json.load(f)
        agent_node = next(c for c in ir["components"] if c["type"] == "jiuwen.LLMReAct")

        mock_provider = AsyncMock()
        mock_provider.get_llm_config = AsyncMock(return_value=MagicMock())
        captured: dict = {}

        def fake_build_traced_model(model, session=None, session_id=None, identity=None):
            captured["identity"] = identity
            return model

        with patch(
            "jiuwen.serve.controllers.execution.ir_converter._get_model_config_provider",
            return_value=mock_provider,
        ), patch(
            "agent_runtime.common.trace_compat.build_traced_model",
            side_effect=fake_build_traced_model,
        ), patch(
            "openjiuwen.core.foundation.llm.Model", return_value=MagicMock()
        ), patch("openjiuwen.core.runner.Runner"), patch(
            "jiuwen.extension.wrapper.restful_api_loader.load_restful_api_from_ir",
            return_value="Gaud_Map",
        ):
            token = _TRACE_IDENTITY.set({"workflow_id": "wf-biz-1"})
            try:
                await IRConverter._create_component(agent_node, None)
            finally:
                _TRACE_IDENTITY.reset(token)

        assert captured.get("identity") == {"workflow_id": "wf-biz-1"}

    @pytest.mark.asyncio
    async def test_identity_defaults_to_none_without_context(self):
        """未置值（普通转换路径由 _add_component 包裹置值）→ identity=None。"""
        from jiuwen.serve.controllers.execution.ir_converter import (
            IRConverter,
            _TRACE_IDENTITY,
        )

        with open(FIXTURE, encoding="utf-8") as f:
            ir = json.load(f)
        agent_node = next(c for c in ir["components"] if c["type"] == "jiuwen.LLMReAct")

        mock_provider = AsyncMock()
        mock_provider.get_llm_config = AsyncMock(return_value=MagicMock())
        captured: dict = {}

        def fake_build_traced_model(model, session=None, session_id=None, identity=None):
            captured["identity"] = identity
            return model

        with patch(
            "jiuwen.serve.controllers.execution.ir_converter._get_model_config_provider",
            return_value=mock_provider,
        ), patch(
            "agent_runtime.common.trace_compat.build_traced_model",
            side_effect=fake_build_traced_model,
        ), patch(
            "openjiuwen.core.foundation.llm.Model", return_value=MagicMock()
        ), patch("openjiuwen.core.runner.Runner"), patch(
            "jiuwen.extension.wrapper.restful_api_loader.load_restful_api_from_ir",
            return_value="Gaud_Map",
        ):
            assert _TRACE_IDENTITY.get() is None
            await IRConverter._create_component(agent_node, None)

        assert captured.get("identity") is None
