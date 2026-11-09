#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""FlowCode sandbox execution tests — exec_env + fallback logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agent_runtime.extension.workflow_node.flow_code import FlowCode, FlowCodeConfig
from agent_runtime.extension.workflow_node.code_runner.local_code_runner import (
    LocalCodeRunner,
)
from agent_runtime.extension.workflow_node.code_runner.sandbox_code_runner import (
    SandboxCodeRunner,
)
from agent_runtime.extension.workflow_node.code_runner.base_code_runner import (
    CodeRunResult,
)


def _mock_sys_op():
    mock_sys_op = MagicMock()
    mock_code_op = MagicMock()
    mock_sys_op.code.return_value = mock_code_op
    return mock_sys_op


def _mock_resource_mgr(local_op=None, sandbox_op=None):
    ops = {}
    if local_op:
        ops["flow_code_sys_op"] = local_op
    if sandbox_op:
        ops["flow_code_sandbox_sys_op"] = sandbox_op

    mock_mgr = MagicMock()
    mock_mgr.get_sys_operation = MagicMock(side_effect=lambda id: ops.get(id))
    return mock_mgr


def _get_code_runner(flow_code):
    return getattr(flow_code, "_code_runner")


def _set_code_runner(flow_code, runner):
    setattr(flow_code, "_code_runner", runner)


def _get_conf(flow_code):
    return getattr(flow_code, "_conf")


def _call_ensure_code_runner(flow_code):
    getattr(flow_code, "_ensure_code_runner")()


class TestFlowCodeExecEnv:
    @staticmethod
    def test_exec_env_local_creates_local_runner():
        config = FlowCodeConfig(
            code="def main(args): return {}", exec_env="local"
        )
        flow_code = FlowCode(config)

        mock_sys_op = _mock_sys_op()
        mock_mgr = _mock_resource_mgr(local_op=mock_sys_op)

        with patch("openjiuwen.core.runner.Runner.resource_mgr", mock_mgr), \
             patch("agent_runtime.common.config.settings") as mock_settings:
            mock_settings.code_execution.local_exec_mode = "subprocess"
            mock_settings.code_execution.allow_local_exec = True
            _call_ensure_code_runner(flow_code)
            assert isinstance(_get_code_runner(flow_code), LocalCodeRunner)

    @staticmethod
    def test_exec_env_sandbox_creates_sandbox_runner():
        config = FlowCodeConfig(
            code="def main(args): return {}", exec_env="sandbox"
        )
        flow_code = FlowCode(config)

        local_op = _mock_sys_op()
        sandbox_op = _mock_sys_op()
        mock_mgr = _mock_resource_mgr(local_op=local_op, sandbox_op=sandbox_op)

        with patch("openjiuwen.core.runner.Runner.resource_mgr", mock_mgr), \
             patch("agent_runtime.common.config.settings") as mock_settings:
            mock_settings.code_execution.local_exec_mode = "subprocess"
            _call_ensure_code_runner(flow_code)
            assert isinstance(_get_code_runner(flow_code), SandboxCodeRunner)

    @staticmethod
    def test_exec_env_sandbox_no_sandbox_sysop_raises():
        config = FlowCodeConfig(
            code="def main(args): return {}", exec_env="sandbox"
        )
        flow_code = FlowCode(config)

        local_op = _mock_sys_op()
        mock_mgr = _mock_resource_mgr(local_op=local_op)

        with patch("openjiuwen.core.runner.Runner.resource_mgr", mock_mgr), \
             patch("agent_runtime.common.config.settings") as mock_settings:
            mock_settings.code_execution.local_exec_mode = "subprocess"
            with pytest.raises(Exception, match="Failed to create runner.*Fallback.*disabled"):
                _call_ensure_code_runner(flow_code)

    @staticmethod
    def test_exec_env_empty_defaults_to_sandbox():
        config = FlowCodeConfig(
            code="def main(args): return {}", exec_env=""
        )
        flow_code = FlowCode(config)

        local_op = _mock_sys_op()
        sandbox_op = _mock_sys_op()
        mock_mgr = _mock_resource_mgr(local_op=local_op, sandbox_op=sandbox_op)

        with patch("openjiuwen.core.runner.Runner.resource_mgr", mock_mgr), \
             patch("agent_runtime.common.config.settings") as mock_settings:
            mock_settings.code_execution.local_exec_mode = "subprocess"
            _call_ensure_code_runner(flow_code)
            assert isinstance(_get_code_runner(flow_code), SandboxCodeRunner)

    @staticmethod
    def test_exec_env_local_no_sysop_raises():
        config = FlowCodeConfig(
            code="def main(args): return {}", exec_env="local"
        )
        flow_code = FlowCode(config)

        mock_mgr = _mock_resource_mgr()

        with patch("openjiuwen.core.runner.Runner.resource_mgr", mock_mgr), \
             patch("agent_runtime.common.config.settings") as mock_settings:
            mock_settings.code_execution.local_exec_mode = "subprocess"
            mock_settings.code_execution.allow_local_exec = True
            with pytest.raises(Exception, match="flow_code_sys_op.*not found"):
                _call_ensure_code_runner(flow_code)

    @staticmethod
    def test_dict_config_exec_env():
        flow_code = FlowCode({"code": "def main(args): return {}", "exec_env": "sandbox"})
        assert _get_conf(flow_code).exec_env == "sandbox"

    @staticmethod
    def test_dict_config_missing_exec_env_defaults_sandbox():
        flow_code = FlowCode({"code": "def main(args): return {}"})
        assert _get_conf(flow_code).exec_env == "sandbox"


class TestFlowCodeSandboxFallback:
    @staticmethod
    @pytest.mark.asyncio
    async def test_sandbox_run_success_no_fallback():
        config = FlowCodeConfig(
            code="def main(args): return {'result': 1}",
            exec_env="sandbox",
        )
        flow_code = FlowCode(config)

        mock_runner = AsyncMock()
        mock_runner.run = AsyncMock(return_value=CodeRunResult(result={"result": 1}, function_log=""))
        _set_code_runner(flow_code, mock_runner)

        mock_session = MagicMock()
        mock_session.get_component_id.return_value = "test"
        mock_session.get_session_id.return_value = "sess"
        mock_session.get_workflow_id.return_value = "wf"
        mock_session.trace = AsyncMock()
        mock_context = MagicMock()

        with patch(
            "agent_runtime.extension.workflow_node.flow_code._coerce_inputs",
            side_effect=lambda u, s: u,
        ), patch(
            "agent_runtime.extension.workflow_node.flow_code._coerce_outputs",
            side_effect=lambda r, s: r,
        ), patch.object(
            flow_code, "_check_blacklist"
        ):
            from openjiuwen.core.common.constants.constant import USER_FIELDS

            result = await flow_code.invoke(
                inputs={USER_FIELDS: {"x": 1}},
                session=mock_session,
                context=mock_context,
            )
            assert result[USER_FIELDS] == {"result": 1}
            mock_runner.run.assert_called_once()

    @staticmethod
    @pytest.mark.asyncio
    async def test_sandbox_run_failure_raises_error():
        config = FlowCodeConfig(
            code="def main(args): return {'result': 'fallback'}",
            exec_env="sandbox",
        )
        flow_code = FlowCode(config)

        mock_sandbox_runner = AsyncMock()
        mock_sandbox_runner.run = AsyncMock(side_effect=RuntimeError("sandbox down"))
        _set_code_runner(flow_code, mock_sandbox_runner)

        mock_session = MagicMock()
        mock_session.get_component_id.return_value = "test"
        mock_session.get_session_id.return_value = "sess"
        mock_session.get_workflow_id.return_value = "wf"
        mock_session.trace = AsyncMock()
        mock_context = MagicMock()

        with patch(
            "agent_runtime.extension.workflow_node.flow_code._coerce_inputs",
            side_effect=lambda u, s: u,
        ), patch(
            "agent_runtime.extension.workflow_node.flow_code._coerce_outputs",
            side_effect=lambda r, s: r,
        ), patch.object(
            flow_code, "_check_blacklist"
        ), patch(
            "agent_runtime.extension.workflow_node.flow_code.workflow_logger"
        ):
            from openjiuwen.core.common.constants.constant import USER_FIELDS

            with pytest.raises(Exception, match="Sandbox execution failed.*fallback.*disabled"):
                await flow_code.invoke(
                    inputs={USER_FIELDS: {}},
                    session=mock_session,
                    context=mock_context,
                )

    @staticmethod
    @pytest.mark.asyncio
    async def test_local_run_failure_no_fallback():
        config = FlowCodeConfig(
            code="def main(args): return {}",
            exec_env="local",
        )
        flow_code = FlowCode(config)

        mock_local_runner = AsyncMock()
        mock_local_runner.run = AsyncMock(side_effect=RuntimeError("local error"))
        _set_code_runner(flow_code, mock_local_runner)

        mock_session = MagicMock()
        mock_session.get_component_id.return_value = "test"
        mock_session.get_session_id.return_value = "sess"
        mock_session.get_workflow_id.return_value = "wf"
        mock_session.trace = AsyncMock()
        mock_context = MagicMock()

        with patch(
            "agent_runtime.extension.workflow_node.flow_code._coerce_inputs",
            side_effect=lambda u, s: u,
        ), patch(
            "agent_runtime.extension.workflow_node.flow_code._coerce_outputs",
            side_effect=lambda r, s: r,
        ), patch.object(
            flow_code, "_check_blacklist"
        ):
            with pytest.raises(Exception, match="local error"):
                await flow_code.invoke(
                    inputs={},
                    session=mock_session,
                    context=mock_context,
                )

    @staticmethod
    @pytest.mark.asyncio
    async def test_sandbox_failure_raises_build_error():
        config = FlowCodeConfig(
            code="def main(args): return {}",
            exec_env="sandbox",
        )
        flow_code = FlowCode(config)

        mock_sandbox_runner = AsyncMock()
        mock_sandbox_runner.run = AsyncMock(side_effect=RuntimeError("sandbox down"))
        _set_code_runner(flow_code, mock_sandbox_runner)

        mock_session = MagicMock()
        mock_session.get_component_id.return_value = "test"
        mock_session.get_session_id.return_value = "sess"
        mock_session.get_workflow_id.return_value = "wf"
        mock_session.trace = AsyncMock()
        mock_context = MagicMock()

        with patch(
            "agent_runtime.extension.workflow_node.flow_code._coerce_inputs",
            side_effect=lambda u, s: u,
        ), patch(
            "agent_runtime.extension.workflow_node.flow_code._coerce_outputs",
            side_effect=lambda r, s: r,
        ), patch.object(
            flow_code, "_check_blacklist"
        ):
            with pytest.raises(Exception, match="Sandbox execution failed.*fallback.*disabled"):
                await flow_code.invoke(
                    inputs={},
                    session=mock_session,
                    context=mock_context,
                )


class TestFlowCodeInprocessMode:
    """FlowCode._ensure_code_runner 在 inprocess 模式下的行为测试"""

    @staticmethod
    def test_inprocess_mode_creates_inprocess_runner():
        """LOCAL_CODE_EXEC_MODE=inprocess 时，_ensure_code_runner 创建 InprocessCodeRunner"""
        from agent_runtime.extension.workflow_node.code_runner.inprocess_code_runner import (
            InprocessCodeRunner,
        )

        config = FlowCodeConfig(
            code="def main(args): return {}", exec_env="local"
        )
        flow_code = FlowCode(config)

        with patch("agent_runtime.common.config.settings") as mock_settings:
            mock_settings.code_execution.local_exec_mode = "inprocess"
            mock_settings.code_execution.allow_local_exec = True
            _call_ensure_code_runner(flow_code)

        runner = _get_code_runner(flow_code)
        assert isinstance(runner, InprocessCodeRunner)

    @staticmethod
    def test_inprocess_mode_no_sys_operation_required():
        """inprocess 模式下，不依赖 sys_operation 也能创建 runner"""
        from agent_runtime.extension.workflow_node.code_runner.inprocess_code_runner import (
            InprocessCodeRunner,
        )

        config = FlowCodeConfig(
            code="def main(args): return {}", exec_env="local"
        )
        flow_code = FlowCode(config)

        # inprocess 模式下即使 sys_operation 未注册也不报错
        with patch("agent_runtime.common.config.settings") as mock_settings:
            mock_settings.code_execution.local_exec_mode = "inprocess"
            mock_settings.code_execution.allow_local_exec = True
            _call_ensure_code_runner(flow_code)

        runner = _get_code_runner(flow_code)
        assert isinstance(runner, InprocessCodeRunner)

    @staticmethod
    def test_subprocess_mode_requires_sys_operation():
        """LOCAL_CODE_EXEC_MODE=subprocess 时，仍需要 sys_operation"""
        config = FlowCodeConfig(
            code="def main(args): return {}", exec_env="local"
        )
        flow_code = FlowCode(config)

        # 模拟 sys_operation 未注册
        mock_mgr = _mock_resource_mgr(local_op=None)
        with patch("openjiuwen.core.runner.Runner.resource_mgr", mock_mgr), \
             patch("agent_runtime.common.config.settings") as mock_settings:
            mock_settings.code_execution.local_exec_mode = "subprocess"
            mock_settings.code_execution.allow_local_exec = True
            with pytest.raises(Exception, match="flow_code_sys_op"):
                _call_ensure_code_runner(flow_code)

    @staticmethod
    def test_local_exec_disabled_raises():
        """ALLOW_LOCAL_CODE_EXEC=false 时，local 模式拒绝执行"""
        config = FlowCodeConfig(
            code="def main(args): return {}", exec_env="local"
        )
        flow_code = FlowCode(config)

        with patch("agent_runtime.common.config.settings") as mock_settings:
            mock_settings.code_execution.local_exec_mode = "inprocess"
            mock_settings.code_execution.allow_local_exec = False
            with pytest.raises(Exception, match="Local code execution is disabled"):
                _call_ensure_code_runner(flow_code)
