"""chunk_wrapper（完整工作流调用详情链）组件类型归一审验。"""

from agent_runtime.runner.chunk_wrapper import _normalize_component_display_type


class TestChunkNormalizeComponentDisplayType:
    @staticmethod
    def _norm(raw_type: str) -> str:
        return _normalize_component_display_type(raw_type)

    def test_custom_plugin_maps_to_api(self):
        """自定义插件组件类型（custom.draw_box 等）→ Api"""
        assert self._norm("custom.draw_box") == "Api"

    def test_flow_custom_api_maps_to_api(self):
        """自定义插件执行器组件名 FlowCustomApi → Api"""
        assert self._norm("FlowCustomApi") == "Api"

    def test_flow_api_maps_to_api(self):
        """标准 HTTP 插件节点组件名 FlowApi → Api（与 workflow_stream_data_wrapper 姊妹映射表一致）"""
        assert self._norm("FlowApi") == "Api"

    def test_ir_plugin_type_maps_to_api(self):
        """IR 插件类型 jiuwen.plugin → Api"""
        assert self._norm("jiuwen.plugin") == "Api"

    def test_unknown_type_fallback_to_raw(self):
        """未知类型保持原值"""
        assert self._norm("some.unknown") == "some.unknown"

    def test_empty_type_unchanged(self):
        assert self._norm("") == ""