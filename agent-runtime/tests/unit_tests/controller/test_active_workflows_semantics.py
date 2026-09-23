# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# pylint: disable=protected-access  # 单测需直接调用内部方法 _process_workflows/_process_user_input（白盒验证收窄落键语义）
"""activeWorkflows 权限收窄语义单测（区分"未传"与"显式空列表"）。

背景：Controller 模式按用户权限收窄可调用子工作流（activeWorkflows）。
修复前 activeWorkflows=[] 或校验全失败会被回退为"全部 GENERAL 工作流"
参与意图识别，导致越权。修复后契约：

- 未传 / None → 使用全部 GENERAL 工作流（向后兼容）
- 显式 [] / 校验全失败 → 无 GENERAL 候选（闲聊/全局意图/子Agent 仍在，
  识别失败走 DEFAULT 兜底），显式空列表落库为 [] 而非 None
"""

from types import SimpleNamespace

import pytest

from agent_runtime.schemas.orchestration_mgr import ExecutionParams as AgentRunParams
from jiuwen.controller.common.constants import WorkflowConstants
from jiuwen.controller.common.enum import WorkflowType
from jiuwen.controller.common.message_type import MessageType
from jiuwen.controller.task_planner.planners.controller_planner import ControllerPlanner
from jiuwen.controller.task_planner.planning_modules.intention_detect_module import (
    IntentionDetectModule,
)
from jiuwen.serve.schemas.orchestration_mgr import ExecutionParams as JiuWenParams


def _make_workflow_context(workflow_id, workflow_name):
    return SimpleNamespace(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        config_name=workflow_name,
        description=f"desc of {workflow_name}",
    )


class _StubContextManager:
    """覆盖被测方法所需的最小 context_manager 接口"""

    def __init__(self, general_contexts, normal_contexts):
        self._contexts = general_contexts
        self._normal = normal_contexts
        self.globals = {}
        self.add_user_message_calls = []
        self.normal_contexts_calls = 0

    def get_workflow_context_by_id(self, workflow_id, workflow_type):
        assert workflow_type == WorkflowType.GENERAL
        return self._contexts.get(workflow_id)

    def get_normal_workflow_contexts(self):
        self.normal_contexts_calls += 1
        return list(self._normal)

    def set_global_variables(self, key, value):
        self.globals[key] = value

    def get_global_variables(self, key, default=None):
        return self.globals.get(key, default)

    def add_user_message(self, content, enable_history=True):
        self.add_user_message_calls.append((content, enable_history))


class TestExecutionParamsDefault:
    """schema 层：默认 None（未传）必须与显式 [] 可区分"""

    @staticmethod
    def test_defaults_are_none_both_trees():
        assert AgentRunParams().active_workflows is None
        assert AgentRunParams().workflow_sequence is None
        assert JiuWenParams().active_workflows is None
        assert JiuWenParams().workflow_sequence is None

    @staticmethod
    def test_explicit_empty_list_preserved():
        assert AgentRunParams.model_validate({"activeWorkflows": []}).active_workflows == []
        assert JiuWenParams.model_validate({"activeWorkflows": []}).active_workflows == []

    @staticmethod
    def test_explicit_ids_preserved():
        params = AgentRunParams.model_validate({"activeWorkflows": ["a", "b"]})
        assert params.active_workflows == ["a", "b"]


class TestProcessWorkflowsSemantics:
    """意图识别层：_process_workflows 的 None / [] / 非法 id 语义"""

    @staticmethod
    def _make_module(general_contexts, normal_contexts):
        module = object.__new__(IntentionDetectModule)
        module.context_manager = _StubContextManager(general_contexts, normal_contexts)
        # _process_workflows 循环体内维护的三个路由映射表（__init__ 里的实例属性）
        module.category_2_intent_function_map = {}
        module.intent_function_2_category_map = {}
        module.intent_id_to_function_map = {}
        return module

    @staticmethod
    def _workflow_intents(intents):
        """_process_workflows 只往 intents 追加工作流意图（闲聊/全局意图由调用方预置）"""
        return intents

    def test_none_uses_all_general_workflows(self):
        ctx_a = _make_workflow_context("wfA", "A")
        ctx_b = _make_workflow_context("wfB", "B")
        module = self._make_module({}, [ctx_a, ctx_b])

        intents = []
        module._process_workflows(intents, category_index=2, active_workflows=None)

        assert len(intents) == 2
        names = {i["name"] for i in intents}
        assert names == {"A", "B"}

    def test_empty_list_yields_no_workflow_candidates(self):
        """显式空列表：不回退全量，工作流候选为零（修复点）"""
        ctx_a = _make_workflow_context("wfA", "A")
        ctx_b = _make_workflow_context("wfB", "B")
        module = self._make_module({}, [ctx_a, ctx_b])

        intents = []
        module._process_workflows(intents, category_index=2, active_workflows=[])

        assert intents == []
        # 关键：没有走 get_normal_workflow_contexts 回退（None 路径才会调用它）
        assert module.context_manager.normal_contexts_calls == 0

    def test_invalid_ids_filtered_not_fallback(self):
        """校验全失败（如 DEFAULT 工作流 id）：按空列表处理，不回退全量（修复点）"""
        ctx_a = _make_workflow_context("wfA", "A")
        module = self._make_module({}, [ctx_a])

        intents = []
        module._process_workflows(intents, category_index=2, active_workflows=["wfC"])

        assert intents == []

    def test_valid_and_invalid_mixed_keeps_valid_only(self):
        ctx_a = _make_workflow_context("wfA", "A")
        module = self._make_module({"wfA": ctx_a}, [ctx_a])

        intents = []
        module._process_workflows(
            intents, category_index=2, active_workflows=["wfA", "wfC"]
        )

        assert len(intents) == 1
        assert intents[0]["name"] == "A"


class TestProcessUserInputActiveWorkflows:
    """planner 层：_process_user_input 校验后 ACTIVE_WORKFLOWS_KEY 的落库语义"""

    @staticmethod
    def _make_planner(general_contexts, normal_contexts):
        planner = object.__new__(ControllerPlanner)
        planner.task_id = "task_ut"
        planner.context_manager = _StubContextManager(general_contexts, normal_contexts)
        planner.plan_config = SimpleNamespace(global_intents=None)
        return planner

    @staticmethod
    def _make_message(req_params):
        runtime_context = SimpleNamespace(
            conversation_id="cid_ut",
            agent_workflow_context={WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY: req_params},
        )
        return SimpleNamespace(
            message_type=MessageType.USER_INPUT,
            content="hello",
            runtime_data={"runtime_context": runtime_context},
        )

    def test_missing_keeps_key_none(self):
        """未传：ACTIVE_WORKFLOWS_KEY 保持 None（后续走全量，向后兼容）"""
        planner = self._make_planner({}, [])
        planner._process_user_input(self._make_message({}))

        assert (
            planner.context_manager.globals[WorkflowConstants.ACTIVE_WORKFLOWS_KEY]
            is None
        )

    def test_explicit_empty_sets_empty_key(self):
        """显式空列表：落 [] 而非 None（修复点，防回退全量越权）"""
        planner = self._make_planner({}, [])
        planner._process_user_input(
            self._make_message({"active_workflows": []})
        )

        assert (
            planner.context_manager.globals[WorkflowConstants.ACTIVE_WORKFLOWS_KEY] == []
        )

    def test_all_invalid_sets_empty_key(self):
        """校验全失败（DEFAULT id 不在 GENERAL 注册表）：落 [] + error 日志（修复点）"""
        ctx_a = _make_workflow_context("wfA", "A")
        planner = self._make_planner({"wfA": ctx_a}, [ctx_a])
        planner._process_user_input(
            self._make_message({"active_workflows": ["wfC_default"]})
        )

        assert (
            planner.context_manager.globals[WorkflowConstants.ACTIVE_WORKFLOWS_KEY] == []
        )

    def test_valid_ids_set_validated_key(self):
        ctx_a = _make_workflow_context("wfA", "A")
        planner = self._make_planner({"wfA": ctx_a}, [ctx_a])
        planner._process_user_input(
            self._make_message({"active_workflows": ["wfA", "wfC_default"]})
        )

        assert (
            planner.context_manager.globals[WorkflowConstants.ACTIVE_WORKFLOWS_KEY]
            == ["wfA"]
        )

    def test_sequence_priority_registers_sequence(self):
        """workflowSequence 有效时登记序列键，读取端先查序列——优先级语义不变。

        activeWorkflows 同时传入时其键也会照旧落库（与修复前原逻辑一致，
        :284-287 置 None 后 active 块仍会重新落键），但 _get_next_workflow
        先查 VALID_WORKFLOW_SEQUENCE_KEY，序列优先在读取端保证，本修复不改。
        """
        ctx_a = _make_workflow_context("wfA", "A")
        planner = self._make_planner({"wfA": ctx_a}, [ctx_a])
        planner._process_user_input(
            self._make_message(
                {"workflow_sequence": ["wfA"], "active_workflows": ["wfA"]}
            )
        )

        assert planner.context_manager.globals[
            WorkflowConstants.VALID_WORKFLOW_SEQUENCE_KEY
        ] == ["wfA"]
        # 与修复前一致：active 键同样落库（读取端先查序列键，不影响优先级）
        assert (
            planner.context_manager.globals[WorkflowConstants.ACTIVE_WORKFLOWS_KEY]
            == ["wfA"]
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
