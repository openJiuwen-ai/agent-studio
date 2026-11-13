# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access

"""插件/MCP 参数松校验开关（PLUGIN_MCP_LOOSE_PARAM_VALIDATION）单元测试。

覆盖四层：
1. 开关解析（默认关 / true 变体 / 非 true 值）
2. 新引擎 FlowApi._format_api_inputs（未知参数默认抛错；松校验跳过且打
   WARNING——带参数名，迁移期可据此收集清理清单）
3. 新引擎 FlowMcp._format_api_inputs（同上）
4. 旧引擎（orchestration）FlowApi / FlowMcp 的同款行为

说明：FlowCustomApi（callMode=custom）落点未包含在本分支——该组件及其
依赖 custom_plugin_tool 为 dev 线特性，hotfix/v0.2.1 线不存在；上游
!2577 的对应落点随 dev 线合入自然生效。

protected 访问说明：单测直测 _format_api_inputs/直塞 _api/_client 是
本目录既有惯例（见 test_flow_mcp_format_inputs.py），文件头 pylint 禁用
protected-access。
"""

import asyncio
import logging
from types import SimpleNamespace

import pytest

from jiuwen.common.exception import JiuWenBaseException as CommonJiuWenBaseException
from jiuwen.extension.workflow_node.flow_api import FlowApi, FlowApiStatusCode
from jiuwen.extension.workflow_node.flow_mcp import FlowMcp
from jiuwen.extension.workflow_node.utils import JiuWenBaseException
from jiuwen.orchestration.flow.components.flow_api import FlowApi as OldFlowApi
from jiuwen.orchestration.flow.components.flow_mcp import FlowMcp as OldFlowMcp
from jiuwen.plugin.models.api_utils import is_loose_param_validation_enabled
from jiuwen.plugin.models.param import Param

ENV_KEY = "PLUGIN_MCP_LOOSE_PARAM_VALIDATION"


def _make_param(name="query", param_type="string", required=True):
    return Param(name, f"param {name}", param_type=param_type, required=required)


def _mock_workflow_logger(records):
    """构造捕获 warning/error 的 workflow_logger 替身（monkeypatch 模块级名字用）"""
    return SimpleNamespace(
        warning=lambda msg, *a, **kw: records.append(("WARNING", msg, kw)),
        error=lambda msg, *a, **kw: records.append(("ERROR", msg, kw)),
    )


# ─── 1. 开关解析 ───────────────────────────────────────────────────────


class TestLooseFlagParsing:

    @staticmethod
    def test_unset_defaults_off(monkeypatch):
        monkeypatch.delenv(ENV_KEY, raising=False)
        assert is_loose_param_validation_enabled() is False

    @staticmethod
    @pytest.mark.parametrize("value", ["false", "False", "FALSE", "0", "yes", "garbage", ""])
    def test_non_true_values_off(monkeypatch, value):
        monkeypatch.setenv(ENV_KEY, value)
        assert is_loose_param_validation_enabled() is False

    @staticmethod
    @pytest.mark.parametrize("value", ["true", "TRUE", "True", " true ", "\ttrue\n"])
    def test_true_variants_on(monkeypatch, value):
        monkeypatch.setenv(ENV_KEY, value)
        assert is_loose_param_validation_enabled() is True


# ─── 2. 新引擎 FlowApi ─────────────────────────────────────────────────


def _make_flow_api():
    comp = FlowApi()
    comp._api = SimpleNamespace(params=[_make_param()])
    return comp


class TestFlowApiLooseValidation:

    @staticmethod
    def test_unknown_param_raises_by_default(monkeypatch):
        monkeypatch.delenv(ENV_KEY, raising=False)
        comp = _make_flow_api()
        with pytest.raises(JiuWenBaseException) as ei:
            asyncio.run(comp._format_api_inputs({"query": "a", "extra": "b"}))
        assert ei.value.error_code == FlowApiStatusCode.WORKFLOW_API_INPUTS_ERROR.value[0]

    @staticmethod
    def test_loose_on_skips_and_logs_warning_with_param_name(monkeypatch):
        monkeypatch.setenv(ENV_KEY, "true")
        records = []
        monkeypatch.setattr(
            "jiuwen.extension.workflow_node.flow_api.workflow_logger",
            _mock_workflow_logger(records),
        )
        comp = _make_flow_api()
        result = asyncio.run(comp._format_api_inputs({"query": "a", "extra": "b"}))
        assert result == {"query": "a"}
        # 松校验跳过必须打 WARNING（非静默、非 ERROR），且带被跳过的参数名
        warnings = [r for r in records if r[0] == "WARNING"]
        errors = [r for r in records if r[0] == "ERROR"]
        assert len(warnings) == 1
        assert "skip undefined param" in warnings[0][1]
        assert warnings[0][2]["metadata"]["param_name"] == "extra"
        assert errors == []
        # 评审修订 2026-11-04（PR#2577）：松校验跳过的 WARNING 不带 event_type
        # ——防按 event_type 聚合的日志/告警把迁移期兼容性跳过计入组件错误指标
        assert "event_type" not in warnings[0][2]

    @staticmethod
    def test_none_valued_extra_param_always_skipped_without_log(monkeypatch):
        # None 值多余参数在两种模式下都静默丢弃（先于名字检查，与开关无关）
        monkeypatch.delenv(ENV_KEY, raising=False)
        comp = _make_flow_api()
        result = asyncio.run(comp._format_api_inputs({"query": "a", "extra": None}))
        assert result == {"query": "a"}

    @staticmethod
    def test_known_params_transformed_regardless_of_flag(monkeypatch):
        monkeypatch.setenv(ENV_KEY, "true")
        comp = _make_flow_api()
        result = asyncio.run(comp._format_api_inputs({"query": 123}))
        assert result == {"query": "123"}


# ─── 3. 新引擎 FlowMcp ─────────────────────────────────────────────────


def _make_flow_mcp():
    comp = FlowMcp.__new__(FlowMcp)
    comp._client = SimpleNamespace(_tool_params=[_make_param()])
    return comp


class TestFlowMcpLooseValidation:

    @staticmethod
    def test_unknown_param_raises_by_default(monkeypatch):
        monkeypatch.delenv(ENV_KEY, raising=False)
        comp = _make_flow_mcp()
        with pytest.raises(JiuWenBaseException):
            comp._format_api_inputs({"query": "a", "extra": "b"})

    @staticmethod
    def test_loose_on_skips_and_logs_warning_with_param_name(monkeypatch):
        monkeypatch.setenv(ENV_KEY, "true")
        records = []
        monkeypatch.setattr(
            "jiuwen.extension.workflow_node.flow_mcp.workflow_logger",
            _mock_workflow_logger(records),
        )
        comp = _make_flow_mcp()
        # hotfix 线 FlowMcp._format_api_inputs 返回 3 元组
        # (api_inputs, schema_patches, header_params)——dev 线为 2 元组，
        # 本分支按 hotfix 签名解包
        api_inputs, schema_patches, _header_params = comp._format_api_inputs(
            {"query": "a", "extra": "b"}
        )
        assert api_inputs == {"query": "a"}
        assert schema_patches == {}
        warnings = [r for r in records if r[0] == "WARNING"]
        errors = [r for r in records if r[0] == "ERROR"]
        assert len(warnings) == 1
        assert "skip undefined param" in warnings[0][1]
        assert warnings[0][2]["metadata"]["param_name"] == "extra"
        assert errors == []
        # 评审修订 2026-11-04（PR#2577）：松校验跳过的 WARNING 不带 event_type
        # ——防按 event_type 聚合的日志/告警把迁移期兼容性跳过计入组件错误指标
        assert "event_type" not in warnings[0][2]


# ─── 4. 旧引擎（orchestration） ────────────────────────────────────────


def _make_old_flow_api():
    comp = OldFlowApi.__new__(OldFlowApi)
    comp._api = SimpleNamespace(params=[_make_param()])
    return comp


def _make_old_flow_mcp():
    comp = OldFlowMcp.__new__(OldFlowMcp)
    comp.api = SimpleNamespace(params=[_make_param()])
    return comp


class TestOldEngineLooseValidation:

    @staticmethod
    def test_old_flow_api_unknown_param_raises_by_default(monkeypatch):
        monkeypatch.delenv(ENV_KEY, raising=False)
        comp = _make_old_flow_api()
        with pytest.raises(CommonJiuWenBaseException):
            comp._format_api_inputs({"query": "a", "extra": "b"})

    @staticmethod
    def test_old_flow_api_loose_on_skips_and_logs_warning(monkeypatch, caplog):
        monkeypatch.setenv(ENV_KEY, "true")
        comp = _make_old_flow_api()
        with caplog.at_level(logging.WARNING):
            result = comp._format_api_inputs({"query": "a", "extra": "b"})
        assert result == {"query": "a"}
        skip_warnings = [
            r for r in caplog.records if "loose param validation" in r.getMessage()
        ]
        assert len(skip_warnings) == 1
        assert "extra" in skip_warnings[0].getMessage()
        # 松校验跳过不是错误——不应出现 error 级日志
        assert not [
            r for r in caplog.records if r.levelno >= logging.ERROR
        ]

    @staticmethod
    def test_old_flow_mcp_unknown_param_raises_by_default(monkeypatch):
        monkeypatch.delenv(ENV_KEY, raising=False)
        comp = _make_old_flow_mcp()
        with pytest.raises(CommonJiuWenBaseException):
            comp._format_api_inputs({"query": "a", "extra": "b"})

    @staticmethod
    def test_old_flow_mcp_loose_on_skips_and_logs_warning(monkeypatch, caplog):
        monkeypatch.setenv(ENV_KEY, "true")
        comp = _make_old_flow_mcp()
        with caplog.at_level(logging.WARNING):
            result = comp._format_api_inputs({"query": "a", "extra": "b"})
        assert result == {"query": "a"}
        skip_warnings = [
            r for r in caplog.records if "loose param validation" in r.getMessage()
        ]
        assert len(skip_warnings) == 1
        assert "extra" in skip_warnings[0].getMessage()
        assert not [
            r for r in caplog.records if r.levelno >= logging.ERROR
        ]
