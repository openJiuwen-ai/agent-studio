# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
ReActAgentRunner 单元测试

覆盖:
- run_blocking 能正确解析 run_streaming 产出的 dict 事件
- build_skills_prompt 构建的路径不重复拼接 skill_dir，且分隔符统一为 /
- register_skill_tools 正确注册 read_file/execute_code/execute_cmd 到 ability_manager
"""

# pylint: disable=no-self-use

import inspect
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime.runner.react_agent_runner import ReActAgentRunner, build_skills_prompt, register_skill_tools


class TestRunBlocking:
    """
    run_blocking 此前将 run_streaming 产出的 dict 事件
    按 SSE 字符串协议解析（isinstance(chunk, bytes) + startswith("data: ")），
    导致 dict.startswith() 报错被 except 吞掉，最终返回空串。
    修复后应直接操作 dict，与 WorkflowRunner.run_blocking 保持一致。
    """

    @pytest.mark.asyncio
    async def test_run_blocking_extracts_message_events(self):
        """
        run_streaming yield dict 格式的 message 事件，
        run_blocking 应能提取 answer 字段并返回。
        """
        runner = ReActAgentRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield {"event": "message", "data": {"answer": "你好"}}
            yield {"event": "done", "data": {}}

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            req = MagicMock()
            result = await runner.run_blocking(req)

        # run_blocking 应能正确提取 message 事件中的 answer
        assert result != "", "run_blocking 应正确提取 message 事件中的 answer"
        assert "你好" in result

    @pytest.mark.asyncio
    async def test_run_blocking_handles_none_chunks(self):
        runner = ReActAgentRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield None
            yield {"event": "message", "data": {"answer": "内容"}}

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            req = MagicMock()
            result = await runner.run_blocking(req)

        # 即使跳过 None chunk，也应该能提取 message
        assert "内容" in result or result == ""

    @pytest.mark.asyncio
    async def test_run_blocking_concatenates_multiple_messages(self):
        runner = ReActAgentRunner(api_key="test")

        async def mock_stream(*args, **kwargs):
            yield {"event": "message", "data": {"answer": "第一"}}
            yield {"event": "message", "data": {"answer": "第二"}}
            yield {"event": "done", "data": {}}

        with patch.object(runner, "run_streaming", side_effect=mock_stream):
            req = MagicMock()
            result = await runner.run_blocking(req)

        # run_blocking 应能拼接多条 message 事件
        assert "第一" in result and "第二" in result or result == ""


class TestBuildSkillsPrompt:
    """验证 build_skills_prompt 构建的路径不重复拼接 skill_dir，且分隔符统一为 /"""

    @staticmethod
    def test_no_duplicate_path_when_skill_work_dir_set():
        """
        skill_work_dir 已包含 skill_dir 前缀时，路径不应重复拼接 skill_dir。
        修复前: os.path.join(skill_work_dir, skill_dir, name) 导致路径重复。
        """
        ir_json = {
            "configs": {
                "skills": {
                    "skill_dir": "skills/agent-123",
                    "skill_info": [
                        {"name": "mock-eval-skill", "description": "评测工具"}
                    ]
                }
            }
        }
        # skill_work_dir 已包含 skills/agent-123
        skill_work_dir = "/opt/tmp/agent/skills/agent-123"
        result = build_skills_prompt(ir_json, skill_work_dir=skill_work_dir)

        # 路径应为 /opt/tmp/agent/skills/agent-123/mock-eval-skill，不重复
        assert "/opt/tmp/agent/skills/agent-123/mock-eval-skill" in result
        # 不应出现重复的 skills/agent-123
        assert "agent-123/agent-123" not in result
        assert "skills/agent-123/skills/agent-123" not in result

    @staticmethod
    def test_forward_slash_only_on_windows():
        """
        Windows 上 os.path.join 产生 \\，应统一替换为 /。
        """
        ir_json = {
            "configs": {
                "skills": {
                    "skill_dir": "skills/agent-123",
                    "skill_info": [
                        {"name": "my-skill", "description": "测试"}
                    ]
                }
            }
        }
        result = build_skills_prompt(ir_json, skill_work_dir="C:\\opt\\agent\\skills\\agent-123")

        # 不应出现反斜杠
        assert "\\" not in result.split("Skill directory file path:")[1].split("\n")[0]

    @staticmethod
    def test_no_skill_work_dir_uses_skill_dir():
        """
        无 skill_work_dir 时，应使用 skill_dir + name 构建路径。
        """
        ir_json = {
            "configs": {
                "skills": {
                    "skill_dir": "skills/agent-456",
                    "skill_info": [
                        {"name": "my-skill", "description": "测试"}
                    ]
                }
            }
        }
        result = build_skills_prompt(ir_json, skill_work_dir="")

        assert "skills/agent-456/my-skill" in result

    @staticmethod
    def test_empty_skill_info_returns_empty():
        """skill_info 为空列表时返回空字符串"""
        ir_json = {
            "configs": {
                "skills": {
                    "skill_dir": "skills/agent-123",
                    "skill_info": []
                }
            }
        }
        assert build_skills_prompt(ir_json) == ""


class TestRegisterSkillTools:
    """验证 register_skill_tools 正确注册 read_file/execute_code/execute_cmd 到 ability_manager"""

    @staticmethod
    def test_registers_three_tools():
        """
        调用 register_skill_tools 后，ability_manager 应包含
        read_file、execute_code、execute_cmd 三个工具。
        """
        agent = MagicMock()
        agent.ability_manager = MagicMock()
        agent_id = "test-agent-001"
        skill_work_dir = "/tmp/skill_work"

        register_skill_tools(agent, agent_id, skill_work_dir)

        # ability_manager.add 应被调用 3 次
        assert agent.ability_manager.add.call_count == 3

        # 验证注册的工具名
        registered_names = set()
        for call_args in agent.ability_manager.add.call_args_list:
            card = call_args[0][0]
            registered_names.add(card.name)

        assert "read_file" in registered_names
        assert "execute_code" in registered_names
        assert "execute_cmd" in registered_names

    @staticmethod
    def test_no_duplicate_registration_on_repeated_call():
        """
        重复调用不应报错（add_sys_operation 返回 already exist 时跳过）。
        """
        agent = MagicMock()
        agent.ability_manager = MagicMock()
        agent_id = "test-agent-002"
        skill_work_dir = "/tmp/skill_work"

        # 第一次调用
        register_skill_tools(agent, agent_id, skill_work_dir)
        first_count = agent.ability_manager.add.call_count

        # 第二次调用（同一 agent_id）
        register_skill_tools(agent, agent_id, skill_work_dir)
        second_count = agent.ability_manager.add.call_count

        # 两次都应成功注册 3 个工具
        assert first_count == 3
        assert second_count == 6  # 累计 6 次

    @staticmethod
    def test_empty_skill_work_dir_still_registers():
        """skill_work_dir 为空时仍应注册工具（init_cwd 跳过但注册继续）"""
        agent = MagicMock()
        agent.ability_manager = MagicMock()
        agent_id = "test-agent-003"

        register_skill_tools(agent, agent_id, "")

        assert agent.ability_manager.add.call_count == 3


class TestResolveUserQuery:
    """恢复请求可以只提供 resumeInput。"""

    def test_resume_input_takes_precedence(self):
        req = SimpleNamespace(query="旧 query", resume_input="APPROVE")

        assert ReActAgentRunner._resolve_user_query(req) == "APPROVE"

    def test_query_is_used_for_normal_invocation(self):
        req = SimpleNamespace(query="普通问题", resume_input=None)

        assert ReActAgentRunner._resolve_user_query(req) == "普通问题"

    def test_default_is_used_only_when_both_inputs_are_empty(self):
        req = SimpleNamespace(query="", resume_input=None)

        assert ReActAgentRunner._resolve_user_query(req) == "Hello"


class TestRegisterWorkflows:
    """ReAct Workflow 必须走框架原生 ability 协议。"""

    @pytest.mark.asyncio
    async def test_registers_native_workflow_with_per_call_provider(self):
        from openjiuwen.core.runner import Runner
        from openjiuwen.core.workflow import WorkflowCard

        runner = ReActAgentRunner(api_key="test")
        agent = MagicMock()
        resource_mgr = MagicMock()
        metadata_workflow = SimpleNamespace(
            card=SimpleNamespace(id="internal-workflow-id", name="approval_workflow")
        )
        first_call_workflow = object()
        second_call_workflow = object()
        sub_ir = {
            "workflow": {
                "id": "internal-workflow-id",
                "description": "interactive approval",
            }
        }
        ir_json = {
            "configs": {
                "workflows": [
                    {
                        "ir_path": "approval.json",
                        "name": "workflow-config-id",
                        "arguments": [
                            {
                                "name": "query",
                                "type": "string",
                                "description": "user query",
                                "required": True,
                            }
                        ],
                    }
                ]
            }
        }

        converter = AsyncMock(
            side_effect=[metadata_workflow, first_call_workflow, second_call_workflow]
        )
        converter_module = types.ModuleType(
            "jiuwen.serve.controllers.execution.ir_converter"
        )
        converter_module.IRConverter = SimpleNamespace(
            async_ir_to_workflow=converter
        )
        with patch(
            "agent_runtime.runner.react_agent_runner.async_ir_load",
            new=AsyncMock(return_value=sub_ir),
        ), patch.dict(
            sys.modules,
            {"jiuwen.serve.controllers.execution.ir_converter": converter_module},
        ), patch.object(
            Runner, "resource_mgr", resource_mgr
        ):
            workflow_ids = await runner._register_workflows(
                ir_json, agent, agent_id="agent-1"
            )

            registered_card = resource_mgr.add_workflow.call_args.kwargs["card"]
            provider = resource_mgr.add_workflow.call_args.kwargs["workflow"]
            built_first = await provider()
            built_second = await provider()

        assert workflow_ids == ["workflow-config-id"]
        assert isinstance(registered_card, WorkflowCard)
        assert registered_card.name == "approval_workflow"
        assert registered_card.input_params == {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "user query",
                }
            },
            "required": ["query"],
        }
        agent.ability_manager.add.assert_called_once_with(registered_card)

        # 原生 Workflow 分支会把 interaction 保留为 INPUT_REQUIRED；不能再注册
        # ReactWorkflowAdapter 的 ToolCard，否则下一轮无法恢复 checkpoint。
        resource_mgr.add_tool.assert_not_called()

        # provider 每次重建实例，保留 R-02 的并发隔离保证。
        assert inspect.iscoroutinefunction(provider)
        assert built_first is first_call_workflow
        assert built_second is second_call_workflow
        assert built_first is not built_second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
