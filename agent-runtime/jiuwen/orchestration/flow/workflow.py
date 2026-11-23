# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
Workflow execution instance
"""

import asyncio
import copy
import datetime
import os
import sys
import time
from typing import Union, Optional, AsyncGenerator

from jiuwen.common.configs.env_constants import WORKFLOW_TASK_CANCEL_TIMEOUT_KEY
from jiuwen.common.exception.base import JiuWenBaseException, WorkflowAbortException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import (
    logger,
    get_thread_session,
    set_thread_session,
    performance_logger,
    get_x_request_id,
    get_x_execution_id,
)
from jiuwen.context.history import ConversationHistory, ConversationMessage
from jiuwen.context.memory_engine.client.memory_proxy import MemoryProxy
from jiuwen.context.memory_engine.config.memory_ir_config import MemoryIrConfig
from jiuwen.orchestration.callbacks.utils import generate_tracer_id
from jiuwen.orchestration.common.perf_log import wf_performance_buffer
from jiuwen.orchestration.common.runtime_env import set_request_timeout
from jiuwen.orchestration.common.utils import wait_until_timeout, del_safely
from jiuwen.orchestration.flow.bpmn_workflow import BpmnWorkflow
from jiuwen.orchestration.flow.chat_manager import ChatManager
from jiuwen.orchestration.flow.constant import (
    WORKFLOW_API_CONFIGS,
    WORKFLOW_CHAT_MANAGER,
    WORKFLOW_EXECUTE_REQUESTS_HEADERS_NAME,
    WORKFLOW_EXECUTE_DEBUG_INFO,
    WORKFLOW_CHAT_HISTORY,
    WORKFLOW_DEFAULT_LOOP_MAX_NUM,
    TASK_EXECUTE_TIMEOUT,
    TASK_EXECUTE_TIMEOUT_ERROR_MESSAGE,
    WAIT_FOR_USER_INPUT_TIMEOUT_ERROR_MESSAGE,
    WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE,
    WORKFLOW_INSTANCE_DICT,
    WORKFLOW_EXECUTE_PROJECT_ID,
    WORKFLOW_EXECUTE_CONVERSATION_ID,
    WORKFLOW_EXECUTE_USER_ID,
    GLOBAL_CONFIG,
    WORKFLOW_GLOBAL_INTENTS,
    WORKFLOW_X_INVOKE_MODE,
    ENVIRONMENT_VARIABLES,
    MEMORY_VARIABLES,
    MEM_MAP,
    MEMORY_MESSAGE,
    ENABLE_MEMORY_RETRIEVE,
    USER_ID,
    APP_ID,
    REQUEST_VARIABLES,
)
from jiuwen.orchestration.flow.enum import ChatHistoryRole, NodeType, ExecutionStatus
from jiuwen.orchestration.flow.model.workflow_data_class import WorkflowInvokeOutput
from jiuwen.orchestration.flow.runtime_context import RuntimeContext
from jiuwen.orchestration.flow.state import (
    WorkflowState,
    WorkflowSpec,
    LazyWorkflowState,
    LAZY_WORKFLOW_STATE_TYPE_NAME,
    EXECUTED_WORKFLOW_STATE_TYPE_NAME,
    ExecutedWorkflowState,
)
from jiuwen.orchestration.flow.stream.base import StreamCode, StreamData
from jiuwen.serve.controllers.execution.open_utils import (
    cache_workflow_queue,
    async_ir_load,
)

# 多次使用的变量名以常量定义
TYPE = "type"
VALUE = "value"
WORKFLOW_LOOP_MAX_NUM = "WORKFLOW_LOOP_MAX_NUM"
CONTROLLER_MODE_SWITCH = "CONTROLLER_MODE_SWITCH"
CONTROLLER_MODE_JUMP = "CONTROLLER_MODE_JUMP"
_LLM_EXTRA_CONFIGS_KEY = "llm_extra_configs"
_PLUGIN_CONFIGS_KEY = "plugin_configs"
_X_AUTH_TOKEN_KEY = "X-Auth-Token"
_CUST_HEADERS = "cust_headers"
_PROJECT_ID = "project_id"
_SYS_WORKFLOW_CHAT_HISTORY_KEY = "conversationHistory"
_WORKFLOW_CHAT_HISTORY_KEY = "conversation_history"
_WORKFLOW_SYS_KEY = "sys"
_WORKFLOW_CONVERSATION_ID_KEY = "conversationId"
_GLOBAL_VARIABLES_KEY = "global_variables"
_WORKFLOW_ID_CAMEL = "workflowId"
_WORKFLOW_ID_SNAKE = "workflow_id"
_EXECUTION_ID = "execution_id"
_REQUEST_ID = "request_id"
_ANSWER = "answer"
_PLANNER_TIP_CONTENT = "tip_content"
_NODE_NAME = "node_name"
_RESULT_METADATA = "result_metadata"
_MESSAGE_OUTPUTS = "message_outputs"
_CARD_OUTPUTS = "card_outputs"
_GLOBAL_INTENTS_KEY = "global_intents"
_USER_FIELDS = "user_fields"

BJ_TZ = datetime.timezone(
    datetime.timedelta(hours=8),
    name="Asia/Beijing",
)
THRESHOLD_TO_CACHE_WORKFLOW_SKELETON = 1


class Workflow:
    """
    工作流执行实例

    该类用于表示一个工作流的执行实例，包含与工作流相关的属性和方法。
    """

    def __init__(self, **kwargs):
        """
        初始化Workflow实例。

        Args:
            **kwargs: 包含初始化参数的字典，仅包含 x_auth_token。

        Attributes:
            _ir: 内部资源对象，初始化为None。
            _bpmn_workflow_instance: BPMN工作流实例，初始化为None。
            parent_workflow_id: 父工作流ID，初始化为None。
            runtime_context: 运行时上下文，初始化为None。
            sub_workflow: 子工作流字典，初始化为空字典。
            _cur_tasks: 当前任务集合，初始化为空集合。
            stream_out_queue: 流输出队列，初始化为None。
            chat_manager: 聊天管理器对象，初始化为None。
            is_workflow_mode: 工作流模式标志，默认为True。
            is_sub_workflow: 子工作流标志，默认为False。
            _workflow_id: 工作流ID，初始化为None。
            _workflow_name: 工作流名称，初始化为None。
            _is_initialized: 初始化状态标志，默认为False。
            data: 数据字典，初始化为空字典。
        """
        # 成员变量定义
        self._ir = None
        self._bpmn_workflow_instance: Optional[BpmnWorkflow] = None
        self.parent_workflow_id = None
        self.runtime_context = None

        self.sub_workflow = {}
        self._cur_tasks = set()
        self.stream_out_queue = None
        self.chat_manager: Optional[ChatManager] = None
        self.is_workflow_mode = kwargs.get("is_workflow_mode", True)
        self.is_sub_workflow = kwargs.get("is_sub_workflow", False)
        self._workflow_id = None
        self._workflow_name = None
        self._is_initialized = False
        self.data = {}
        self._memory_proxy = None

    def __del__(self):
        try:
            if self._cur_tasks:
                logger.info(f"cur task del: {self._cur_tasks}")
                for task in self._cur_tasks:
                    task.cancel()
        except Exception as e:
            logger.error(f"cancel task failed: {e}")

    @staticmethod
    def _parse_task_node(component: dict, **kwargs):
        """解析规划节点"""
        configs = component.setdefault("configs", [])
        configs.append(
            {
                "name": "task_id",
                "type": "String",
                "value": component.get("id") or "",
            }
        )

    @staticmethod
    def _recover_runtime_context(
        workflow_state: ExecutedWorkflowState, chat_manager: ChatManager, **kwargs
    ) -> RuntimeContext:
        """
        将workflow_state.runtime_context中的信息读取出来到新的runtime_context
        """
        runtime_context = RuntimeContext()
        runtime_context.set(
            WORKFLOW_EXECUTE_DEBUG_INFO,
            workflow_state.runtime_context.get(WORKFLOW_EXECUTE_DEBUG_INFO, {}),
        )
        runtime_context.set(
            WORKFLOW_EXECUTE_PROJECT_ID,
            workflow_state.runtime_context.get(WORKFLOW_EXECUTE_PROJECT_ID, {}),
        )
        runtime_context.set(
            GLOBAL_CONFIG, workflow_state.runtime_context.get(GLOBAL_CONFIG, {})
        )
        runtime_context.set(
            WORKFLOW_EXECUTE_REQUESTS_HEADERS_NAME,
            {
                _X_AUTH_TOKEN_KEY: kwargs.get("x_auth_token"),
                _CUST_HEADERS: kwargs.get("cust_headers"),
            },
        )  # workflow执行中所需请求头信息
        runtime_context.set(WORKFLOW_CHAT_MANAGER, chat_manager)
        runtime_context.get(WORKFLOW_EXECUTE_DEBUG_INFO).update(
            {
                WORKFLOW_X_INVOKE_MODE: kwargs.get("cust_headers", {})
                .get("x-invoke-mode", "")
                .lower()
            }
        )
        runtime_context.set(
            REQUEST_VARIABLES, workflow_state.runtime_context.get(REQUEST_VARIABLES, {})
        )
        return runtime_context

    async def instantiate(
        self, data: Union[dict, WorkflowState, WorkflowSpec] = None, **kwargs
    ):
        """初始化workflow"""
        if self._is_initialized:
            return self
        init_start_time = time.perf_counter()
        is_from_last_state = False
        is_from_cached_workflow_spec = False
        if (
            isinstance(data, WorkflowState)
            and data.type == EXECUTED_WORKFLOW_STATE_TYPE_NAME
        ):
            # 如果传入WorkflowState类型，就恢复到上次执行状态
            await self._load_state(data.workflow_state, **kwargs)
            self._ir = data.workflow_state.bpmn_workflow_state.workflow_json
            is_from_last_state = True
        elif isinstance(data, WorkflowSpec):
            await self.init_from_spec(data, **kwargs)
            is_from_cached_workflow_spec = True
        elif isinstance(data, dict):
            # 缓存中无 WorkflowSpec，就用 IR 创建新实例
            await self._init(data, **kwargs)
            await self.cache_workflow_spec()
        else:
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_INIT_WRONG_TYPE_ERROR.code,
                message=StatusCode.WORKFLOW_INIT_WRONG_TYPE_ERROR.errmsg,
            )
        self._workflow_id = self._ir.get("workflowId")
        self._workflow_name = self._ir.get("workflowName")
        self._memory_proxy = self.create_memory_proxy()
        self.extend_init(**kwargs)
        init_end_time = time.perf_counter()
        init_duration = round((init_end_time - init_start_time) * 1000)
        conversation_id = kwargs.get("conversation_id")
        if conversation_id:
            if len(conversation_id) <= 4:
                masked_conversation_id = "****"
            else:
                masked_conversation_id = f"{conversation_id[:4]}***"
        else:
            masked_conversation_id = "None"
        performance_logger.info(
            f"conversation_id: {masked_conversation_id}"
            f"|workflow_init<data from last state = {is_from_last_state}, "
            f"is_from_cached_workflow_spec ={is_from_cached_workflow_spec} "
            f"workflowId ={self._workflow_id}>|{init_duration}"
        )
        wf_performance_buffer.info("workflow_init", init_duration, conversation_id)
        self._is_initialized = True
        return self

    def extend_init(self, **kwargs):
        """
        初始化扩展点。

        该方法用于在初始化时扩展功能，子类可以重写此方法以实现自定义初始化逻辑。

        Args:
            **kwargs: 关键字参数，用于传递初始化时所需的额外参数。

        Returns:
            无返回值。

        Raises:
            无特定异常。
        """
        pass

    def create_memory_proxy(self) -> MemoryProxy | None:
        """
        create memory proxy
        """
        memory_dict = self._ir.get("configs", {}).get("memory")
        if memory_dict is None:
            return None
        memory_config = MemoryIrConfig.from_config_dict(memory_dict)
        if memory_config is None or not memory_config.enable_memory:
            return None
        return MemoryProxy(memory_config)

    def extend_error_template(self, tmpl):
        """
        获取异常信息模板扩展点。

        该方法用于扩展或修改异常信息模板，子类可以重写此方法以自定义异常信息。

        Args:
            tmpl: 异常信息模板，通常为字符串类型。

        Returns:
            返回修改后的异常信息模板。

        Raises:
            无特定异常。
        """
        return tmpl

    async def init_from_spec(self, workflow_spec: WorkflowSpec, **kwargs):
        """
        从 WorkflowSpec 重建 Workflow 实例。
        """
        # 子工作流重建
        self._ir = workflow_spec.ir
        self.chat_manager = self._get_new_chat_manager()
        self.runtime_context = self._get_initial_runtime_context(**kwargs)
        self.sub_workflow = await self._async_init_sub_workflow(**kwargs)
        self.runtime_context.set(WORKFLOW_INSTANCE_DICT, self.sub_workflow)
        self._bpmn_workflow_instance = BpmnWorkflow()
        self._bpmn_workflow_instance.instantiate(
            data=workflow_spec, runtime_context=self.runtime_context
        )

    def get_workflow_id(self):
        """
        获取 IR 中的 workflow_id
        """
        return self._workflow_id

    def get_workflow_name(self):
        """
        获取 IR 中的 workflow_name
        """
        return self._workflow_name

    async def cache_workflow_spec(self):
        """
        将状态无关的 Worklflow 实例放入缓存。
        """
        # 仅已发布状态的workflow才缓存spec
        if not self._ir.get("is_published", False):
            return
        ir_path = self._ir.get("ir_path", "")
        components_num = len(self._ir.get("components", []))
        workflow_id = self._ir.get("workflowId")
        # components个数较少，不需要缓存
        if len(ir_path) == 0 or components_num <= THRESHOLD_TO_CACHE_WORKFLOW_SKELETON:
            return

        spec = WorkflowSpec(
            workflow_id=workflow_id,
            ir=self._ir,
            node_spec={
                node_id: node.node_spec
                for node_id, node in self._bpmn_workflow_instance.nodes.items()
            },
            bpmn_spec=self._bpmn_workflow_instance.bpmn_spec,
        )
        await cache_workflow_queue.aput(ir_path, spec)

    def recover_chat_manager(self):
        """
        Recover the attributes of ChatManager.
        """
        if hasattr(self.chat_manager, "_output_queue"):
            return
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.get_event_loop()
        self.chat_manager.recover_chat_manager(loop=loop)

    def get_workflow_execute_status(self) -> ExecutionStatus:
        """
        START：其他情况
        END：整个workflow执行完成（由bpmn控制）
        USER_INTERACT；workflow交互中断（手动控制stop_bpmn_flag）
        """
        if self._bpmn_workflow_instance:
            # workflow交互中断，跳出bpmn执行
            if self._bpmn_workflow_instance.stop_bpmn_flag:
                return ExecutionStatus.USER_INTERACT
            # workflow执行完成，结束bpmn执行
            if self._bpmn_workflow_instance.workflow.is_completed():
                return ExecutionStatus.END
            return ExecutionStatus.START
        return ExecutionStatus.START

    def get_state(self) -> WorkflowState:
        """获取中断workflow"""
        # 1. 获取BpmnInstanceState
        bpmn_instance_state = self._bpmn_workflow_instance.get_state()
        # 2. 获取每个sub_workflow的workflow_state
        sub_workflow_states = {
            node_id: sub_wf.get_state() for node_id, sub_wf in self.sub_workflow.items()
        }
        return WorkflowState(
            type=EXECUTED_WORKFLOW_STATE_TYPE_NAME,
            workflow_state=ExecutedWorkflowState(
                workflow_id=self._workflow_id,
                workflow_name=self._workflow_name,
                parent_workflow_id=self.parent_workflow_id,
                sub_workflow_states=sub_workflow_states,
                runtime_context={
                    WORKFLOW_EXECUTE_DEBUG_INFO: self.runtime_context.get(
                        WORKFLOW_EXECUTE_DEBUG_INFO, {}
                    ),
                    WORKFLOW_EXECUTE_PROJECT_ID: self.runtime_context.get(
                        WORKFLOW_EXECUTE_PROJECT_ID, {}
                    ),
                    GLOBAL_CONFIG: self.runtime_context.get(GLOBAL_CONFIG),
                    REQUEST_VARIABLES: self.runtime_context.get(REQUEST_VARIABLES, {}),
                },
                bpmn_workflow_state=bpmn_instance_state,
            ),
        )

    async def astream(self, query: str, params: dict):
        """
        对外暴露的流式执行接口，返回一个生成器
        """
        if not get_thread_session():
            set_thread_session(
                self.runtime_context.get(WORKFLOW_EXECUTE_DEBUG_INFO, {}).get(
                    WORKFLOW_EXECUTE_CONVERSATION_ID, ""
                )
            )
        return await self._arun(query, True, params)

    async def ainvoke(self, query: str, params):
        """
        对外暴露的阻塞式执行接口
        """
        execution_id = self._bpmn_workflow_instance.tracer.trace_id
        origin_output = await self._arun(query, False, params)
        if "code" in origin_output and "message" in origin_output:
            data = dict(
                error_code=origin_output.get("code"),
                error_message=origin_output.get("message"),
            )
        else:
            data = dict(
                answer=origin_output.get(_ANSWER),
                user_fields=origin_output.get(_USER_FIELDS),
                planner_node_name=origin_output.get(_RESULT_METADATA, {}).get(
                    _NODE_NAME
                ),
                planner_tip_content=origin_output.get(_RESULT_METADATA, {}).get(
                    _PLANNER_TIP_CONTENT
                ),
            )
        return WorkflowInvokeOutput(
            data=data,
            message_list=origin_output.get(_MESSAGE_OUTPUTS),
            card_list=origin_output.get(_CARD_OUTPUTS),
            execution_id=execution_id,
        )

    async def async_clean_up(self):
        """清理相关资源"""
        try:

            async def _do_clean_up():
                await self.chat_manager.aclear()
                if self._cur_tasks:
                    logger.info(f"cur task: {self._cur_tasks}")
                    for task in self._cur_tasks:
                        task.cancel()
                    await asyncio.gather(*self._cur_tasks, return_exceptions=True)
                self._cur_tasks.clear()

            timeout = os.getenv(WORKFLOW_TASK_CANCEL_TIMEOUT_KEY)
            if timeout is not None:
                try:
                    timeout = float(timeout)
                except Exception:
                    timeout = None
            await asyncio.wait_for(_do_clean_up(), timeout=timeout)
            if not self.parent_workflow_id:
                self.clear_bpmn_workflow_instance()
            logger.debug("Workflow (id=%s) clean up done.", id(self))
        except asyncio.TimeoutError:
            logger.error("workflow资源清理超时")
        except Exception as e:
            logger.error(
                "workflow资源清理失败，失败原因：{}".format(str(e)),
                simple_log="workflow资源清理失败",
            )
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_CLEAR_RESOURCES_ERROR_AFTER_EXECUTION.code,
                message=StatusCode.WORKFLOW_CLEAR_RESOURCES_ERROR_AFTER_EXECUTION.errmsg,
            ) from e

    def clean_up(self):
        """清理相关资源"""
        try:
            if not self.parent_workflow_id:
                self.clear_bpmn_workflow_instance()
            self.chat_manager.clear()
            self._cur_tasks.clear()
            logger.debug("Workflow (id=%s) clean up done.", id(self))
        except Exception as e:
            logger.error(
                "workflow资源清理失败，失败原因：{}".format(str(e)),
                simple_log="workflow资源清理失败",
            )
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_CLEAR_RESOURCES_ERROR_AFTER_EXECUTION.code,
                message=StatusCode.WORKFLOW_CLEAR_RESOURCES_ERROR_AFTER_EXECUTION.errmsg,
            ) from e

    def clear_bpmn_workflow_instance(self):
        """
        clear_bpmn_workflow_instance
        """
        del_safely(self, "_bpmn_workflow_instance")
        for _sub_workflow in self.sub_workflow.values():
            _sub_workflow.clear_bpmn_workflow_instance()

    def _get_new_chat_manager(self):
        """
        获取一个新的ChatManager实例
        """
        if self.is_workflow_mode or self.is_sub_workflow:
            loop = asyncio.get_event_loop()
        else:
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return ChatManager.create_chat_manager(loop=loop)

    async def _init(self, ir: dict, **kwargs):
        """
        Create workflow instance based on ir.
        """
        conversation_id = kwargs.get("conversation_id")
        start_time = time.perf_counter()
        self._ir = self._pre_handlers(copy.deepcopy(ir))  # IR预处理
        self.chat_manager = self._get_new_chat_manager()

        self.runtime_context = self._get_initial_runtime_context(**kwargs)
        init_runtime_context_end_time = time.perf_counter()
        init_runtime_context_duration = round(
            (init_runtime_context_end_time - start_time) * 1000
        )
        performance_logger.info(
            f"conversation_id: {conversation_id}"
            f"|init_runtime_context|{init_runtime_context_duration}",
            simple_log="init_runtime_context",
        )
        wf_performance_buffer.info(
            "workflow_init_runtime_context",
            init_runtime_context_duration,
            conversation_id,
        )

        self.sub_workflow = await self._async_init_sub_workflow(**kwargs)
        # workflow执行中所需请求头信息
        self.runtime_context.set(WORKFLOW_INSTANCE_DICT, self.sub_workflow)
        init_sub_workflow_end_time = time.perf_counter()
        init_sub_workflow_duration = round(
            (init_sub_workflow_end_time - init_runtime_context_end_time) * 1000
        )
        performance_logger.info(
            f"conversation_id: {conversation_id}|_init_sub_workflow"
            f"|{init_sub_workflow_duration}",
            simple_log="_init_sub_workflow",
        )
        wf_performance_buffer.info(
            "workflow_init_sub", init_sub_workflow_duration, conversation_id
        )

        get_chat_manager_end_time = time.perf_counter()
        get_chat_manager_duration = round(
            (get_chat_manager_end_time - init_sub_workflow_end_time) * 1000
        )
        performance_logger.info(
            f"conversation_id: {conversation_id}|get_chat_manager|{get_chat_manager_duration}",
            simple_log="get_chat_manager",
        )
        wf_performance_buffer.info(
            "workflow_init_chat_manager", get_chat_manager_duration, conversation_id
        )

        self._bpmn_workflow_instance = BpmnWorkflow()
        self._bpmn_workflow_instance.instantiate(
            data=self._ir,
            runtime_context=self.runtime_context,
            loop_max_num=int(
                os.environ.get(WORKFLOW_LOOP_MAX_NUM) or WORKFLOW_DEFAULT_LOOP_MAX_NUM
            ),
        )
        get_bpmn_workflow_end_time = time.perf_counter()
        get_bpmn_workflow_duration = round(
            (get_bpmn_workflow_end_time - get_chat_manager_end_time) * 1000
        )
        performance_logger.info(
            f"conversation_id: {conversation_id}|get_bpmn_workflow|{get_bpmn_workflow_duration}",
            simple_log="get_bpmn_workflow",
        )
        wf_performance_buffer.info(
            "workflow_init_bpmn", get_bpmn_workflow_duration, conversation_id
        )

    async def _load_state(self, workflow_state: ExecutedWorkflowState, **kwargs):
        """
        Recover workflow instance based on workflow_state.
        """
        # 1. 成员变量初始化
        self.chat_manager = self._get_new_chat_manager()
        self.runtime_context = self._recover_runtime_context(
            workflow_state=workflow_state, chat_manager=self.chat_manager, **kwargs
        )
        debug_info = self.runtime_context.get(WORKFLOW_EXECUTE_DEBUG_INFO, {})
        if _EXECUTION_ID not in debug_info:
            debug_info[_EXECUTION_ID] = generate_tracer_id()
        self.parent_workflow_id = workflow_state.parent_workflow_id
        # 2. 基于workflow state创建bpmn workflow instance
        self._bpmn_workflow_instance = BpmnWorkflow()
        self._bpmn_workflow_instance.instantiate(
            data=workflow_state.bpmn_workflow_state,
            runtime_context=self.runtime_context,
            loop_max_num=int(
                os.environ.get(WORKFLOW_LOOP_MAX_NUM) or WORKFLOW_DEFAULT_LOOP_MAX_NUM
            ),
        )
        # 3. 遍历sub_workflow_states字典，对其中每一个子workflow状态调用Workflow.__init__恢复实例，获得sub_workflow列表
        self.sub_workflow = {}
        for (
            sub_workflow_id,
            sub_workflow_state,
        ) in workflow_state.sub_workflow_states.items():
            self.sub_workflow[sub_workflow_id] = await self._recover_sub_workflow(
                sub_workflow_state, **kwargs
            )

        # 4. 成员变量赋值
        self.runtime_context.set(WORKFLOW_INSTANCE_DICT, self.sub_workflow)

    async def _recover_sub_workflow(self, sub_workflow_state: WorkflowState, **kwargs):
        if sub_workflow_state.type == LAZY_WORKFLOW_STATE_TYPE_NAME:
            state = sub_workflow_state.workflow_state
            return LazyWorkflow(
                parent_workflow_id=state.parent_workflow_id,
                workflow_id=state.workflow_id,
                workflow_name=state.workflow_name,
                comp_id=state.comp_id,
                ir_path=state.ir_path,
                runtime_context=self.runtime_context,
                **kwargs,
            )

        wf = Workflow(**kwargs)
        await wf.instantiate(data=sub_workflow_state, **kwargs)
        wf.stream_out_queue = asyncio.Queue()
        return wf

    async def _arun(self, query: str, stream_enable: bool, params):
        """
        执行入口函数
        参数：
            query(str):  用户输入
            params：
                conversationHistory(list):  端到端对话历史
                pluginConfigs(list): 插件运行时动态配置
                globalVariables(dict): 全局变量配置
                llmExtraConfigs(dict): 模型配置
                globalIntents(list): 全局意图
            stream_enable(bool): 是否开启流式
        返回值：
            非流式返回值：
            {
                answer(str): 运行结果
                tipContent: 正常输出外的tip信息
                nodeName: 与tipContent绑定的节点名
            }
            流式返回值：
                Generator
        """
        await self._update_runtime_context(
            params, query
        )  # 一个Workflow()对应一个runtime_context，每次都要改

        global_variables = params.get(_GLOBAL_VARIABLES_KEY, {})
        sys_args = global_variables.get(_WORKFLOW_SYS_KEY, {})
        utc_time = datetime.datetime.now(tz=datetime.timezone.utc)
        current_time = (utc_time + datetime.timedelta(hours=8)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        conversation_history = params.get(_WORKFLOW_CHAT_HISTORY_KEY, [])
        sys_conversation_history = sys_args.get(_SYS_WORKFLOW_CHAT_HISTORY_KEY, [])
        new_conversation_history = (
            sys_conversation_history
            if not conversation_history
            else conversation_history
        )
        sys_args.update(
            {
                "conversationHistory": new_conversation_history,
                "currentTime": current_time,
            }
        )
        global_variables.update(
            {
                "sys": sys_args,
                "conversationHistory": params.get(_WORKFLOW_CHAT_HISTORY_KEY, []),
            }
        )

        try:
            result = await self._achat(
                query=query,
                global_variables=global_variables,
                stream_enable=stream_enable,
            )
        except WorkflowAbortException as e:
            if self.parent_workflow_id:
                raise e
            # 对于主工作流，捕获异常后返回异常数据而不是重新抛出
            result = {
                "code": e.error_code,
                "message": e.message,
                **e.data,  # 将异常数据中的字段展开
            }

        if self.parent_workflow_id and isinstance(result, AsyncGenerator):
            # 子工作流在子线程中运行，惰性计算保留在该线程中运行完毕，数据用队列传出
            async for data in result:
                await self.stream_out_queue.put(data)
            return None
        return result

    async def _achat(
        self, query: str, global_variables: dict, stream_enable: bool = False
    ):
        """
        运行bpmn_workflow实例，返回处理后的最终执行结果
        @param query: 用户输入
        @param global_variables: 全局变量
        @param stream_enable: 是否流式调用的标识
        """
        self.chat_manager.set_finish(False)
        self._execute_bpmn_workflow(
            query=query, stream_enable=stream_enable, global_variables=global_variables
        )

        # 流式输出
        if stream_enable:
            output = self._process_streaming_output(self.chat_manager)
        # 非流式输出
        else:
            output = await self._get_output()
        return output

    def _execute_bpmn_workflow(
        self, query: str, stream_enable: bool, global_variables: dict
    ):
        """
        实例化bpmn_workflow对象，并进行调用
        """
        # 执行workflow

        if stream_enable:
            cur_task = asyncio.create_task(
                # 平台执行workflow使用流式
                self._bpmn_workflow_instance.astream(
                    {"query": query, **global_variables}
                )
            )
        else:
            cur_task = asyncio.create_task(
                # 平台执行workflow使用阻塞式
                self._bpmn_workflow_instance.ainvoke(
                    {"query": query, **global_variables}
                )
            )
        self._cur_tasks.add(cur_task)
        cur_task.add_done_callback(lambda t: self._task_done_callback(task=t))

    def _task_done_callback(self, task):
        """
        检查任务是否因异常而结束，是的话日志中打印调用栈信息
        @param task: 待检查的任务
        @return: None
        """
        exception = task.exception()
        self._cur_tasks.remove(task)
        if exception and self.chat_manager:
            import traceback

            traceback_info = "".join(
                traceback.format_exception(None, exception, exception.__traceback__)
            )
            logger.error(
                traceback_info, simple_log="workflow task_done_callback error."
            )
            # 处理异常
            cur_loop = self.chat_manager.get_loop()
            task_exception = task.exception()
            if not isinstance(task_exception, JiuWenBaseException):
                task_exception = JiuWenBaseException(
                    message=self.extend_error_template(
                        WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE
                    ).format(
                        StatusCode.WORKFLOW_EXECUTE_ERROR.code,
                        StatusCode.WORKFLOW_EXECUTE_ERROR.errmsg,
                    ),
                    error_code=StatusCode.WORKFLOW_EXECUTE_ERROR.code,
                )

            self.chat_manager.tasks.add(
                cur_loop.create_task(self.chat_manager.put_out(task_exception))
            )
            self.chat_manager.set_finish(True)

    async def _get_output(self):
        """
        对异步执行结果进行处理，主要完成以下处理：
        1、异常返回处理
        2、flow状态更新
        3、对话标志位刷新
        4、对话结束后的资源清理
        """
        # 执行过程中的JiuWenBaseException来自于components执行，信息需要以正常对话的方式返回
        output = await wait_until_timeout(
            self.chat_manager.get_out(),
            TASK_EXECUTE_TIMEOUT,
            self.extend_error_template(TASK_EXECUTE_TIMEOUT_ERROR_MESSAGE),
        )
        if isinstance(output, WorkflowAbortException):
            # 返回异常中携带的用户定义错误信息
            return {
                "code": output.error_code,
                "message": output.message,
                **output.data,  # 将异常数据中的字段展开
            }

        if isinstance(output, JiuWenBaseException):
            return dict(
                code=output.error_code,
                message=self.extend_error_template(
                    WORKFLOW_UNIFIED_ERROR_INFORMATION_UNSAFE
                ).format(output.error_code, output.message),
            )

        # 等待用户输入超时
        if output == WAIT_FOR_USER_INPUT_TIMEOUT_ERROR_MESSAGE:
            # 对话结束
            self.chat_manager.set_finish(True)

        # 非流式需要等待BPMN结束信号
        await wait_until_timeout(
            self.chat_manager.get_out(),
            TASK_EXECUTE_TIMEOUT,
            self.extend_error_template(TASK_EXECUTE_TIMEOUT_ERROR_MESSAGE),
        )

        return output

    async def _process_streaming_output(self, cur_chat_manager: ChatManager):
        # 如果有异常，bpmn_workflow._run_task()的异常处理会向chat_manager <异步> 地放入三条消息，先后顺序不一定
        #   1. _on_execution_error_debug_info()会封装一个【workflow_node_message】事件的StreamData放入chat_manager
        #   2. _pass_exception_info()会先放入一个封装【ERROR】事件的StreamData，再放入一个封装【FINISH】事件的StreamData
        # 最后，bpmn执行的回调函数发挥作用，
        #   3. 在_task_done_callback中还会把【JiuWenBaseException】放入chat_manager

        # 可能的顺序1：workflow_node_message(error), ERROR, FINISH, JiuWenBaseException
        # 可能的顺序2：ERROR, workflow_node_message(error), FINISH, JiuWenBaseException
        # 可能的顺序3：ERROR, FINISH, workflow_node_message(error), JiuWenBaseException
        # 能保证
        #   1. 【ERROR】在【FINISH】之前
        #   2. 【JiuWenBaseException】为这四条消息中的最后一条

        error_flag = False
        finish_msg = None
        while True:
            res = await wait_until_timeout(
                cur_chat_manager.get_out(),
                TASK_EXECUTE_TIMEOUT,
                self.extend_error_template(TASK_EXECUTE_TIMEOUT_ERROR_MESSAGE),
            )
            if isinstance(res, JiuWenBaseException) and error_flag:
                # 只有【JiuWenBaseException】不需要put_control，这个消息是直接put_out发送的，不是on_recv
                yield finish_msg
                break

            # 请求下一轮数据
            await cur_chat_manager.put_control("")

            if res.code == StreamCode.FINISH.value:
                # 延迟发送FINISH
                if not error_flag:
                    yield res
                    break
                finish_msg = res
                continue
            if res.code == StreamCode.MESSAGE_END.value:
                yield res
                # add message to conversation history and yield intermediate_message
                content = (
                    res.data.get("origin_answer")
                    if res.data.get("origin_answer", "")
                    else res.data.get("answer", "")
                )
                enable_history = res.data.get("enable_history", True)
                chat_history = self.runtime_context.get(WORKFLOW_CHAT_HISTORY)
                if content and enable_history:
                    chat_history.add(
                        ConversationMessage(
                            role=ChatHistoryRole.ASSISTANT.value, content=content
                        )
                    )
                yield self._create_intermediate_message(chat_history.get_all_messages())
                continue

            if res.code == StreamCode.ERROR.value:
                error_flag = True
                # 异常结束组件抛出的异常信息不同于jiuwen的异常信息，所以不需要error流式数据。
                if res.data.get("node_type", "") != NodeType.ERROR_END.value:
                    yield res
                continue
            yield res

    def _create_intermediate_message(self, intermediate_messages):
        return StreamData(
            code=StreamCode.CONTROLLER_INTERMEDIATE_MESSAGE.value,
            msg="intermediate message",
            data=dict(answer=intermediate_messages),
            execution_id=self._bpmn_workflow_instance.tracer.trace_id,
        )

    def _get_streaming_output(self):
        loop = self.chat_manager.get_loop()

        # 将异步生成器转换为同步生成器
        def run_async_gen():
            generator = self._process_streaming_output(self.chat_manager)
            while True:
                try:
                    item = loop.run_until_complete(generator.__anext__())
                    yield item
                except StopAsyncIteration:
                    break

        return run_async_gen()

    def _pre_handlers(self, ir_info: dict):
        """
        预处理原始IR
        """
        handlers = {
            "Task": self._parse_task_node,
        }
        for _, component in enumerate(ir_info.get("components", [])):
            node_type = component.get(TYPE, "")
            handler = handlers.get(node_type)
            if handler and callable(handler):
                handler(component=component)
        return ir_info

    async def _async_init_sub_workflow(self, **kwargs):
        """
        初始化子workflow
        kwargs: 使用x_auth_token字段
        """
        sub_workflows = {}
        parent_workflow_id = self._ir.get(_WORKFLOW_ID_CAMEL)
        for component in self._ir.get("components", []):
            if component.get("type") == NodeType.SUB_WORKFLOW.value:
                reference = component.get("configs", {}).get("reference", {})
                sub_workflow_id = reference.get("id", "")
                # 子workflowId不能等于父workflowId
                if parent_workflow_id == sub_workflow_id:
                    raise JiuWenBaseException(
                        error_code=StatusCode.SUB_WORKFLOW_INVALID_ID_ERROR.code,
                        message=StatusCode.SUB_WORKFLOW_INVALID_ID_ERROR.errmsg.format(
                            sub_workflow_id=sub_workflow_id
                        ),
                    )
                try:
                    kwargs.update({"is_sub_workflow": True})
                    workflow_name = component.get("name", "")
                    comp_id = component.get("id")
                    ref_path_key = reference.get("path", "")
                    sub_workflow_instance = LazyWorkflow(
                        parent_workflow_id,
                        sub_workflow_id,
                        workflow_name,
                        comp_id,
                        ref_path_key,
                        self.runtime_context,
                        **kwargs,
                    )

                except Exception as e:
                    logger.error("Constructing a sub workflow instance failed")
                    raise JiuWenBaseException(
                        error_code=StatusCode.SUB_WORKFLOW_CONSTRUCTION_ERROR.code,
                        message=StatusCode.SUB_WORKFLOW_CONSTRUCTION_ERROR.errmsg.format(
                            workflow_name=component.get("name", ""),
                            workflow_id=reference.get("id", ""),
                        ),
                    ) from e
                sub_workflows.update({component.get("id"): sub_workflow_instance})
        return sub_workflows

    def _get_initial_runtime_context(self, **kwargs) -> RuntimeContext:
        initial_runtime_context = RuntimeContext()
        initial_runtime_context.set(WORKFLOW_CHAT_MANAGER, self.chat_manager)
        workflow_execute_debug_info = kwargs.get(WORKFLOW_EXECUTE_DEBUG_INFO, {})
        workflow_execute_debug_info.update(
            {
                _WORKFLOW_ID_SNAKE: self._ir.get(_WORKFLOW_ID_CAMEL),
                WORKFLOW_EXECUTE_CONVERSATION_ID: kwargs.get("conversation_id"),
                WORKFLOW_EXECUTE_USER_ID: kwargs.get("user_id"),
                WORKFLOW_X_INVOKE_MODE: kwargs.get("cust_headers", {})
                .get("x-invoke-mode", "")
                .lower(),
            }
        )
        workflow_execute_debug_info[_EXECUTION_ID] = get_x_execution_id()
        workflow_execute_debug_info[_REQUEST_ID] = get_x_request_id()

        initial_runtime_context.set(
            WORKFLOW_EXECUTE_DEBUG_INFO, workflow_execute_debug_info
        )
        headers_got = {
            _X_AUTH_TOKEN_KEY: kwargs.get("x_auth_token"),
            _CUST_HEADERS: kwargs.get("cust_headers"),
        }
        initial_runtime_context.set(WORKFLOW_EXECUTE_REQUESTS_HEADERS_NAME, headers_got)
        project_id = kwargs.get(WORKFLOW_EXECUTE_PROJECT_ID, None)
        initial_runtime_context.set(
            WORKFLOW_EXECUTE_PROJECT_ID,
            project_id
            if project_id is not None
            else {_PROJECT_ID: kwargs.get("project_id")},
        )
        initial_runtime_context.set(GLOBAL_CONFIG, self._ir.get("configs", {}))
        return initial_runtime_context

    async def _update_runtime_context(self, params: dict, query: str):
        """
        params: orchestration_mgr.ExecutionParams
            _WORKFLOW_CHAT_HISTORY_KEY: 对话历史
            _PLUGIN_CONFIGS_KEY: 插件配置项
        """
        # 插件动态配置
        self.runtime_context.set(
            WORKFLOW_API_CONFIGS, params.get(_PLUGIN_CONFIGS_KEY, {}) or {}
        )

        # workflow端到端对话历史, 手动拼接query到最后
        sys_chat_history = (
            params.get(_GLOBAL_VARIABLES_KEY, {})
            .get(_WORKFLOW_SYS_KEY, {})
            .get(_SYS_WORKFLOW_CHAT_HISTORY_KEY, [])
        )

        old_chat_history = params.get(_WORKFLOW_CHAT_HISTORY_KEY)
        if old_chat_history:
            origin_chat_history = old_chat_history
        else:
            origin_chat_history = sys_chat_history

        if not params.get(CONTROLLER_MODE_SWITCH, False):
            origin_chat_history.append(
                dict(role=ChatHistoryRole.USER.value, content=query)
            )
        else:
            self.runtime_context.set(
                CONTROLLER_MODE_JUMP, params.get(CONTROLLER_MODE_JUMP, False)
            )
        self.runtime_context.set(
            WORKFLOW_CHAT_HISTORY, ConversationHistory(origin_chat_history)
        )
        self.runtime_context.set(
            WORKFLOW_GLOBAL_INTENTS, params.get(_GLOBAL_INTENTS_KEY) or []
        )
        self.runtime_context.set(
            ENVIRONMENT_VARIABLES, params.get(ENVIRONMENT_VARIABLES) or {}
        )
        self.runtime_context.set(MEMORY_VARIABLES, params.get(MEMORY_VARIABLES) or {})
        self.runtime_context.set(MEM_MAP, params.get(MEM_MAP) or {})

        enable_memory_retrieve = params.get("enable_memory_retrieve", False)
        user_id = params.get(_GLOBAL_VARIABLES_KEY, {}).get("userId", "")
        app_id = params.get("app_id", "")
        self.runtime_context.set(ENABLE_MEMORY_RETRIEVE, enable_memory_retrieve)
        self.runtime_context.set(USER_ID, user_id)
        self.runtime_context.set(APP_ID, app_id)

        # 只有请求中没有request_variables才使用runtime_context恢复的request_variables 优先级: 请求params > recovered_vars
        recovered_request_vars = self.runtime_context.get(REQUEST_VARIABLES, {})
        global_variables = params.get(_GLOBAL_VARIABLES_KEY, {})
        request_variables = {
            k: v
            for k, v in global_variables.items()
            if k
            not in (
                _WORKFLOW_CONVERSATION_ID_KEY,
                _WORKFLOW_SYS_KEY,
                _SYS_WORKFLOW_CHAT_HISTORY_KEY,
            )
        }
        final_session_vars = {**recovered_request_vars, **request_variables}
        self.runtime_context.set(REQUEST_VARIABLES, final_session_vars)

        if (
            isinstance(self._memory_proxy, MemoryProxy)
            and self._memory_proxy.enable_memory
        ):
            # Use memory_repo_id from params (multi-agent override) or IR,
            # not app_id, so that memory is retrieved from the correct repo.
            memory_repo_id = params.get("memory_repo_id", "") or (
                self._ir.get("configs", {}).get("memory", {}).get("memory_repo_id", "")
            )
            scope_id = memory_repo_id or app_id
            if enable_memory_retrieve and user_id != "" and scope_id != "":
                memory_message = await self._memory_proxy.get_related_memory_msg(
                    user_id=user_id, scope_id=scope_id, query=query
                )
                if memory_message is not None:
                    self.runtime_context.set(MEMORY_MESSAGE, memory_message)

        envs = self.runtime_context.get(ENVIRONMENT_VARIABLES)
        set_request_timeout(envs)


class LazyWorkflow:
    def __init__(
        self,
        parent_workflow_id: str,
        workflow_id: str,
        workflow_name: str,
        comp_id: str,
        ir_path: str,
        runtime_context: Union[dict, RuntimeContext] = None,
        **kwargs,
    ):
        self.parent_workflow_id = parent_workflow_id
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.comp_id = comp_id
        self.ir_path = ir_path
        self._instance = None  # 保存Workflow实例
        self._params = kwargs.copy()
        if isinstance(runtime_context, RuntimeContext):
            self._runtime_context = {
                WORKFLOW_EXECUTE_DEBUG_INFO: copy.deepcopy(
                    runtime_context.get(WORKFLOW_EXECUTE_DEBUG_INFO, None)
                ),
                WORKFLOW_EXECUTE_PROJECT_ID: copy.deepcopy(
                    runtime_context.get(WORKFLOW_EXECUTE_PROJECT_ID, None)
                ),
            }
        elif isinstance(runtime_context, dict):
            self._runtime_context = runtime_context.copy()
        else:
            self._runtime_context = {}
        self._params.update(self._runtime_context)

    async def instantiate(self, **kwargs) -> Workflow:
        """instantiate"""
        try:
            # 优先从缓存中读取 WorkflowSpec 重建
            sub_wf_spec = await cache_workflow_queue.aget(self.ir_path)
            if "is_sub_workflow" not in self._params:
                self._params["is_sub_workflow"] = self.parent_workflow_id is not None
            if sub_wf_spec is not None:
                sub_workflow_instance = await build_workflow(
                    data=sub_wf_spec, **self._params
                )
            else:
                # 缓存中找不到则使用 IR 构建
                sub_ir_data = await async_ir_load(self.ir_path)
                sub_workflow_instance = await build_workflow(
                    data=sub_ir_data, **self._params
                )
                await (
                    sub_workflow_instance.cache_workflow_spec()
                )  # 一旦用 IR 初始化即加入缓存

        except Exception as e:
            logger.error("Constructing a sub workflow instance failed")
            base_message = StatusCode.SUB_WORKFLOW_CONSTRUCTION_ERROR.errmsg.format(
                workflow_name=self.workflow_name, workflow_id=self.workflow_id
            )

            # 如果是 JiuWenBaseException，拼接错误码和错误信息
            if isinstance(e, JiuWenBaseException):
                extra_info = (
                    f" | caused by JiuWenBaseException[{e.error_code}]: {e.message}"
                )
            else:
                # 普通异常，直接拼接异常信息
                extra_info = f" | caused by Exception: {type(e).__name__}"

            raise JiuWenBaseException(
                error_code=StatusCode.SUB_WORKFLOW_CONSTRUCTION_ERROR.code,
                message=base_message + extra_info,
            ) from e

        sub_workflow_instance.parent_workflow_id = self.parent_workflow_id
        sub_workflow_instance.stream_out_queue = asyncio.Queue()
        self._instance = sub_workflow_instance
        return sub_workflow_instance

    def get_state(self):
        """获取中断state"""
        if (
            self._instance is not None
            and self._instance.get_workflow_execute_status() != ExecutionStatus.END
        ):
            return self._instance.get_state()
        return WorkflowState(
            type=LAZY_WORKFLOW_STATE_TYPE_NAME,
            workflow_state=LazyWorkflowState(
                parent_workflow_id=self.parent_workflow_id,
                workflow_id=self.workflow_id,
                workflow_name=self.workflow_name,
                comp_id=self.comp_id,
                ir_path=self.ir_path,
                runtime_context=self._runtime_context,
            ),
        )

    def clear_bpmn_workflow_instance(self):
        """clear bpmn workflow instance"""
        if self._instance:
            self._instance.clear_bpmn_workflow_instance()


async def build_workflow(
    data: Union[dict, WorkflowState, WorkflowSpec], **kwargs
) -> Workflow:
    """
    构建工作流实例。

    根据输入的数据类型，创建并初始化工作流实例。如果输入数据是WorkflowState类型且类型名为LAZY_WORKFLOW_STATE_TYPE_NAME，
    则创建LazyWorkflow实例。如果输入数据是字典类型，则从缓存中获取工作流规范并创建Workflow实例。

    Args:
        data (Union[dict, WorkflowState, WorkflowSpec]): 用于构建工作流的输入数据。
        **kwargs: 其他可选参数。

    Returns:
        Workflow: 返回初始化后的工作流实例。

    Raises:
        无

    """
    if isinstance(data, WorkflowState) and data.type == LAZY_WORKFLOW_STATE_TYPE_NAME:
        state = data.workflow_state
        lwf = LazyWorkflow(
            parent_workflow_id=state.parent_workflow_id,
            workflow_id=state.workflow_id,
            workflow_name=state.workflow_name,
            comp_id=state.comp_id,
            ir_path=state.ir_path,
            runtime_context=state.runtime_context,
            **kwargs,
        )
        return await lwf.instantiate()
    if isinstance(data, dict):
        cache_workflow_spec = await cache_workflow_queue.aget(data.get("ir_path", ""))
        if cache_workflow_spec:
            data = cache_workflow_spec
    wf = Workflow(**kwargs)
    await wf.instantiate(data=data, **kwargs)
    return wf


def sync_build_workflow(
    data: Union[dict, WorkflowState, WorkflowSpec], **kwargs
) -> Workflow:
    """sync build workflow"""
    return asyncio.new_event_loop().run_until_complete(build_workflow(data, **kwargs))
