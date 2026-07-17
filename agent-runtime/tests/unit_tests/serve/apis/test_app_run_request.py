# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Tests for app_run_request.py — request schema validation."""

import pytest
from pydantic import ValidationError

from agent_runtime.serve.apis.app_run_request import (
    WorkflowAppRunRequest,
    AgentAppRunRequest,
    WorkflowRunContext,
    AgentRunContext,
)


class TestWorkflowAppRunRequest:
    """Workflow request schema tests."""

    @staticmethod
    def test_defaults():
        req = WorkflowAppRunRequest()
        assert req.inputs == {}
        assert req.globals == {}
        assert req.environment == {}
        assert req.messages == []
        assert req.enable_history is True

    @staticmethod
    def test_with_inputs():
        req = WorkflowAppRunRequest(inputs={"query": "hello", "key": "value"})
        assert req.inputs["query"] == "hello"
        assert req.inputs["key"] == "value"

    @staticmethod
    def test_memory_inputs():
        req = WorkflowAppRunRequest(memory_inputs={"mem_key": "mem_val"})
        assert req.memory_inputs == {"mem_key": "mem_val"}

    @staticmethod
    def test_user_id_alias():
        req = WorkflowAppRunRequest.model_validate({"userId": "user-123"})
        assert req.user_id == "user-123"

    @staticmethod
    def test_enable_history_alias():
        req = WorkflowAppRunRequest.model_validate({"enable_history": False})
        assert req.enable_history is False

    @staticmethod
    def test_plugin_configs():
        from agent_runtime.schemas.orchestration_mgr import PluginConfig
        pc = PluginConfig.model_validate({"pluginId": "p1"})
        req = WorkflowAppRunRequest(plugin_configs=[pc])
        assert len(req.plugin_configs) == 1
        assert req.plugin_configs[0].plugin_id == "p1"

    @staticmethod
    def test_version_accepts_string():
        req = WorkflowAppRunRequest(version="v1")
        assert req.version == "v1"

    @staticmethod
    def test_version_accepts_int():
        req = WorkflowAppRunRequest(version=42)
        assert req.version == 42


class TestAgentAppRunRequest:
    """Agent request schema tests."""

    @staticmethod
    def test_defaults():
        req = AgentAppRunRequest()
        assert req.query is None
        assert req.inputs == {}
        assert req.tool_switch_dict == {}
        assert req.histories == []
        assert req.files == []
        assert req.agent_type == "auto"
        assert req.enable_history is True

    @staticmethod
    def test_query_optional():
        """query field is optional — no validation error when omitted."""
        req = AgentAppRunRequest()
        assert req.query is None

    @staticmethod
    def test_query_with_value():
        req = AgentAppRunRequest(query="test question")
        assert req.query == "test question"

    @staticmethod
    def test_query_alias():
        req = AgentAppRunRequest.model_validate({"query": "aliased query"})
        assert req.query == "aliased query"

    @staticmethod
    def test_inputs():
        req = AgentAppRunRequest(inputs={"key": "val"})
        assert req.inputs["key"] == "val"

    @staticmethod
    def test_tool_switch_dict_alias():
        req = AgentAppRunRequest.model_validate({
            "tool_switch_dict": {"tool1": True, "tool2": False}
        })
        assert req.tool_switch_dict == {"tool1": True, "tool2": False}

    @staticmethod
    def test_agent_type_default():
        req = AgentAppRunRequest()
        assert req.agent_type == "auto"

    @staticmethod
    def test_agent_type_alias():
        req = AgentAppRunRequest.model_validate({"agent_type": "ReAct"})
        assert req.agent_type == "ReAct"

    @staticmethod
    def test_user_id_alias():
        req = AgentAppRunRequest.model_validate({"userId": "agent-user"})
        assert req.user_id == "agent-user"

    @staticmethod
    def test_enable_history_alias():
        req = AgentAppRunRequest.model_validate({"enable_history": False})
        assert req.enable_history is False

    @staticmethod
    def test_files():
        req = AgentAppRunRequest(files=[{"name": "file.txt", "type": "text"}])
        assert len(req.files) == 1
        assert req.files[0]["name"] == "file.txt"

    @staticmethod
    def test_model_deployment_id():
        req = AgentAppRunRequest.model_validate({
            "model_deployment_id": "deploy-123"
        })
        assert req.model_deployment_id == "deploy-123"

    @staticmethod
    def test_long_term_memory():
        req = AgentAppRunRequest.model_validate({
            "long_term_memory": {"enabled": True}
        })
        assert req.long_term_memory == {"enabled": True}


class TestRunContextDataclasses:
    """Run context dataclass tests."""

    @staticmethod
    def test_workflow_run_context():
        ctx = WorkflowRunContext(
            project_id="proj-1",
            workflow_id="wf-1",
            conversation_id="conv-1",
            version="v1",
        )
        assert ctx.project_id == "proj-1"
        assert ctx.workflow_id == "wf-1"
        assert ctx.conversation_id == "conv-1"
        assert ctx.version == "v1"

    @staticmethod
    def test_workflow_run_context_no_version():
        ctx = WorkflowRunContext(
            project_id="proj-1",
            workflow_id="wf-1",
            conversation_id="conv-1",
            version=None,
        )
        assert ctx.version is None

    @staticmethod
    def test_agent_run_context():
        ctx = AgentRunContext(
            project_id="proj-2",
            agent_id="agent-1",
            conversation_id="conv-2",
            version="v2",
        )
        assert ctx.project_id == "proj-2"
        assert ctx.agent_id == "agent-1"
        assert ctx.conversation_id == "conv-2"
        assert ctx.version == "v2"

    @staticmethod
    def test_agent_run_context_no_version():
        ctx = AgentRunContext(
            project_id="proj-2",
            agent_id="agent-1",
            conversation_id="conv-2",
            version=None,
        )
        assert ctx.version is None
