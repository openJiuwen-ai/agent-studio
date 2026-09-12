# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Start 节点 _request 入参合并优先级测试。

背景(2026-09-10 bug 修复):页面试运行传入的Start节点业务参数,经 globalVariables
进入 session 的 _request,但 Start 直接输入(openjiuwen schema 解析)为 None。
原 _fill_default_values 先用默认值覆盖 None,导致 _assemble_output 的 _request
兜底无法再覆盖,真实入参被默认值遮蔽。

修复新增 _merge_request_inputs:在默认值填充之前,把 _request 中 Start 已声明
字段的非 None 值合并进直接输入。本文件锁定合并后的优先级:

    直接输入有效值 > _request 同名非 None 值 > Start 配置默认值
"""
# pylint: disable=protected-access

from unittest.mock import MagicMock

import pytest

from jiuwen.extension.workflow_node import start as start_module
from jiuwen.extension.workflow_node.start import Start
from jiuwen.orchestration.flow.constant import REQUEST_VARIABLES


def _make_start(declared_ids, defaults=None):
    """构造 Start,声明给定 userFields.inputs 字段及默认值。"""
    defaults = defaults or {}
    inputs = [
        {"id": fid, "type": "string", "required": False, "default_value": defaults.get(fid, "")}
        for fid in declared_ids
    ]
    conf = {
        "userFields": {"inputs": inputs, "outputs": []},
        "systemFields": {"inputs": [], "outputs": []},
    }
    return Start(conf)


def _patch_request(monkeypatch, request_dict):
    """patch start.get_workflow_param,使 REQUEST_VARIABLES 返回指定 _request。"""
    def fake_get_workflow_param(session, key, default=None):
        if key == REQUEST_VARIABLES:
            return request_dict
        return default
    monkeypatch.setattr(start_module, "get_workflow_param", fake_get_workflow_param)


def _session(nesting_depth=0):
    """构造 mock session,默认模拟根工作流(depth==0)。

    _is_root_workflow 读 session._inner.workflow_nesting_depth()。
    默认 0 = 根工作流(前置 _request 合并生效);>0 = 子工作流(跳过合并)。
    """
    session = MagicMock()
    session._inner.workflow_nesting_depth.return_value = nesting_depth
    return session


class TestMergeRequestInputsPrecedence:
    """_merge_request_inputs — 优先级与边界。"""

    @staticmethod
    def test_direct_none_request_has_value_default_exists_uses_request(monkeypatch):
        """§9.1-1:顶层 None + _request 有值 + 有默认 → 取 _request。"""
        _patch_request(monkeypatch, {"input": "studio"})
        start = _make_start(["input"], defaults={"input": "主工作流默认值"})
        merged = start._merge_request_inputs({"input": None}, _session())
        assert merged["input"] == "studio"

    @staticmethod
    def test_direct_absent_request_has_value_uses_request(monkeypatch):
        """§9.1-2:顶层字段缺失 + _request 有值 → 取 _request。"""
        _patch_request(monkeypatch, {"input": "studio"})
        start = _make_start(["input"], defaults={"input": "default"})
        merged = start._merge_request_inputs({}, _session())
        assert merged["input"] == "studio"

    @staticmethod
    def test_direct_value_not_overridden_by_request(monkeypatch):
        """§9.1-3:顶层有值 + _request 也有值 → 取顶层。"""
        _patch_request(monkeypatch, {"input": "request-value"})
        start = _make_start(["input"], defaults={"input": "default"})
        merged = start._merge_request_inputs({"input": "direct-value"}, _session())
        assert merged["input"] == "direct-value"

    @staticmethod
    def test_neither_direct_nor_request_keeps_absent(monkeypatch):
        """§9.1-4:顶层和 _request 都无值 → merge 不引入该字段(留给默认值填充)。"""
        _patch_request(monkeypatch, {})
        start = _make_start(["input"], defaults={"input": "default"})
        merged = start._merge_request_inputs({"input": None}, _session())
        assert merged["input"] is None

    @staticmethod
    def test_request_none_does_not_override(monkeypatch):
        """§9.1-5:_request 值为 None → 不覆盖顶层 None(留给默认值填充)。"""
        _patch_request(monkeypatch, {"input": None})
        start = _make_start(["input"], defaults={"input": "default"})
        merged = start._merge_request_inputs({"input": None}, _session())
        assert merged["input"] is None

    @pytest.mark.parametrize(
        "value",
        [False, 0, [], {}],
        ids=["false", "zero", "empty_list", "empty_dict"],
    )
    @staticmethod
    def test_falsy_request_values_preserved(monkeypatch, value):
        """§9.1-6:_request 值为 False/0/[]/{} → 保留实际值(不用真值判断)。"""
        _patch_request(monkeypatch, {"flag": value})
        start = _make_start(["flag"], defaults={"flag": "default"})
        merged = start._merge_request_inputs({"flag": None}, _session())
        assert merged["flag"] == value

    @staticmethod
    def test_undeclared_request_field_not_merged(monkeypatch):
        """§9.1-7:_request 中 Start 未声明字段 → 不进入 merged_inputs。"""
        _patch_request(monkeypatch, {"input": "studio", "undeclared": "leak"})
        start = _make_start(["input"], defaults={"input": "default"})
        merged = start._merge_request_inputs({"input": None}, _session())
        assert "undeclared" not in merged
        assert merged["input"] == "studio"

    @staticmethod
    def test_multiple_fields_resolve_independently(monkeypatch):
        """§9.1-8:多字段分别按优先级处理。"""
        _patch_request(monkeypatch, {
            "a": "req-a",   # 顶层 None → 取 _request
            "b": "req-b",   # 顶层有值 → 保留顶层
            # c: _request 无 → 保留顶层 None(留给默认)
            "d": None,      # _request None → 不覆盖(留给默认)
        })
        start = _make_start(
            ["a", "b", "c", "d"],
            defaults={"a": "da", "b": "db", "c": "dc", "d": "dd"},
        )
        merged = start._merge_request_inputs(
            {"a": None, "b": "top-b", "c": None, "d": None}, _session()
        )
        assert merged["a"] == "req-a"
        assert merged["b"] == "top-b"
        assert merged["c"] is None
        assert merged["d"] is None

    @staticmethod
    def test_no_declared_fields_passes_through(monkeypatch):
        """§9.1-10:无声明字段的 Start,merge 不引入任何 _request 字段。"""
        _patch_request(monkeypatch, {"input": "studio", "other": "x"})
        start = _make_start([], defaults={})
        merged = start._merge_request_inputs({"query": "hi"}, _session())
        assert "input" not in merged
        assert "other" not in merged
        assert merged["query"] == "hi"


class TestMergeRequestInputsScope:
    """_merge_request_inputs — 仅根工作流(depth==0)合并,子工作流跳过。"""

    @staticmethod
    def test_child_workflow_skips_merge(monkeypatch):
        """§6.2-2:depth=1,直接 None + _request 同名值 → 不合并,保留 None。"""
        _patch_request(monkeypatch, {"input": "parent-value"})
        start = _make_start(["input"], defaults={"input": "child-default"})
        merged = start._merge_request_inputs({"input": None}, _session(nesting_depth=1))
        assert merged["input"] is None

    @staticmethod
    def test_child_workflow_mapped_value_preserved(monkeypatch):
        """§6.2-3:depth=1,已映射非 None 值 → 原值不变(不走 _request)。"""
        _patch_request(monkeypatch, {"input": "parent-value"})
        start = _make_start(["input"], defaults={"input": "child-default"})
        merged = start._merge_request_inputs({"input": "mapped"}, _session(nesting_depth=1))
        assert merged["input"] == "mapped"

    @staticmethod
    def test_root_workflow_depth_zero_merges(monkeypatch):
        """§6.2-1:depth=0,直接 None + _request 有值 → 合并 _request 值。"""
        _patch_request(monkeypatch, {"input": "studio"})
        start = _make_start(["input"], defaults={"input": "root-default"})
        merged = start._merge_request_inputs({"input": None}, _session(nesting_depth=0))
        assert merged["input"] == "studio"


class TestIsRootWorkflow:
    """_is_root_workflow — 保守判定,无法确定时返回 False(不合并)。"""

    @staticmethod
    def test_depth_zero_is_root():
        assert Start._is_root_workflow(_session(nesting_depth=0)) is True

    @staticmethod
    def test_depth_one_not_root():
        assert Start._is_root_workflow(_session(nesting_depth=1)) is False

    @staticmethod
    def test_no_inner_attr_not_root():
        session = MagicMock()
        del session._inner  # 无 _inner 属性
        assert Start._is_root_workflow(session) is False

    @staticmethod
    def test_no_depth_getter_not_root():
        """inner 存在但无 workflow_nesting_depth 方法 → False。"""
        session = MagicMock()
        inner = MagicMock()
        del inner.workflow_nesting_depth
        session._inner = inner
        assert Start._is_root_workflow(session) is False

    @staticmethod
    def test_depth_getter_raises_not_root():
        """workflow_nesting_depth() 抛异常 → 保守 False(broad except)。"""
        session = MagicMock()
        session._inner.workflow_nesting_depth.side_effect = ValueError("bad depth")
        assert Start._is_root_workflow(session) is False

    @staticmethod
    def test_depth_returning_false_not_root():
        """False == 0 在 Python 为 True,必须用 type 严格判定,避免误判为根。"""
        session = MagicMock()
        session._inner.workflow_nesting_depth.return_value = False
        assert Start._is_root_workflow(session) is False

    @staticmethod
    def test_depth_returning_none_not_root():
        session = MagicMock()
        session._inner.workflow_nesting_depth.return_value = None
        assert Start._is_root_workflow(session) is False

    @staticmethod
    def test_depth_returning_string_zero_not_root():
        """"0" 字符串虽 == 0,但非 int,不应判为根。"""
        session = MagicMock()
        session._inner.workflow_nesting_depth.return_value = "0"
        assert Start._is_root_workflow(session) is False


class TestMergeRequestFullResolution:
    """组合 _merge_request_inputs → _fill_default_values 的最终值解析。"""

    @staticmethod
    def test_child_unmapped_resolves_to_child_default(monkeypatch):
        """§7.2:子工作流未映射 → merge 保留 None → fill_default 填子默认。"""
        _patch_request(monkeypatch, {"input": "parent-value"})
        start = _make_start(["input"], defaults={"input": "child-default"})
        merged = start._merge_request_inputs({"input": None}, _session(nesting_depth=1))
        resolved = start._fill_default_values(merged)
        assert resolved["input"] == "child-default"

    @staticmethod
    def test_child_field_absent_resolves_to_child_default(monkeypatch):
        """§7.2:子工作流字段顶层不存在(非 None)→ 仍填子默认。"""
        _patch_request(monkeypatch, {"input": "parent-value"})
        start = _make_start(["input"], defaults={"input": "child-default"})
        merged = start._merge_request_inputs({}, _session(nesting_depth=1))
        resolved = start._fill_default_values(merged)
        assert resolved["input"] == "child-default"

    @staticmethod
    def test_root_request_value_survives_default_fill(monkeypatch):
        """根工作流:_request 值合并后不被默认值覆盖。"""
        _patch_request(monkeypatch, {"input": "studio"})
        start = _make_start(["input"], defaults={"input": "root-default"})
        merged = start._merge_request_inputs({"input": None}, _session(nesting_depth=0))
        resolved = start._fill_default_values(merged)
        assert resolved["input"] == "studio"

    @staticmethod
    def test_root_no_request_fills_default(monkeypatch):
        """根工作流:_request 无值 → 默认值生效。"""
        _patch_request(monkeypatch, {})
        start = _make_start(["input"], defaults={"input": "root-default"})
        merged = start._merge_request_inputs({"input": None}, _session(nesting_depth=0))
        resolved = start._fill_default_values(merged)
        assert resolved["input"] == "root-default"

    @staticmethod
    def test_reuse_workflow_standalone_trial_uses_request(monkeypatch):
        """§7.3:可复用工作流单独试运行(depth=0)→ 真实请求值优先于默认值。"""
        _patch_request(monkeypatch, {"input": "trial-value"})
        start = _make_start(["input"], defaults={"input": "reuse-default"})
        merged = start._merge_request_inputs({"input": None}, _session(nesting_depth=0))
        resolved = start._fill_default_values(merged)
        assert resolved["input"] == "trial-value"
