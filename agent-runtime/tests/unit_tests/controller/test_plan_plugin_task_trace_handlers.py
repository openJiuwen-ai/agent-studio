# coding: utf-8
# pylint: disable=protected-access
"""PlanExecuteMode._create_plugin_task 的 trace_handlers 透传测试。

规划模式工具调用此前无 execute_tool span 的根因：插件任务的 runtime_data
只带 plugins，PluginHandler 经 **runtime_data 把 kwargs 传入 plugin.ainvoke，
各工具包装器（RestfulApiToolNew / MCP / CustomPluginTool）内部 TraceManager
依赖其中的 trace_handlers 键发射 on_plugin_start/end。本测试钉住该键的存在
与来源（StreamRequest 保存的 self._trace_handlers）。
"""

import asyncio
from types import SimpleNamespace

from jiuwen.controller.agent.control_mode.plan_execute_mode import PlanExecuteMode
from jiuwen.orchestration.flow.stream.base import StreamCode


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


def _drive_first_outcome(agen):
    """推进 stream 至首个产出；缺桩态由兜底 except 转为 ERROR 产出。

    stream 主体整体处于 try/except 兜底内，规划段缺桩失败不会向外抛，
    而是产出一条 ERROR StreamData；本辅助只负责推进到该产出。若入口段
    本身缺陷导致向外抛错，返回 None 交由调用方断言暴露。
    """
    try:
        return asyncio.run(asyncio.wait_for(anext(agen), timeout=5))
    except Exception:
        return None


def test_stream_entry_seeds_trace_handlers_from_stream_request():
    """钉真实来源：stream 入口把 trace_handlers 存到 self._trace_handlers。

    透传用例（_make_mode 手工注入）只钉 runtime_data 形态；本用例驱动真实
    stream 入口段（属性就地初始化 + StreamRequest 构造 + 上下文保存），
    断言赋值发生在任何规划逻辑之前。缺桩态下规划段失败由 stream 兜底
    except 接管并转 ERROR StreamData 产出——入口段已完成的证据。
    """
    handlers = [SimpleNamespace(name="otel_handler")]
    mode = PlanExecuteMode.__new__(PlanExecuteMode)
    mode.task_id = "task-1"  # 兜底 except 的日志与 StreamData 构造会读取

    agen = mode.stream(query="你好", trace_handlers=handlers)
    first = _drive_first_outcome(agen)

    assert mode._trace_handlers is handlers, "stream 入口必须真实赋值 trace_handlers"
    assert first is not None, "缺桩态兜底应产出 ERROR StreamData 而非向外抛错"
    assert first.code == StreamCode.ERROR.value, "兜底产出应为 ERROR 形态"
