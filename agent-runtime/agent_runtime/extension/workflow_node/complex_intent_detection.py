# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
ComplexIntentDetection - 高级意图识别组件

功能特性:
- LLM 意图识别（基于 IntentDetection 组件）
- 子工作流执行（根据意图识别结果选择分支）
- 变量聚合（多分支输出合并）
- 状态管理与中断恢复
- 支持流式输出

设计说明:
- 继承 WorkflowComponent（openjiuwen 标准组件基类）
- 通过组合方式持有 IntentDetection 和 SubWorkflow 实例
- 使用 Session 进行状态管理和交互中断
- 使用 ModelContext 进行上下文管理
"""

from __future__ import annotations

import copy
import time
import traceback
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from agent_runtime.common.session_state_access import get_state_info
from openjiuwen.core.common.logging import workflow_logger, LogEventType
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.base import Graph
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow.components.component import WorkflowComponent
from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter
from pydantic import BaseModel, Field, ValidationError

from jiuwen.extension.workflow_node.intent_detection import IntentDetection
from jiuwen.extension.workflow_node.utils import JiuWenBaseException


_KEY_CLASSIFICATION_ID = "classificationId"
_INPUT = "input"
_COMPLEX_INTENT_TYPE = "EI.ComplexIntentDetection"
_RESPONSE_CONTENT = "responseContent"


class BranchWorkflowConfig(BaseModel):
    """分支工作流配置"""
    ir_path: Optional[str] = None
    workflow_id: Optional[str] = None


class BranchConfig(BaseModel):
    """分支配置"""
    catalog: str = Field(min_length=1)
    id: str = Field(min_length=1)
    configs: Optional[BranchWorkflowConfig] = None


class ComplexIntentDetectionConfig(BaseModel):
    """高级意图识别配置"""
    user_fields: dict = Field(default_factory=dict, alias="userFields")
    system_fields: dict = Field(default_factory=dict, alias="systemFields")
    in3: bool = Field(default=False)
    agg_mode: str = Field(default="first-non-null")
    sub_node_id: str = Field(alias="intentDetectionContainerNodeId")
    branches: List[BranchConfig] = Field(min_length=1)
    groups: dict = Field(min_length=1)
    intent_identification: Optional[dict] = None
    llm: Optional[dict] = None
    prompt: str = ""
    enable_history: bool = False
    chat_history_max_turn: int = 3
    enable_knowledge: bool = False
    kg: dict = Field(default_factory=dict)
    memory: dict = Field(default_factory=dict)
    recall_threshold: float = 0.8


class ExecutionStatus(str, Enum):
    """执行状态枚举"""
    START = "START"
    END = "END"
    USER_INTERACT = "USER_INTERACT"


@dataclass
class ComplexIntentState:
    """高级意图识别组件执行状态"""
    status: ExecutionStatus = ExecutionStatus.START
    intent_result: dict = field(default_factory=dict)
    workflow_id: Optional[str] = None
    sub_workflows: dict = field(default_factory=dict)
    matched_layer: Optional[str] = None
    matched_score: float = 0.0
    branch_id: Optional[str] = None
    resume_query: Optional[str] = None
    interrupt_child_node_id: Optional[str] = None


def parse_value(result: dict, descriptions: list) -> Any:
    """从嵌套字典中按路径解析值"""
    current = result
    for desc in descriptions:
        if desc in current:
            current = current.get(desc)
        else:
            return None
    return current


def _build_intent_conf(conf: dict) -> dict:
    """构建透传给 IntentDetection 的配置"""
    if "kg" in conf and conf.get("kg"):
        category = conf["kg"].get("category")
        if category:
            conf["kg"]["filterString"] = f"category:{category}"
    return conf


def convert_input(inputs: Input) -> dict:
    """转换输入格式"""
    from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
    if isinstance(inputs, InteractiveInput):
        raw = inputs.get_raw_inputs() if hasattr(inputs, 'get_raw_inputs') else None
        result = dict(inputs) if hasattr(inputs, '__iter__') else {}
        if raw:
            result[_INPUT] = raw
        user_fields = inputs.get("userFields", {}) or {}
        return {**result, _INPUT: result.get(_INPUT) or raw or user_fields.get(_INPUT)}
    if _INPUT in inputs:
        return dict(inputs) if isinstance(inputs, dict) else inputs
    if isinstance(inputs, dict):
        user_fields = inputs.get("userFields", {}) or {}
        return {**inputs, _INPUT: user_fields.get(_INPUT)}
    return inputs


class ComplexIntentDetection(WorkflowComponent):
    """高级意图识别组件

    功能：
    - LLM 意图识别（使用 IntentDetection 组件）
    - 子工作流执行（根据意图识别结果选择分支）
    - 变量聚合（多分支输出合并）
    - 状态管理与中断恢复
    - 流式输出支持

    Args:
        configs: 组件配置字典
        node_id: 节点 ID
        node_name: 节点名称
        node_type: 节点类型
    """

    def __init__(
        self,
        configs: dict,
        node_id: Optional[str] = None,
        node_name: Optional[str] = None,
        node_type: str = _COMPLEX_INTENT_TYPE,
    ):
        super().__init__()
        self._configs = configs
        self._node_id = node_id or configs.get("node_id", "")
        self._node_name = node_name or configs.get("name", "")
        self._node_type = node_type

        self._parse_configs()
        self._intent_detection: Optional[IntentDetection] = None
        self._init_intent_detection()

        self._state = ComplexIntentState()
        self._state_retry = ComplexIntentState()
        self._sub_workflows: Dict[str, Any] = {}
        self._branch2group: Dict[str, Dict[str, List[List[str]]]] = {}
        self._build_branch_to_group()

        self._sub_workflow_error: Optional[Exception] = None
        self._session: Optional[Session] = None
        self._context: Optional[ModelContext] = None
        self._router = BranchRouter()

    def _parse_configs(self) -> None:
        """解析配置"""
        try:
            self._config = ComplexIntentDetectionConfig.model_validate(self._configs)
        except ValidationError as e:
            workflow_logger.error(
                f"ComplexIntentDetection config validation failed: {e}",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
            )
            raise JiuWenBaseException(
                error_code=101000,
                message=f"ComplexIntentDetection config validation failed: {e}",
            ) from e

        self._branches: Dict[str, BranchConfig] = {
            b.id: b for b in self._config.branches
        }
        self._wf_to_branches: Dict[str, BranchConfig] = {
            b.configs.workflow_id: b
            for b in self._config.branches
            if b.configs and b.configs.workflow_id
        }

    def _init_intent_detection(self) -> None:
        """初始化意图识别组件"""
        intent_configs = copy.deepcopy(self._configs)

        if "branches" not in intent_configs:
            intent_configs["branches"] = [
                {"id": b.id, "catalog": b.catalog}
                for b in self._config.branches
            ]

        if self._config.llm:
            intent_configs["llm"] = self._config.llm
        if self._config.prompt:
            intent_configs["prompt"] = self._config.prompt

        intent_configs["enableHistory"] = self._config.enable_history
        intent_configs["chatHistoryMaxTurn"] = self._config.chat_history_max_turn
        intent_configs["enableKnowledge"] = self._config.enable_knowledge

        if self._config.kg:
            intent_configs["kg"] = self._config.kg
        if self._config.memory:
            intent_configs["memory"] = self._config.memory

        intent_configs["recallThreshold"] = self._config.recall_threshold

        self._intent_configs = _build_intent_conf(intent_configs)
        self._intent_detection = IntentDetection(self._intent_configs)

    def _build_branch_to_group(self) -> None:
        """构建分支到组的映射"""
        for group_name, branches in self._config.groups.items():
            for branch in branches:
                desc = branch.replace("${", "").replace("}", "").split(".")
                if len(desc) >= 2:
                    node_id = desc[0]
                    self._branch2group.setdefault(node_id, {}).setdefault(
                        group_name, []
                    ).append(desc[1:])

    def reset(self) -> bool:
        """重置组件状态"""
        self._state = deepcopy(self._state_retry)
        self._sub_workflows.clear()
        self._sub_workflow_error = None
        return True

    def get_state(self) -> ComplexIntentState:
        """获取当前执行状态"""
        return self._state

    async def load_state(self, state: ComplexIntentState) -> None:
        """从输入状态恢复

        恢复状态后，需要同时恢复子工作流的实例。
        """
        self._state = deepcopy(state)

        if self._state.sub_workflows and self._state.workflow_id:
            workflow_id = self._state.workflow_id
            if workflow_id in self._state.sub_workflows:
                recover_data = self._state.sub_workflows[workflow_id]
                await self._recover_sub_workflow(workflow_id, recover_data)

    async def _recover_sub_workflow(self, workflow_id: str, recover_data: dict) -> None:
        """恢复子工作流实例"""
        from jiuwen.serve.controllers.execution.ir_converter import IRConverter
        from storage import get_storage_provider
        from agent_runtime.common.ir_interfaces import StorageConfigError, StorageReadError

        try:
            recover_config = recover_data.get("configs")
            instance_data = recover_data.get("instance_data")
            if not recover_config:
                workflow_logger.warning(f"No recover config for workflow {workflow_id}")
                return

            branch_config = BranchWorkflowConfig(**recover_config)

            ir_path = branch_config.ir_path
            if not ir_path:
                return

            provider = get_storage_provider()
            ir_json_str = await provider.get_content(ir_path)
            import json
            child_ir = json.loads(ir_json_str)
            child_workflow = await IRConverter.async_ir_to_workflow(child_ir)

            sub_workflow_comp = SubWorkflowComponentWrapper(
                workflow=child_workflow,
                node_id=workflow_id,
                node_name=f"{self._node_name}-sub",
            )

            if instance_data and hasattr(sub_workflow_comp, 'load_state'):
                await sub_workflow_comp.load_state(instance_data)

            self._sub_workflows[workflow_id] = {
                "instance": sub_workflow_comp,
                "sub_instance": child_workflow,
                "configs": recover_config,
            }

            workflow_logger.info(f"Recovered sub-workflow {workflow_id}")
        except (StorageConfigError, StorageReadError) as e:
            workflow_logger.error(f"Failed to load sub-workflow IR for recovery: {e}")
        except Exception as e:
            workflow_logger.error(f"Failed to recover sub-workflow {workflow_id}: {e}")

    def add_component(self, graph: Graph, node_id: str, wait_for_all: bool = False) -> None:
        """将组件添加到工作流图"""
        graph.add_node(node_id, self.to_executable(), wait_for_all=wait_for_all)

    def to_executable(self) -> "ComplexIntentDetection":
        """返回可执行实例"""
        return self

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext, **kwargs
    ) -> Output:
        """同步执行入口"""
        start_time = time.perf_counter()
        self._session = session
        self._context = context

        try:
            inputs_dict = convert_input(inputs)

            intent_result, intent_branch = await self._get_intent_result(inputs_dict, **kwargs)
            # 单节点执行仅返回意图
            if inputs_dict.get("__single_debug_recovery__", False):
                return intent_result

            wf_id, wf_result = await self._execute_branch_workflow(inputs_dict, intent_branch, **kwargs)

            intent_result[_RESPONSE_CONTENT] = wf_result.get(_RESPONSE_CONTENT, "") if wf_result else ""
            result = self._get_aggregate_result(wf_id, wf_result, intent_result)

            duration = round((time.perf_counter() - start_time) * 1000)
            workflow_logger.info(
                f"ComplexIntentDetection completed in {duration}ms",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_id=self._node_id,
                component_type_str=_COMPLEX_INTENT_TYPE,
                session_id=session.get_session_id(),
            )

            return result

        except Exception as e:
            from openjiuwen.core.graph.pregel import GraphInterrupt
            if isinstance(e, GraphInterrupt):
                raise
            workflow_logger.error(
                f"ComplexIntentDetection invoke failed: {e}\n{traceback.format_exc()}",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_id=self._node_id,
                component_type_str=_COMPLEX_INTENT_TYPE,
            )
            return {
                "result": self._get_default_result(),
                "error": str(e),
            }

    async def _get_intent_result(self, inputs: dict, **kwargs) -> tuple[dict, str]:
        """获取意图识别结果"""
        if self._state.status == ExecutionStatus.START:
            if self._intent_detection is None:
                self._init_intent_detection()

            intent_result = await self._intent_detection.invoke(
                inputs, self._session, self._context, **kwargs
            )

            self._state.intent_result = intent_result
            classification_id = intent_result.get(_KEY_CLASSIFICATION_ID, 0)
            intent_branch = f"branch_{classification_id}"
            self._state.branch_id = intent_branch
        else:
            intent_result = self._state.intent_result
            classification_id = self._state.intent_result.get(_KEY_CLASSIFICATION_ID, 0)
            intent_branch = f"branch_{classification_id}"

        return intent_result, intent_branch

    async def _execute_branch_workflow(
        self, inputs: dict, intent_branch: str, **kwargs
    ) -> tuple[Optional[str], Optional[dict]]:
        """执行分支工作流"""
        branch_config = self._branches.get(intent_branch)
        if not branch_config:
            workflow_logger.warning(f"Branch {intent_branch} not found in configuration")
            self._state.status = ExecutionStatus.END
            return None, None

        if not branch_config.configs or not branch_config.configs.workflow_id:
            self._state.status = ExecutionStatus.END
            return None, None

        workflow_id = branch_config.configs.workflow_id
        self._state.workflow_id = workflow_id

        try:
            wf_result = await self._invoke_sub_workflow(inputs, branch_config.configs, **kwargs)
            return workflow_id, wf_result
        except Exception as e:
            from openjiuwen.core.graph.pregel import GraphInterrupt
            if isinstance(e, GraphInterrupt):
                raise
            self._state.status = ExecutionStatus.END
            self._sub_workflow_error = e
            workflow_logger.error(
                f"Sub-workflow execution failed: {e}\n{traceback.format_exc()}",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
            )
            raise

    async def _invoke_sub_workflow(
        self, inputs: dict, branch_config: BranchWorkflowConfig, **kwargs
    ) -> dict:
        """调用子工作流

        核心逻辑：
        1. 检查是否需要恢复（从 session 读取 INTERACTIVE_INPUT）
        2. 如果需要恢复，使用 InteractiveInput 包装用户输入
        3. 调用子工作流的 invoke 方法（SubWorkflow 会自动处理中断）
        4. 保存子工作流状态，以便下次恢复
        """
        from openjiuwen.core.session.interaction.interactive_input import InteractiveInput

        workflow_id = branch_config.workflow_id
        if not workflow_id:
            return {}

        if workflow_id not in self._sub_workflows:
            await self._init_sub_workflow(workflow_id, branch_config)

        sub_workflow_info = self._sub_workflows.get(workflow_id)
        if not sub_workflow_info:
            return {}

        sub_workflow = sub_workflow_info.get("instance")
        sub_instance = sub_workflow_info.get("sub_instance")
        if not sub_workflow:
            return {}

        is_resuming = self._state.status == ExecutionStatus.USER_INTERACT
        is_child_resuming = self._check_child_workflow_needs_resume()

        sub_checkpoint_exists = False
        if self._session and workflow_id:
            inner_session = getattr(self._session, '_inner', None)
            if inner_session:
                try:
                    checkpointer = inner_session.checkpointer()
                    sub_checkpoint_exists = await checkpointer.session_exists(inner_session.session_id())
                except (KeyError, AttributeError, RuntimeError):
                    pass

        should_resume = is_resuming or is_child_resuming or sub_checkpoint_exists

        if isinstance(inputs, InteractiveInput):
            sub_inputs = inputs
        else:
            sub_inputs = self._build_sub_workflow_input(inputs)

            if should_resume:
                resume_query = self._extract_resume_query() or ""
                child_node_id = self._state.interrupt_child_node_id
                if child_node_id:
                    sub_inputs = InteractiveInput()
                    sub_inputs.update(child_node_id, resume_query)
                else:
                    sub_inputs = InteractiveInput(raw_inputs=resume_query)

        try:
            result = await sub_workflow.invoke(
                sub_inputs, self._session, self._context, is_resuming=should_resume, **kwargs
            )

            sub_workflow_state = sub_workflow.get_state()
            if isinstance(sub_workflow_state, dict):
                status_str = sub_workflow_state.get("status", "END")
                status_str_upper = status_str.upper() if isinstance(status_str, str) else status_str
                self._state.status = ExecutionStatus(status_str_upper) if isinstance(status_str, str) else status_str
            else:
                self._state.status = getattr(sub_workflow_state, 'status', ExecutionStatus.END)

            if self._state.status != ExecutionStatus.END and workflow_id in self._sub_workflows:
                if sub_instance and hasattr(sub_instance, 'get_state'):
                    self._state.sub_workflows.setdefault(workflow_id, {})["sub_instance_data"] = \
                        sub_instance.get_state()
                if hasattr(sub_workflow, 'get_state'):
                    self._state.sub_workflows.setdefault(workflow_id, {})["instance_data"] = \
                        sub_workflow.get_state()

            return result if isinstance(result, dict) else {_RESPONSE_CONTENT: result}
        except Exception as e:
            from openjiuwen.core.graph.pregel import GraphInterrupt
            if isinstance(e, GraphInterrupt):
                self._state.status = ExecutionStatus.USER_INTERACT
                if hasattr(sub_workflow, '_interrupt_child_node_id'):
                    self._state.interrupt_child_node_id = sub_workflow._interrupt_child_node_id
                raise
            workflow_logger.error(f"Sub-workflow invoke failed: {e}\n{traceback.format_exc()}")
            raise

    def _check_child_workflow_needs_resume(self) -> bool:
        """检查子工作流是否需要从中断恢复"""
        from openjiuwen.core.common.constants.constant import INTERACTIVE_INPUT

        try:
            session_state = self._session.get_state() if self._session else {}
            if isinstance(session_state, dict):
                workflow_state = session_state.get("workflow_state", {})
                if isinstance(workflow_state, dict):
                    # 优先检查 __interactive_input__ (双下划线)
                    if workflow_state.get("__interactive_input__"):
                        return True
                    # 兜底：检查 workflow.workflow 中的 INTERACTIVE_INPUT
                    workflow = workflow_state.get("workflow", {})
                    if isinstance(workflow, dict):
                        inner_workflow = workflow.get("workflow", {})
                        interactive_input = (
                            inner_workflow.get(INTERACTIVE_INPUT)
                            if isinstance(inner_workflow, dict)
                            else None
                        )
                        if interactive_input:
                            return True
        except (KeyError, TypeError, AttributeError) as e:
            workflow_logger.warn(f"get sub workflow session checkpoint failed: {e}\n{traceback.format_exc()}")
            pass
        return False

    def _extract_resume_query(self) -> Optional[str]:
        """从 session 中提取恢复查询"""
        from openjiuwen.core.common.constants.constant import INTERACTIVE_INPUT

        try:
            if self._session:
                workflow_state = get_state_info(self._session, "workflow_state")
                if isinstance(workflow_state, dict):
                    # 优先从 __interactive_input__ (双下划线) 读取恢复输入
                    interactive_input = workflow_state.get("__interactive_input__")
                    if interactive_input:
                        if isinstance(interactive_input, list) and interactive_input:
                            last = interactive_input[-1]
                            if hasattr(last, "content"):
                                return last.content
                            return str(last)
                        return str(interactive_input) if interactive_input else None
                    # 兜底：从 workflow.workflow 中读取
                    workflow = workflow_state.get("workflow", {})
                    if isinstance(workflow, dict):
                        inner_workflow = workflow.get("workflow", {})
                        interactive_input = (
                            inner_workflow.get(INTERACTIVE_INPUT)
                            if isinstance(inner_workflow, dict)
                            else None
                        )
                        if interactive_input:
                            if isinstance(interactive_input, list) and interactive_input:
                                last = interactive_input[-1]
                                if hasattr(last, "content"):
                                    return last.content
                                return str(last)
                            return str(interactive_input) if interactive_input else None
        except Exception as e:
            workflow_logger.warn(f"get session checkpoint failed: {e}\n{traceback.format_exc()}")
        return None

    async def _init_sub_workflow(
        self, workflow_id: str, branch_config: BranchWorkflowConfig
    ) -> None:
        """初始化子工作流"""
        from jiuwen.serve.controllers.execution.ir_converter import IRConverter
        from storage import get_storage_provider
        from agent_runtime.common.ir_interfaces import StorageConfigError, StorageReadError

        ir_path = branch_config.ir_path
        if not ir_path:
            workflow_logger.warning(f"No ir_path for workflow {workflow_id}")
            return

        try:
            provider = get_storage_provider()
            ir_json_str = await provider.get_content(ir_path)

            import json
            child_ir = json.loads(ir_json_str)
            child_workflow = await IRConverter.async_ir_to_workflow(child_ir)

            sub_workflow_comp = SubWorkflowComponentWrapper(
                workflow=child_workflow,
                node_id=workflow_id,
                node_name=f"{self._node_name}-sub",
            )

            self._sub_workflows[workflow_id] = {
                "instance": sub_workflow_comp,
                "sub_instance": child_workflow,
                "configs": branch_config.model_dump() if hasattr(branch_config, "model_dump") else {},
            }

        except (StorageConfigError, StorageReadError) as e:
            workflow_logger.error(f"Failed to load sub-workflow IR: {e}")
        except Exception as e:
            workflow_logger.error(f"Failed to init sub-workflow {workflow_id}: {e}\n{traceback.format_exc()}")

    @staticmethod
    def _build_sub_workflow_input(inputs: dict) -> dict:
        """构建子工作流输入"""
        sub_inputs = copy.deepcopy(inputs)
        if "systemFields" in sub_inputs:
            query = sub_inputs.get(_INPUT) or sub_inputs.get("query", "")
            sub_inputs["systemFields"]["query"] = query
        return sub_inputs

    def _get_aggregate_result(
        self, wf_id: Optional[str], wf_result: Optional[dict], intent_result: dict
    ) -> dict:
        """获取聚合结果"""
        if self._state.status != ExecutionStatus.END:
            return {"workflow_result": wf_result} | intent_result

        if wf_id is None or wf_result is None:
            return intent_result

        return self._aggregate_output(wf_id, wf_result) | intent_result

    def _aggregate_output(self, wf_id: str, wf_result: dict) -> dict:
        """聚合输出"""
        branch = self._wf_to_branches.get(wf_id)
        if not branch:
            return {}

        branch_id = branch.id
        group_result = {}

        for group_name, desc_list in self._branch2group.get(branch_id, {}).items():
            group_result[group_name] = next(
                (parse_value(wf_result, desc) for desc in desc_list), None
            )

        return group_result

    @staticmethod
    def _get_default_result() -> dict:
        """获取默认结果"""
        return {
            "result": "分类0",
            "reason": "default",
            _KEY_CLASSIFICATION_ID: 0,
            "name": "其他意图",
        }

    @property
    def node_id(self) -> str:
        """获取节点 ID"""
        return self._node_id

    @property
    def node_name(self) -> str:
        """获取节点名称"""
        return self._node_name

    @property
    def node_type(self) -> str:
        """获取节点类型"""
        return self._node_type


class SubWorkflowComponentWrapper(WorkflowComponent):
    """子工作流包装组件

    用于包装 openjiuwen Workflow 实例，使其可以作为 WorkflowComponent 使用。
    支持中断检测和处理，当子工作流需要用户交互时会触发 session.interact()。
    """

    def __init__(self, workflow: Any, node_id: str, node_name: str = ""):
        super().__init__()
        self._workflow = workflow
        self._node_id = node_id
        self._node_name = node_name or node_id
        self._node_state = None
        self._interrupt_child_node_id = None
        self._pending_interact_prompt = ""

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext, is_resuming: bool = False, **kwargs
    ) -> Output:
        """执行子工作流"""
        from openjiuwen.core.session.stream import BaseStreamMode
        from openjiuwen.core.session.stream.base import OutputSchema
        from openjiuwen.core.session.interaction.interactive_input import InteractiveInput
        from openjiuwen.core.common.constants.constant import INTERACTION
        from openjiuwen.core.graph.pregel import GraphInterrupt

        try:
            is_interactive_input = isinstance(inputs, InteractiveInput)
            if is_interactive_input:
                workflow_inputs = inputs
            else:
                workflow_inputs = {"query": inputs.get(_INPUT) if isinstance(inputs, dict) else str(inputs)}
                if isinstance(inputs, dict):
                    workflow_inputs.update({k: v for k, v in inputs.items()})

            inner_session = getattr(session, '_inner', None)
            if inner_session:
                from openjiuwen.core.session.internal.workflow import WorkflowSession
                checkpointer = inner_session.checkpointer()
                sub_workflow_id = getattr(self._workflow, '_card', None) and self._workflow._card.id or 'unknown'
                temp_session = WorkflowSession(
                    workflow_id=sub_workflow_id,
                    parent=inner_session,
                )
                recovery_inputs = workflow_inputs if (is_interactive_input or is_resuming) else None
                await checkpointer.pre_workflow_execute(temp_session, recovery_inputs)

            stream_modes = [BaseStreamMode.OUTPUT, BaseStreamMode.CUSTOM]
            stream_result = self._workflow.stream(
                workflow_inputs, session, context=context, stream_modes=stream_modes, is_sub=True
            )

            collected = []
            final_res = ""
            final_val = {}

            async for chunk in stream_result:
                collected.append(chunk)

                chunk_type = None
                chunk_payload = None
                if isinstance(chunk, OutputSchema):
                    chunk_type = chunk.type
                    chunk_payload = chunk.payload if isinstance(chunk.payload, dict) else {}

                is_interaction = False
                if chunk_type == INTERACTION or (isinstance(chunk_type, str) and '__interaction__' in str(chunk_type)):
                    is_interaction = True
                    if hasattr(chunk_payload, 'id'):
                        self._interrupt_child_node_id = chunk_payload.id
                    elif isinstance(chunk_payload, dict):
                        self._interrupt_child_node_id = chunk_payload.get('id')
                        interact_value = chunk_payload.get('value') or chunk_payload.get('prompt', '')
                        if interact_value:
                            self._pending_interact_prompt = str(interact_value)

                if is_interaction:
                    self._node_state = {
                        "status": "user_interact",
                        "interrupt_child_node_id": self._interrupt_child_node_id,
                        _RESPONSE_CONTENT: final_res,
                        "userFields": final_val,
                    }
                    await session.interact(self._pending_interact_prompt or final_res)

                if hasattr(chunk, 'model_dump'):
                    chunk_dict = chunk.model_dump()
                elif hasattr(chunk, 'dict'):
                    chunk_dict = chunk.model_dump()
                elif isinstance(chunk, dict):
                    chunk_dict = chunk
                else:
                    chunk_dict = {"type": type(chunk).__name__, "data": str(chunk)}

                if "data" in chunk_dict:
                    chunk_dict["payload"] = chunk_dict.pop("data")

                if (chunk_dict.get("type", "workflow_end") in ["workflow_final", "workflow_end"] or
                        chunk_dict.get("payload", {}).get("node_type") == "jiuwen.end"):
                    continue

                await session.write_stream(chunk_dict)

                if isinstance(chunk, OutputSchema):
                    payload = chunk.payload if isinstance(chunk.payload, dict) else {}
                    if chunk.type == "workflow_final":
                        final_res = payload.get("answer", "")
                        final_val = payload.get("user_fields", {})
                    elif chunk.type == "message_end":
                        final_res = payload.get("answer", "")
                        if "userFields" in payload:
                            final_val = payload.get("userFields", {})

            self._node_state = {
                "status": "end",
                _RESPONSE_CONTENT: final_res,
                "userFields": final_val,
            }
            if inner_session:
                from openjiuwen.core.session.internal.workflow import WorkflowSession
                checkpointer = inner_session.checkpointer()
                sub_workflow_id = getattr(self._workflow, '_card', None) and self._workflow._card.id or 'unknown'
                temp_session = WorkflowSession(
                    workflow_id=sub_workflow_id,
                    parent=inner_session,
                    session_id=inner_session.session_id()
                )
                await checkpointer.post_workflow_execute(temp_session, self._node_state, exception=None)

            merged_result = self._merge_results(collected) if collected else {}
            merged_result[_RESPONSE_CONTENT] = merged_result.get("answer", final_res)
            return merged_result

        except GraphInterrupt:
            raise
        except Exception as e:
            workflow_logger.error(f"SubWorkflowComponentWrapper invoke failed: {e}\n{traceback.format_exc()}")
            raise

    def get_state(self) -> dict:
        """获取当前状态"""
        return self._node_state or {"status": "end"}

    def load_state(self, state: dict) -> None:
        """加载状态"""
        self._node_state = state
        if state:
            self._interrupt_child_node_id = state.get("interrupt_child_node_id")

    @staticmethod
    def _merge_results(chunks: list) -> dict:
        """合并流式结果，提取关键输出字段"""
        result = {}
        final_data = {}

        for chunk in chunks:
            if hasattr(chunk, 'type') and (hasattr(chunk, 'data') or hasattr(chunk, 'payload')):
                chunk_type_str = str(chunk.type) if hasattr(chunk.type, 'value') else str(chunk.type)
                chunk_data = chunk.data if hasattr(chunk, 'data') else chunk.payload

                if isinstance(chunk_data, dict):
                    if chunk_type_str in ("workflow_end", "workflow_final"):
                        final_data[_RESPONSE_CONTENT] = chunk_data.get("answer", "")
                        if "userFields" in chunk_data:
                            final_data["userFields"] = chunk_data.get("userFields")
                        if "user_fields" in chunk_data:
                            final_data["userFields"] = chunk_data.get("user_fields")
                        continue

                    if chunk_type_str == "message_end":
                        final_data = {
                            "answer": chunk_data.get("answer", ""),
                            _RESPONSE_CONTENT: chunk_data.get("answer", ""),
                            "origin_answer": chunk_data.get("origin_answer", ""),
                            "result": chunk_data.get("result", ""),
                            "node_id": chunk_data.get("node_id", ""),
                            "node_name": chunk_data.get("node_name", ""),
                            "node_type": chunk_data.get("node_type", ""),
                            "think": chunk_data.get("think", ""),
                            "should_interrupt": chunk_data.get("should_interrupt", False),
                        }
                        if "userFields" in chunk_data:
                            final_data["userFields"] = chunk_data.get("userFields")
                    elif chunk_type_str == "partial_content":
                        if "node_id" not in final_data:
                            final_data["node_id"] = chunk_data.get("node_id", "")
                        if "node_name" not in final_data:
                            final_data["node_name"] = chunk_data.get("node_name", "")
                        if "node_type" not in final_data:
                            final_data["node_type"] = chunk_data.get("node_type", "")
                        if "answer" not in final_data and "answer" in chunk_data:
                            final_data["answer"] = chunk_data.get("answer", "")
                    result.update(chunk_data)
                elif chunk_data is not None:
                    final_data["_raw"] = str(chunk_data)
                continue

            if isinstance(chunk, dict):
                result.update(chunk)
                continue

            if chunk is not None:
                result["_raw_chunk"] = str(chunk)

        result.update(final_data)
        return result

    def add_component(self, graph: Graph, node_id: str, wait_for_all: bool = False) -> None:
        """添加到工作流图"""
        graph.add_node(node_id, self, wait_for_all=wait_for_all)