# coding: utf-8
# pylint: disable=protected-access
"""PlanExecuteMode._create_plugin_task 的 trace_handlers 透传测试。

规划模式工具调用此前无 execute_tool span 的根因：插件任务的 runtime_data
只带 plugins，PluginHandler 经 **runtime_data 把 kwargs 传入 plugin.ainvoke，
各工具包装器（RestfulApiToolNew / MCP / CustomPluginTool）内部 TraceManager
依赖其中的 trace_handlers 键发射 on_plugin_start/end。本测试钉住该键的存在
与来源（StreamRequest 保存的 self._trace_handlers）。
"""

from types import SimpleNamespace

from jiuwen.controller.agent.control_mode.plan_execute_mode import PlanExecuteMode


def _make_mode(trace_handlers):
    """绕过重初始化链，仅装配 _create_plugin_task 触碰的状态。"""
    mode = PlanExecuteMode.__new__(PlanExecuteMode)
    mode.task_id = "task-1"
    if trace_handlers is not None:
        mode._trace_handlers = trace_handlers
    return mode


def test_plugin_task_runtime_data_carries_trace_handlers():
    """有 trace_handlers 时进入任务 runtime_data，随执行链传入 ainvoke。"""
    handlers = [SimpleNamespace(name="otel_handler")]
    mode = _make_mode(handlers)

    plugin = SimpleNamespace(name="weather_query")
    task = mode._create_plugin_task(plugin, {"city": "北京"}, "call-1")

    runtime_data = task.input_data["runtime_data"]
    assert runtime_data["trace_handlers"] is handlers
    assert runtime_data["plugins"] == [plugin]
    assert task.input_data["plugin"] is plugin


def test_plugin_task_runtime_data_defaults_to_none():
    """_trace_handlers 未设置（如非遥测链路）时透传 None，不抛错。"""
    mode = _make_mode(trace_handlers=None)

    plugin = SimpleNamespace(name="weather_query")
    task = mode._create_plugin_task(plugin, {}, "call-2")

    assert task.input_data["runtime_data"]["trace_handlers"] is None
