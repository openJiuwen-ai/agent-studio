# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.

"""
DebugStreamFormatter 单组件调试事件 node_type 校验。

覆盖：单组件调试产出的 node_type 应使用 _COMPONENT_TYPE_DISPLAY 映射后的
展示类型（如 jiuwen.plugin → Plugin、jiuwen.llm → LLM），而非未映射的
原始 IR 类型，保证前端图标（svgMap）能正确命中。
"""

from agent_runtime.runner.debug_formatter import DebugStreamFormatter
from jiuwen.orchestration.flow.stream.base import StreamCode, StreamData


class TestDebugFormatterNodeType:
    @staticmethod
    def _make_formatter(component_type: str) -> DebugStreamFormatter:
        return DebugStreamFormatter(
            execution_id="exec-1",
            component_id="node_1",
            component_name="test",
            component_type=component_type,
            agent_id="agent-1",
            inputs={"query": "hi"},
        )

    @staticmethod
    def _finish_data():
        return StreamData(
            code=StreamCode.FINISH.value,
            msg="ok",
            data={"answer": {"answer": "x"}},
            execution_id="e",
        )

    @staticmethod
    def _node_types_of(formatter, stream_data):
        events = formatter.format(stream_data)
        types = set()
        for ev in events:
            data = ev.get("data") or {}
            if isinstance(data, dict) and data.get("node_type"):
                types.add(data["node_type"])
        return types

    def test_plugin_node_type_is_display_value(self):
        formatter = self._make_formatter("jiuwen.plugin")
        types = self._node_types_of(formatter, self._finish_data())
        assert "Plugin" in types
        assert "jiuwen.plugin" not in types

    def test_custom_plugin_ir_type_also_mapped(self):
        """自定义插件传入 IR 类型（jiuwen.plugin）：单组件调试统一映射为 Plugin"""
        formatter = self._make_formatter("jiuwen.plugin")
        types = self._node_types_of(formatter, self._finish_data())
        assert "Plugin" in types
        assert "jiuwen.plugin" not in types

    def test_llm_node_type_is_display_value(self):
        formatter = self._make_formatter("jiuwen.llm")
        types = self._node_types_of(formatter, self._finish_data())
        assert "LLM" in types
        assert "jiuwen.llm" not in types

    def test_unknown_type_fallback_to_raw(self):
        formatter = self._make_formatter("some.unknown")
        types = self._node_types_of(formatter, self._finish_data())
        assert "some.unknown" in types

    def test_component_type_field_unchanged(self):
        formatter = self._make_formatter("jiuwen.plugin")
        events = formatter.format(self._finish_data())
        comp_types = {
            ev.get("data", {}).get("componentType")
            for ev in events
            if ev.get("data", {}).get("componentType")
        }
        assert comp_types == {"Plugin"}