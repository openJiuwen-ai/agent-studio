# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""End 节点对 None inputs / None 叶子的防护。

背景: Start→End 直连且 End 引用 memory.a[0].b 时,若 memory.a 为空默认曾被
Start 写成 None,Pregel 会把未命中下标解析成 None 传入 End;`x in None`
抛 TypeError。本文件覆盖 End 侧归一与 coalesce 兜底。
"""
# pylint: disable=protected-access

from jiuwen.extension.workflow_node.end import End


class TestEndNullInputsGuard:
    @staticmethod
    def test_normalize_inputs_dict_none_and_non_dict():
        assert End._normalize_inputs_dict(None) == {}
        assert End._normalize_inputs_dict("x") == {}
        assert End._normalize_inputs_dict({"a": 1}) == {"a": 1}

    @staticmethod
    def test_coalesce_none_leaves_replaces_none_keeps_others():
        data = {"a": None, "b": "", "c": 0, "d": False, "e": [], "f": {"x": 1}}
        End._coalesce_none_leaves(data)
        assert data == {
            "a": "",
            "b": "",
            "c": 0,
            "d": False,
            "e": [],
            "f": {"x": 1},
        }

    @staticmethod
    def test_coalesce_none_leaves_ignores_non_dict():
        End._coalesce_none_leaves(None)  # type: ignore[arg-type]
        End._coalesce_none_leaves([])  # type: ignore[arg-type]

    @staticmethod
    def test_ensure_response_dict():
        assert End._ensure_response_dict(None) == {}
        assert End._ensure_response_dict({"ok": 1}) == {"ok": 1}
        assert End._ensure_response_dict("hi") == {"response": "hi"}

    @staticmethod
    def test_extract_user_fields_handles_none_inputs():
        end = End.__new__(End)
        assert end._extract_user_fields(None) == {}
        assert end._extract_user_fields({"userFields": {"x": None}}) == {"x": None}
        assert end._extract_user_fields({"a": 1}) == {"a": 1}
        assert end._extract_user_fields({"userFields": "bad"}) == {}

    @staticmethod
    def test_has_response_payload_rejects_none_payload():
        from jiuwen.extension.workflow_node.end import _has_response_payload

        class _Out:
            def __init__(self, payload):
                self.type = "t"
                self.payload = payload

        assert _has_response_payload(_Out(None)) is False
        assert _has_response_payload(_Out({"response": "x"})) is True
        assert _has_response_payload(_Out({"other": 1})) is False
        assert _has_response_payload("plain") is False
