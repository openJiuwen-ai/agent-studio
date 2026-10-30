"""chunk_wrapper（完整工作流调用详情链）组件类型归一审验。"""

from agent_runtime.runner.chunk_wrapper import _normalize_component_display_type


class TestChunkNormalizeComponentDisplayType:
    def test_custom_plugin_maps_to_api(self):
        """自定义插件组件类型（custom.draw_box 等）→ Api"""
        assert _normalize_component_display_type("custom.draw_box") == "Api"

    def test_flow_custom_api_maps_to_api(self):
        """自定义插件执行器组件名 FlowCustomApi → Api"""
        assert _normalize_component_display_type("FlowCustomApi") == "Api"

    def test_ir_plugin_type_maps_to_api(self):
        """IR 插件类型 jiuwen.plugin → Api"""
        assert _normalize_component_display_type("jiuwen.plugin") == "Api"

    def test_unknown_type_fallback_to_raw(self):
        """未知类型保持原值"""
        assert _normalize_component_display_type("some.unknown") == "some.unknown"

    def test_empty_type_unchanged(self):
        assert _normalize_component_display_type("") == ""