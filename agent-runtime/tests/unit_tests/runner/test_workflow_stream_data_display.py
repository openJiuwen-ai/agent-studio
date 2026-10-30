"""
完整工作流调用详情链（workflow_stream_data_wrapper）组件类型归一校验。

覆盖：payload.componentType 在下发 manager 前统一归一——
自定义插件组件类型（custom.*）与 IR 类型（jiuwen.plugin）映射为 Api，
使 manager NodeType.fromInsight 命中 PLUGIN（调用详情展示 Plugin 而非 Unknown）。
"""

from agent_runtime.runner.workflow_stream_data_wrapper import (
    _DEBUG_EVENT_RETURN_TO_SERVICE,
    _normalize_component_display_type,
)


class TestNormalizeComponentDisplayType:
    def test_custom_plugin_maps_to_api(self):
        """自定义插件组件类型（custom.draw_box 等）→ Api"""
        assert _normalize_component_display_type("custom.draw_box") == "Api"
        assert _normalize_component_display_type("custom.tag") == "Api"

    def test_flow_custom_api_maps_to_api(self):
        """自定义插件执行器组件名 FlowCustomApi → Api"""
        assert _normalize_component_display_type("FlowCustomApi") == "Api"

    def test_ir_plugin_type_maps_to_api(self):
        """IR 插件类型 jiuwen.plugin → Api"""
        assert _normalize_component_display_type("jiuwen.plugin") == "Api"

    def test_known_component_maps_by_table(self):
        """映射表内既有类型维持原映射"""
        assert _normalize_component_display_type("FlowApi") == "Api"
        assert _normalize_component_display_type("FlowCode") == "Code"

    def test_unknown_type_fallback_to_raw(self):
        """未知类型保持原值（不引入新映射）"""
        assert _normalize_component_display_type("some.unknown") == "some.unknown"

    def test_empty_type_unchanged(self):
        assert _normalize_component_display_type("") == ""

    def test_jiuwen_plugin_in_map(self):
        """映射表副本需含 jiuwen.plugin → Api（与 workflow_wrapper 对齐）"""
        assert _DEBUG_EVENT_RETURN_TO_SERVICE.get("jiuwen.plugin") == "Api"