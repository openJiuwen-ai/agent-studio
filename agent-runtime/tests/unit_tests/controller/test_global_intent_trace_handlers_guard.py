# -*- coding: UTF-8 -*-
# pylint: disable=protected-access  # 单元测试需直接验证 _get_handle_global_intent_workflow 的防御取出行为（公共入口在意图检测 try 深处，桩面过大）
"""create_global_intent_task_by_interrupt_message 的 runtime_data 防御单测。

覆盖检视意见（197604081）：中断消息 runtime_data 为 None / 非 dict / 缺失时，
trace_handlers 取 None，意图任务创建不受遥测数据影响——不因裸调
msg.runtime_data.get 抛 AttributeError 被外层 except 吞掉后静默丢任务。
"""
import json
from types import SimpleNamespace

from jiuwen.controller.task_planner.rule_modules.rule_module import RuleModule


class _IntentConfig:
    def __init__(self, intent_id):
        self.intent_id = intent_id


def _make_module():
    """绕过 __init__ 构造最小 RuleModule（本测试只关心单方法行为）。"""
    module = object.__new__(RuleModule)
    module.controller_config = SimpleNamespace(
        global_intents=[_IntentConfig("gi-1")]
    )
    return module


def _make_msg(runtime_data="__unset__"):
    kwargs = {}
    if runtime_data != "__unset__":
        kwargs["runtime_data"] = runtime_data
    return SimpleNamespace(
        task_id="t-1",
        content=json.dumps({"intent": {"intent_id": "gi-1"}}),
        **kwargs,
    )


def _capture_call(module, monkeypatch):
    captured = {}

    def _fake_create(global_intent, task_id, trace_handlers=None):
        captured["args"] = (global_intent, task_id, trace_handlers)
        return "TASK"

    monkeypatch.setattr(module, "create_global_intent_task", _fake_create)
    return captured


def test_none_runtime_data_still_creates_intent_task(monkeypatch):
    module = _make_module()
    captured = _capture_call(module, monkeypatch)
    ret = module.create_global_intent_task_by_interrupt_message(_make_msg(None))
    assert ret == "TASK"
    assert captured["args"][2] is None


def test_non_dict_runtime_data_still_creates_intent_task(monkeypatch):
    module = _make_module()
    captured = _capture_call(module, monkeypatch)
    ret = module.create_global_intent_task_by_interrupt_message(
        _make_msg("garbage")
    )
    assert ret == "TASK"
    assert captured["args"][2] is None


def test_missing_runtime_data_attr_still_creates_intent_task(monkeypatch):
    module = _make_module()
    captured = _capture_call(module, monkeypatch)
    ret = module.create_global_intent_task_by_interrupt_message(_make_msg())
    assert ret == "TASK"
    assert captured["args"][2] is None


def test_dict_runtime_data_passes_handlers(monkeypatch):
    module = _make_module()
    captured = _capture_call(module, monkeypatch)
    handlers = ["h1"]
    ret = module.create_global_intent_task_by_interrupt_message(
        _make_msg({"trace_handlers": handlers})
    )
    assert ret == "TASK"
    assert captured["args"][2] is handlers


class _PlannerIntent:
    def __init__(self):
        self.name = "gi-name"
        self.handler_type = "workflow"


def _make_planner():
    """绕过 __init__ 构造最小 ControllerPlanner（只关心单方法行为）。"""
    from jiuwen.controller.task_planner.planners.controller_planner import (
        ControllerPlanner,
    )

    planner = object.__new__(ControllerPlanner)
    planner.plan_config = SimpleNamespace(global_intents=[_PlannerIntent()])
    return planner


def _planner_capture_call(planner, monkeypatch):
    captured = {}

    def _fake_rule_module_call(global_intent, task_id, trace_handlers=None):
        captured["args"] = (global_intent, task_id, trace_handlers)
        return "TASK"

    planner.rule_module = SimpleNamespace(
        create_global_intent_task=_fake_rule_module_call
    )
    return captured


def test_planner_none_runtime_data_still_creates_intent_task(monkeypatch):
    """controller_planner 侧同口径：runtime_data 为 None 不炸、任务照常创建。"""
    planner = _make_planner()
    captured = _planner_capture_call(planner, monkeypatch)
    msg = SimpleNamespace(
        task_id="t-9", runtime_data=None,
    )
    ret = planner._get_handle_global_intent_workflow("gi-name", msg)
    assert ret == "TASK"
    assert captured["args"][2] is None


def test_planner_dict_runtime_data_passes_handlers(monkeypatch):
    planner = _make_planner()
    captured = _planner_capture_call(planner, monkeypatch)
    handlers = ["h2"]
    msg = SimpleNamespace(
        task_id="t-9", runtime_data={"trace_handlers": handlers},
    )
    ret = planner._get_handle_global_intent_workflow("gi-name", msg)
    assert ret == "TASK"
    assert captured["args"][2] is handlers
