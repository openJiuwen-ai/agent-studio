#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Union, Generator, Dict, Any, AsyncGenerator, Optional

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.utils.utils import format_exception_reason
from jiuwen.context.base import VARIABLE_NAME_KEY, VARIABLE_DEFAULT_KEY
from jiuwen.context.history import ConversationHistory
from jiuwen.controller.agent.base_agent import BaseAgent
from jiuwen.controller.agent.control_mode.control_factory import ControlFactory
from jiuwen.controller.common.config import AgentConfig
from jiuwen.controller.common.constants import WorkflowConstants
from jiuwen.controller.common.enum import RetCode
from jiuwen.controller.context_manager.context_manager import ContextManager
from jiuwen.controller.task_planner.planners.controller_planner import ControllerState
from jiuwen.controller.task_planner.planners.plan_execute_planner import (
    PlanExecuteState,
)
from jiuwen.controller.utils.utils import AgentUtils, WorkspaceUtils
from jiuwen.insight.manager import TraceManager, get_child_manager
from jiuwen.insight.utils import get_instance_info
from jiuwen.orchestration import Invokable
from jiuwen.serve.controllers.execution.manager import AsyncStateManager
from jiuwen.serve.controllers.execution.open_utils import serialize_object
from openjiuwen.core.sys_operation.cwd import init_cwd


class TaskInvokeStatus(Enum):
    """
    Enumeration class for task invoke status.

    Attributes:
       INIT (str): The initial status.
       SUCCESS (str): The success status.
       WAIT_USER_INPUT (str): The status indicating waiting for user input.
       FAILED (str): The failed status.
       UNKNOWN (str): The unknown status.
    """

    INIT = "init"
    SUCCESS = "success"
    WAIT_USER_INPUT = "wait_user_input"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class AgentState:
    workflow_states: list = field(
        default_factory=list
    )  # 未执行完的workflow的序列化实例, 序列化方法架设提供
    task_queue_state: Dict[str, Any] = field(default_factory=dict)  # 任务队列的状态
    controller_state: ControllerState = field(
        default_factory=ControllerState
    )  # 控制器状态，以task_id为键
    plan_execute_state: Optional[PlanExecuteState] = None  # PlanExecute 状态
    controller_global_variables: Dict[str, Any] = field(
        default_factory=dict
    )  # 控制器全局变量
    created_at: datetime = field(default_factory=datetime.now)


class Agent(BaseAgent):
    """
    new agent class
    """

    query_key_word = "query"
    result_key_word = "result"
    plan_prompt_key_word = "prompt_info"
    ret_code_key_word = "ret_code"
    _max_task_id_length = 32
    agent_mode = ""

    def __init__(self, config: AgentConfig = None):
        """初始化Agent实例"""
        if config is None:
            config = AgentConfig()

        super().__init__(config=config)

        self.context_manager = ContextManager(agent_config=config)

        self.control_mode = ControlFactory.create_control_mode(
            agent_config=config, context_manager=self.context_manager
        )
        self.workflows = config.workflows or []
        self.plugins = config.plugins or []
        self.mcps = []
        self.result = None
        self.task_id = config.task_id
        self.agent_id = config.agent_id
        self._invoke_status = TaskInvokeStatus.INIT

        # 保存 skill 配置
        self.skill_dir = config.skill_dir or ""
        self.skill_info = config.skill_info or []

    @classmethod
    def from_state(cls, agent_config: AgentConfig, agent_state: AgentState):
        """
        获取Agent状态，如果获取到，根据保存的状态和AgentConfig初始化Agent实例，否则直接根据AgentConfig初始化Agent实例

        Args:
            config: 包含必要参数的字典，包括model, plan_config, task_id和workflows

        Returns:
            Agent: 根据配置初始化的Agent实例
        """
        logger.info(
            f"task_id {agent_config.task_id} |agent_state from_state created at: {agent_state.created_at}"
        )
        agent = cls(config=agent_config)
        if agent_state is not None:
            agent.context_manager.load_state(agent_state=agent_state)
            agent.control_mode.task_planner.load_state(state=agent_state)
        return agent

    def get_control_mode(self):
        """
        获取控制模式
        Returns: plan_mode
        """
        return self.control_mode.plan_config.plan_mode

    def get_task_end(self):
        """
        获取任务状态
        Returns: task_end
        """
        return self.control_mode.task_end

    def clear_state(self):
        """
        清理Agent中不需要的内存
        """
        self.context_manager.clear_all()
        self.control_mode.task_planner.task_queue.clear_all_tasks()

    async def save_state(self, key):
        """
        保存AgentState，Workflow的序列化方法由Workflow提供

        Args:
            key: 状态存储的键名
        """
        planner_state = self.control_mode.task_planner.get_state()
        controller_state = planner_state
        plan_execute_state = None
        if isinstance(planner_state, PlanExecuteState):
            controller_state = None
            plan_execute_state = planner_state
        agent_state = AgentState(
            workflow_states=self.control_mode.get_interrupted_workflow_state(),
            task_queue_state=self.control_mode.task_planner.task_queue.get_state(),
            controller_state=controller_state,
            plan_execute_state=plan_execute_state,
            controller_global_variables=self.context_manager.get_global_variables(
                "controller_global_variables", {}
            ),
        )
        serialized_agent_state = serialize_object(agent_state)
        logger.info(
            f"task_id {self.task_id}| agent_state create at: {agent_state.created_at},"
            f" controller_state: {agent_state.controller_state}",
            simple_log="agent state saved successfully",
        )
        await AsyncStateManager().save_state(key, serialized_agent_state)

    async def get_state(self):
        """
        获取AgentState，Workflow的序列化方法由Workflow提供
        """
        planner_state = self.control_mode.task_planner.get_state()
        controller_state = planner_state
        plan_execute_state = None
        if isinstance(planner_state, PlanExecuteState):
            controller_state = None
            plan_execute_state = planner_state
        agent_state = AgentState(
            workflow_states=self.control_mode.get_interrupted_workflow_state(),
            task_queue_state=self.control_mode.task_planner.task_queue.get_state(),
            controller_state=controller_state,
            plan_execute_state=plan_execute_state,
            controller_global_variables=self.context_manager.get_global_variables(
                "controller_global_variables", {}
            ),
        )
        return agent_state

    async def load_state(self, state: AgentState):
        """
        根据AgentState覆盖ContextMemory中的消息队列和WorkSpace中的Workflow实例

        Args:
            state: Agent状态对象
            ir_data: IR数据，用于恢复工作流实例
        """
        self.context_manager.load_state(agent_state=state)
        self.control_mode.task_planner.load_state(state=state)

    async def prepare_execution(self, inputs, kwargs):
        """
        准备执行环境，处理输入并设置上下文

        Args:
            inputs: 用户输入，可以是字符串或字典
            kwargs: 额外参数

        Returns:
            Tuple: (查询文本, 提示信息, 运行时上下文, 追踪管理器)
        """
        runtime_context = kwargs.get("runtime_context")

        # 初始化聊天历史
        self._initialize_chat_history(runtime_context)

        # 传递记忆使用请求级参数
        params = runtime_context.agent_workflow_context.get(
            WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, {}
        )
        self.context_manager.set_memory_request_params(
            memory_app_id=params.get("app_id", ""),
            memory_enable_user_profile=params.get("enable_memory_retrieve", False),
        )

        # 处理输入
        query, prompt_info = AgentUtils.process_input(
            inputs, self.query_key_word, self.plan_prompt_key_word
        )

        # 根据模式处理特定逻辑
        trace_manager = await self._handle_mode_specific_logic(runtime_context, kwargs)

        return query, prompt_info, runtime_context, trace_manager

    def update_controller_global_variables(self, runtime_context):
        """
        Controller模式下全局变量写入workflow_req_params

        Args:
            runtime_context: 上下文
        """
        global_variables = runtime_context.agent_workflow_context.get(
            "workflow_req_params", {}
        ).get("global_variables", {})
        logger.info(
            f"received global_variables: {global_variables}",
            simple_log="global_variables saved successfully",
        )
        controller_global_vars = self.context_manager.get_global_variables(
            "controller_global_variables"
        )
        if controller_global_vars:
            # 遍历controller_global_variables中的每个键值对
            for key, value in controller_global_vars.items():
                # 只有当global_variables中该key不存在，或者值为None或空字符串时，才使用controller的值
                if (
                    key not in global_variables
                    or global_variables[key] is None
                    or global_variables[key] == ""
                ):
                    global_variables[key] = value

            logger.info(
                f"update_controller_global_variables global variables updated: {controller_global_vars}",
                simple_log="update_controller_global_variables global variables updated",
            )

    async def get_tools(self, query, kwargs):
        """
        根据查询和配置获取工具

        Args:
            query: 用户查询
            kwargs: 额外参数

        Returns:
            Tuple: (plugins, workflows)
        """
        # 生成工具 - 返回plugins和workflows
        plugins, workflows, mcps = await WorkspaceUtils.gen_tools(
            query,
            self.plugins,
            self.workflows,
            self.mcps,
            agent_id=self.agent_id,
            **kwargs,
        )

        # 处理工具开关
        tool_switch_dict = kwargs.get("tool_switch_dict")
        if tool_switch_dict:
            plugins, workflows = WorkspaceUtils.update_tool_switch(
                plugins, workflows, tool_switch_dict
            )

        return plugins, workflows, mcps


    async def invoke(self, inputs, *, session=None, **kwargs):
        """
        invoke agent

        Args:
            inputs: 用户输入，可以是字符串或字典#
            **kwargs: 额外参数

        Returns:
            执行结果
        """
        if session is not None:
            kwargs["session"] = session
        raise NotImplementedError()

    async def stream(
        self, inputs: Union[dict, str], *, session=None, **kwargs
    ) -> AsyncGenerator:
        if session is not None:
            kwargs["session"] = session
        async for item in self.astream(inputs, **kwargs):
            yield item

    async def astream(
        self, inputs: Union[dict, str], *, session=None, **kwargs
    ) -> AsyncGenerator:
        if session is not None:
            kwargs["session"] = session
        """
        Execute the planning assistance engine to execute the input instruction and output the result as stream type.

        Args:
            inputs: User input instruction (dict or string)
            **kwargs: 额外参数

        Returns:
            流式输出迭代器
        """
        # 准备执行环境
        (
            query,
            prompt_info,
            runtime_context,
            trace_manager,
        ) = await self.prepare_execution(inputs, kwargs)

        # 获取工具
        plugins, workflows, mcps = await self.get_tools(query, kwargs)
        plugins, skill_ctx = await self._inject_skills_if_needed(runtime_context, plugins)

        # 构建流式参数
        stream_params = self._build_stream_params(
            query,
            prompt_info,
            plugins,
            workflows,
            mcps,
            trace_manager,
            runtime_context,
            kwargs,
            skill_context=skill_ctx,
        )

        original_template = self._patch_system_prompt(skill_ctx.prompt_suffix)
        try:
            async for item in self._execute_stream_by_mode(
                stream_params, trace_manager
            ):
                yield item
        except Exception as e:
            raise JiuWenBaseException(
                StatusCode.AGENT_UPDATE_PLUGIN_WITH_TYPE_ERROR.code,
                f"controller agent astream error. {format_exception_reason(e)}",
            ) from e
        finally:
            self._restore_system_prompt(skill_ctx.prompt_suffix, original_template)

    def update_plugins(self, plugins: list) -> None:
        """
        更新Agent的插件列表

        Args:
            plugins: 新的插件列表
        """
        if plugins is None:
            self.plugins = []
        elif isinstance(plugins, list):
            from jiuwen.extension.wrapper.tool_wrapper import ToolWrapper

            invalid_plugins = [
                p for p in plugins if not isinstance(p, (Invokable, ToolWrapper))
            ]
            if invalid_plugins:
                raise JiuWenBaseException(
                    StatusCode.AGENT_UPDATE_PLUGIN_WITH_TYPE_ERROR.code,
                    StatusCode.AGENT_UPDATE_PLUGIN_WITH_TYPE_ERROR.errmsg.format(
                        type(invalid_plugins[0])
                    ),
                )
            self.plugins = plugins
        else:
            raise JiuWenBaseException(
                StatusCode.AGENT_UPDATE_PLUGIN_WITH_TYPE_ERROR.code,
                StatusCode.AGENT_UPDATE_PLUGIN_WITH_TYPE_ERROR.errmsg.format(
                    type(plugins)
                ),
            )

    def update_mcps(self, mcps: list) -> None:
        """
        更新Agent的mcp列表

        Args:
            mcps: 新的mcp列表
        """
        if mcps is None:
            self.mcps = []
        elif isinstance(mcps, list):
            invalid_mcps = [p for p in mcps if not isinstance(p, Invokable)]
            if invalid_mcps:
                raise JiuWenBaseException(
                    StatusCode.AGENT_UPDATE_PLUGIN_WITH_TYPE_ERROR.code,
                    StatusCode.AGENT_UPDATE_PLUGIN_WITH_TYPE_ERROR.errmsg.format(
                        type(invalid_mcps[0])
                    ),
                )
            self.mcps = mcps
        else:
            raise JiuWenBaseException(
                StatusCode.AGENT_UPDATE_PLUGIN_WITH_TYPE_ERROR.code,
                StatusCode.AGENT_UPDATE_PLUGIN_WITH_TYPE_ERROR.errmsg.format(
                    type(mcps)
                ),
            )

    async def _iterate_stream_planner_res(
        self, yield_res: Generator, trace_manager: TraceManager
    ):
        """
        迭代处理流式规划结果

        Args:
            yield_res: 从规划器获取的生成器
            trace_manager: 跟踪管理器
        """
        async for item in yield_res:
            if isinstance(item, dict):
                if item.get(self.ret_code_key_word, "") == RetCode.SUCCESS:  # 正常执行
                    execute_res = {"result": item.get("result", "")}
                    self.result = execute_res.get(self.result_key_word)
                elif item.get(self.ret_code_key_word, "") in [
                    RetCode.FUNC_CALL_GEN,
                    RetCode.API_EXEC_RESULT,
                    RetCode.API_EXCEPTION,
                    RetCode.CONT_OPT_RESULT,
                    RetCode.UX_SIGNAL,
                    RetCode.STREAM_OUTPUT_LLM,
                    RetCode.STREAM_REFLECTION,
                    RetCode.INTERMEDIATE_MESSAGE,
                    RetCode.STREAM_THINK_LLM,
                ]:
                    # 流式返回function call生成工具或执行结果、异常报错，还有内容优选的结果，还有对前端的控制信号，还有流式输出大模型的生成结果
                    yield item
                elif item.get(self.ret_code_key_word, "") == RetCode.FAILED:  # 执行报错
                    res = item.get(self.result_key_word, "")
                    if isinstance(res, dict):
                        msg = res.get("message", "Unknown error")
                        code = res.get("code", -1)
                        err_msg = f"Planning assistance engine failed to plan or execute: {msg}"
                        error_code = code if code is not None else -1
                    else:
                        err_msg = "Planning assistance engine failed to plan or execute"
                        error_code = -1

                    err = ValueError(err_msg)
                    await trace_manager.on_chain_error(err)

                    yield JiuWenBaseException(error_code=error_code, message=err_msg)
                else:
                    err = ValueError("Unsupported plan_states_code.")
                    await trace_manager.on_chain_error(err)
                    raise err

    def _initialize_chat_history(self, runtime_context):
        """初始化聊天历史到上下文管理器"""
        chat_history = (
            runtime_context.agent_workflow_context.get(
                "workflow_chat_history", ConversationHistory()
            )
        ).get_all_messages()
        self.context_manager.engine.add_messages(chat_history)

    async def _handle_mode_specific_logic(self, runtime_context, kwargs):
        """根据计划模式处理特定逻辑"""
        if self._is_controller_mode():
            self.update_controller_global_variables(runtime_context)
        # React 模式的特定处理
        if self._is_react_mode():
            await self._handle_react_mode_variables(runtime_context)
        return await self._setup_trace_manager(kwargs)

    async def _handle_react_mode_variables(self, runtime_context):
        """
        处理 React 模式的变量初始化和更新
        """
        # 1. 更新 Agent 输入变量（从请求的 globalVariables）
        if runtime_context and hasattr(runtime_context, "agent_workflow_context"):
            req_params = runtime_context.agent_workflow_context.get(
                WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, {}
            )
            global_variables = req_params.get("global_variables", {})
            self._update_agent_input_variables(global_variables)

        # 2. 加载记忆变量
        await self._load_memory_variables()

    def _update_agent_input_variables(self, global_variables: dict):
        """
        从请求的 globalVariables 部分更新 Agent 输入变量（支持嵌套）
        仅更新 agent_inputs 中已存在的键（包括嵌套键），不新增字段
        """
        if not global_variables:
            return

        context_manager = self.control_mode.context_manager
        agent_inputs = context_manager.get_global_variables("agent_inputs")

        if agent_inputs is None:
            return

        # 执行嵌套部分更新（仅对已存在的路径）
        updated = self._partial_update_dict(agent_inputs, global_variables)

        if updated:
            context_manager.set_global_variables("agent_inputs", agent_inputs)
            logger.info(f"task_id: {self.task_id}| Updated agent_inputs from request")

    def _partial_update_dict(self, target: dict, updates: dict) -> bool:
        """
        递归地对 target 字典进行部分更新（仅更新已存在的键）
        :param target: 原始字典（会被原地修改）
        :param updates: 要更新的字段（可能嵌套）
        :return: 是否发生了更新
        """
        updated = False
        for key, value in updates.items():
            if key not in target:
                continue  # 不新增字段，跳过不存在的键

            if isinstance(value, dict) and isinstance(target[key], dict):
                # 递归进入嵌套字典
                if self._partial_update_dict(target[key], value):
                    updated = True
            else:
                # 叶子节点：直接替换值（允许类型变化）
                target[key] = value
                updated = True

        return updated

    async def _load_memory_variables(self):
        """
        加载记忆变量到 ContextManager
        复用 ContextEngine.search_memory_all_variables 方法
        """
        context_manager = self.control_mode.context_manager
        if not context_manager.engine.conf.enable_memory:
            return

        memory_vars = await context_manager.get_memory_variables_dict() or {}
        # 遍历配置中定义的变量，匹配并拼接结果
        for var in self.context_manager.engine.conf.mem_variables:
            name = var.get(VARIABLE_NAME_KEY)
            if not name:
                continue

            # 从一次性获取的字典中取值，若无则用默认值
            var_value = memory_vars.get(name, "")
            default_value = var.get(VARIABLE_DEFAULT_KEY, "")
            if not var_value and default_value:
                memory_vars[name] = default_value

        context_manager.set_global_variables("memory_variables", memory_vars)

        logger.info(
            f"task_id: {self.task_id}| Loaded memory: {list(memory_vars.keys())}"
        )

    def _is_controller_mode(self):
        """检查是否为Controller模式"""
        return self.control_mode.plan_config.plan_mode == "Controller"

    def _is_react_mode(self):
        """检查是否为 React 模式"""
        return self.control_mode.plan_config.plan_mode == "ReAct"

    def _is_tool_use_mode(self):
        """检查是否为 ToolUse 模式"""
        return self.control_mode.plan_config.plan_mode == "ToolUse"

    async def _setup_trace_manager(self, kwargs):
        """设置并初始化追踪管理器"""
        trace_manager = TraceManager.generate_manager(
            kwargs.pop("trace_handlers", None),
            get_instance_info(
                self,
                blacklist=[
                    "results",
                    "memory_inputs",
                    "memory",
                    "flows",
                    "workflow_dict",
                    "workflows",
                ],
            ),
            session=kwargs.pop("session", None),
        )
        await trace_manager.on_chain_start(kwargs.get("inputs"))  # 使用原始inputs
        return trace_manager

    def _build_stream_params(
        self,
        query,
        prompt_info,
        plugins,
        workflows,
        mcps,
        trace_manager,
        runtime_context,
        kwargs,
        skill_context=None,
    ):
        """构建流式执行参数"""
        from jiuwen.controller.common.config import SkillInjectionContext

        return {
            "query": query,
            "prompt_info": prompt_info,
            "plugins": plugins,
            "workflows": workflows,
            "trace_handlers": get_child_manager(trace_manager)
            if trace_manager
            else None,
            "session": kwargs.get("session"),
            "runtime_context": runtime_context,
            "contexts": kwargs.get("contexts"),
            "multimodal_image": kwargs.get("multimodal_image"),
            "request_params": kwargs.get("request_params"),
            "mcps": mcps,
            "skill_context": skill_context or SkillInjectionContext.empty(),
        }

    async def _execute_stream_by_mode(self, stream_params, trace_manager):
        """根据不同模式执行流式处理"""
        yield_res = self.control_mode.stream(**stream_params)
        plan_mode = self.control_mode.plan_config.plan_mode

        if plan_mode == "Controller":
            async for item in self._handle_controller_mode_stream(yield_res):
                yield item
        elif plan_mode == "ReAct":
            async for item in self._handle_react_mode_stream(yield_res, trace_manager):
                yield item
        elif plan_mode == "ToolUse":
            async for item in self._handle_tooluse_mode_stream(
                yield_res, trace_manager
            ):
                yield item
        else:
            async for item in self._handle_default_mode_stream(yield_res):
                yield item

    async def _handle_controller_mode_stream(self, yield_res):
        """处理Controller模式的流式输出"""
        async for item in yield_res:
            yield item

    async def _handle_react_mode_stream(self, yield_res, trace_manager):
        """处理ReAct模式的流式输出"""
        async for item in self._iterate_stream_planner_res(yield_res, trace_manager):
            yield item
        if trace_manager:
            await trace_manager.on_chain_end(self.result)
        yield self.result

    async def _handle_tooluse_mode_stream(self, yield_res, trace_manager):
        """处理ToolUse模式的流式输出"""
        async for item in self._iterate_stream_planner_res(yield_res, trace_manager):
            yield item
        if trace_manager:
            await trace_manager.on_chain_end(self.result)
        yield self.result

    async def _handle_default_mode_stream(self, yield_res):
        """处理默认模式的流式输出"""
        async for item in yield_res:
            yield item

    async def _inject_skills_if_needed(self, runtime_context, plugins):
        """根据计划模式决定是否进行动态技能注入，返回 (plugins, SkillInjectionContext)

        如果 skill 文件下载失败，将错误信息注入到 prompt_suffix 中告知模型，
        确保模型能感知 skill 配置异常，而非静默跳过后让模型尝试读取不存在的文件。
        """
        from jiuwen.controller.common.config import SkillInjectionContext

        plan_mode = self.control_mode.plan_config.plan_mode
        if plan_mode in ("ReAct", "PlanExecute"):
            plugins_augmented, skill_ctx = self._apply_runtime_skill_injection(runtime_context, plugins)
            download_ok = await self._prepare_skill_files_async(skill_ctx.work_dir or "")
            if not download_ok and skill_ctx.prompt_suffix:
                # skill下载失败但提示词已构建：将错误信息注入到提示词中，
                # 让模型知道 skill 文件不可用，避免模型尝试读取不存在的文件
                error_hint = (
                    "\n\n[WARNING] Skill file download failed. "
                    "The skill files referenced above may not be available on disk. "
                    "Please inform the user that skill configuration is broken and needs to be fixed."
                )
                skill_ctx = SkillInjectionContext(
                    prompt_suffix=skill_ctx.prompt_suffix + error_hint,
                    tool_names=skill_ctx.tool_names,
                    tool_refs=skill_ctx.tool_refs,
                    work_dir=skill_ctx.work_dir,
                )
                logger.error(
                    f"Skill download failed for agent {self.agent_id}. "
                    f"Error hint injected into system prompt. "
                    f"Check OBS configuration and skill file availability."
                )
            return plugins_augmented, skill_ctx
        return plugins, SkillInjectionContext.empty()

    def _patch_system_prompt(self, skills_prompt_suffix):
        """临时覆盖系统提示词，仅对本次请求生效。返回原始模板用于恢复。"""
        if not skills_prompt_suffix:
            return None
        import copy
        from jiuwen.prompt import TemplateManager
        from jiuwen.prompt.index.template_store import Template

        task_id = self.control_mode.plan_config.task_id
        tm = TemplateManager()
        original_template = tm.get(task_id)
        if original_template and original_template.content:
            patched_content = copy.deepcopy(original_template.content)
            for msg in patched_content:
                if msg.get("role") == "system":
                    msg["content"] = (
                        (msg.get("content", "") or "") + "\n\n" + skills_prompt_suffix
                    )
                    break
            tm.register(Template(name=task_id, content=patched_content), force=True)
        return original_template

    @staticmethod
    def _restore_system_prompt(skills_prompt_suffix, original_template):
        """恢复被 _patch_system_prompt 修改的系统提示词"""
        if skills_prompt_suffix and original_template is not None:
            from jiuwen.prompt import TemplateManager

            tm = TemplateManager()
            tm.register(original_template, force=True)

    def _apply_runtime_skill_injection(self, runtime_context, plugins: list) -> tuple:
        """
        在每次 astream 调用时，从 runtime_context.sys_operation_card（SysOperationCard）动态创建
        SysOperation，构建 sysop 工具并合并到 plugins（返回新列表，不修改 self.plugins）；
        同时从 agent_config 的 skill_dir / skill_info 构造提示词后缀。

        当 runtime_context.sys_operation_card 为 None 时直接跳过，零开销。

        Returns:
            (augmented_plugins, SkillInjectionContext)
        """
        from jiuwen.controller.common.config import SkillInjectionContext

        sys_operation_card = getattr(runtime_context, "sys_operation_card", None)
        if sys_operation_card is None:
            return plugins, SkillInjectionContext.empty()

        from openjiuwen.core.sys_operation import SysOperationCard
        from jiuwen.sys_operation.sys_operation_plugin import build_sysop_tools

        if not isinstance(sys_operation_card, SysOperationCard):
            sys_operation_card = SysOperationCard(**sys_operation_card)

        from openjiuwen.core.runner import Runner

        # sandbox_root 是 List[str]，init_cwd 和 skill 路径拼接都只用"主工作目录"（取第一个元素）
        primary_work_dir = ""
        if sys_operation_card.work_config:
            sandbox_roots = sys_operation_card.work_config.sandbox_root or []
            if sandbox_roots:
                primary_work_dir = sandbox_roots[0] or ""

        init_cwd(primary_work_dir)

        add_result = Runner.resource_mgr.add_sys_operation(sys_operation_card, tag=self.agent_id)
        if not add_result.is_ok() and "resource already exist" in str(add_result):
            logger.info(
                f"sys_operation resource already registered for agent {self.agent_id}, "
                f"card_id={sys_operation_card.id}"
            )
        sys_operation = Runner.resource_mgr.get_sys_operation(
            sys_operation_card.id, tag=self.agent_id
        )

        # sys_operation = SysOperation(sys_operation_card)
        extra_tools = build_sysop_tools(sys_operation)
        augmented_plugins = list(plugins) + extra_tools

        return augmented_plugins, SkillInjectionContext(
            prompt_suffix=self._build_skills_prompt(primary_work_dir),
            tool_names={getattr(t, "name", "") for t in extra_tools} - {""},
            tool_refs={id(t) for t in extra_tools},
            work_dir=primary_work_dir,
        )

    def _build_skills_prompt(self, work_dir: str = "") -> str:
        """
        从 agent_config 中的 skill_dir / skill_info 构建 skill 提示词。
        参考开源 SkillUtil.get_skill_prompt 实现。

        当 local 模式下 work_dir 非空时，将 work_dir 拼接到 skill 的目录路径上，
        使 Agent 能够通过绝对路径访问 skill 文件。

        Args:
            work_dir: 工作目录（local 模式下的绝对路径前缀，为空时不拼接）

        Returns:
            拼接后的 skill 提示词字符串（为空时返回空字符串）
        """
        if not self.skill_info:
            return ""

        import posixpath

        system_prompt = (
            "You are an agent equipped with various skills to solve problems.\n"
            "Before attempting any task, read the relevant skill document (SKILL.md) "
            "using read_file and follow its workflow.\n"
        )

        skills_info = []
        for index, skill in enumerate(self.skill_info):
            name = skill.get("name", "")
            description = skill.get("description", "")
            skill_directory = (
                posixpath.join(self.skill_dir, name) if self.skill_dir else name
            )
            if work_dir:
                skill_directory = posixpath.join(work_dir, skill_directory)
            skills_info.append(
                f"{index}.Skill name: {name}; "
                f"Skill description: {description}; "
                f"Skill directory file path: {skill_directory}"
            )

        skill_text = (
            "\nTo help you better complete tasks, the following skill knowledge is equipped:\n"
            + "\n".join(skills_info)
            + "\n"
            "You can use the read_file tool to read the corresponding SKILL.md file to obtain the relevant skill.\n"
        )
        return system_prompt + "\n" + skill_text

    async def _prepare_skill_files_async(self, work_dir: str) -> bool:
        """
        在 agent 执行前下载并解压 skill zip 文件到本地工作目录，
        使 read_file 工具能够读取 SKILL.md 文件。

        使用 download_to_file 流式下载，比 get_content（先加载到内存再写入）更高效可靠。

        Args:
            work_dir: 本地工作目录路径

        Returns:
            True: 所有 skill 文件下载成功或已存在
            False: 至少一个 skill 下载失败（错误已记录到日志）
        """
        import os
        import zipfile

        logger.info(
            f"[SkillDownload] Starting skill file preparation. "
            f"work_dir='{work_dir}', skill_info count={len(self.skill_info) if self.skill_info else 0}, "
            f"skill_dir='{self.skill_dir}', skill_info={self.skill_info}"
        )

        # Skill 文件存储路径解析（优先级：本地路径 > 环境变量映射）：
        # - 生产环境：work_dir（如 /opt/tmp/agent）由 Dockerfile 预创建，路径已存在，直接使用
        # - 开发环境：本地不存在容器路径，通过 SKILL_STORAGE_DIR 环境变量指定本地存储目录
        original_work_dir = work_dir  # 保留原始值用于日志

        if os.path.exists(work_dir):
            # 优先级1：路径已存在 → 直接使用（生产容器或本地已有该目录）
            logger.info(f"[SkillDownload] work_dir '{work_dir}' exists locally, using it directly.")
        else:
            # 路径不存在（开发环境）或为空 → 回退到 SKILL_STORAGE_DIR 环境变量
            from agent_runtime.common.config import settings
            skill_storage_dir = settings.skill_storage.skill_storage_dir
            if skill_storage_dir:
                # 优先级2：环境变量提供了替代路径
                work_dir = skill_storage_dir
                logger.info(
                    f"[SkillDownload] original_work_dir '{original_work_dir}' does not exist locally, "
                    f"falling back to SKILL_STORAGE_DIR: '{work_dir}'"
                )
                # 确保替代路径本身存在
                if not os.path.exists(work_dir):
                    logger.error(
                        f"[SkillDownload] SKILL_STORAGE_DIR '{work_dir}' does not exist locally. "
                        f"Please create this directory manually. "
                        f"Skill file download will be skipped."
                    )
                    return False
            else:
                # 无环境变量兜底：无法确定 skill 文件存储路径
                logger.error(
                    f"[SkillDownload] work_dir '{original_work_dir}' does not exist locally and "
                    f"SKILL_STORAGE_DIR env is not set. In production, the Dockerfile should "
                    f"pre-create this directory. In development, please set SKILL_STORAGE_DIR "
                    f"to a local directory for skill file storage, e.g. "
                    f"SKILL_STORAGE_DIR=windows or linux path"
                    f"Skill file download will be skipped."
                )
                return False

        logger.info(f"[SkillDownload] Before OBS config check, about to import env_constants")

        # 检查 OBS 环境变量配置
        try:
            from jiuwen.common.configs.env_constants import DATASOURCE_OBS_BUCKET_KEY
            logger.info(f"[SkillDownload] After import env_constants")
        except Exception as e:
            logger.error(f"[SkillDownload] Failed to import env_constants: {e}")
            import traceback
            logger.error(f"[SkillDownload] Import traceback: {traceback.format_exc()}")
            return False

        # 直接使用环境变量名称
        obs_bucket = os.environ.get(DATASOURCE_OBS_BUCKET_KEY, "")
        obs_server = os.environ.get("DATASOURCE_OBS_SERVER", "")
        obs_ak = os.environ.get("DATASOURCE_OBS_AK", "")
        obs_sk = os.environ.get("DATASOURCE_OBS_SK", "")
        logger.info(
            f"[SkillDownload] OBS config check: "
            f"bucket='{obs_bucket}', server='{obs_server}', "
            f"DATASOURCE_OBS_AK={'set' if obs_ak else 'NOT SET'}, "
            f"DATASOURCE_OBS_SK={'set' if obs_sk else 'NOT SET'}"
        )

        if not work_dir or not self.skill_info or not self.skill_dir:
            logger.warning(
                f"[SkillDownload] Skipped: work_dir='{work_dir}', "
                f"skill_info={'provided' if self.skill_info else 'None'}, "
                f"skill_dir='{self.skill_dir}'"
            )
            return False

        skill_local_path_prefix = os.path.join(work_dir, self.skill_dir)
        logger.info(f"[SkillDownload] Attempting to create skill directory: {skill_local_path_prefix}")

        # 确保 skill 子目录存在
        try:
            os.makedirs(skill_local_path_prefix, exist_ok=True)
            logger.info(f"[SkillDownload] Directory created/exists: {skill_local_path_prefix}")
        except Exception as e:
            logger.error(f"[SkillDownload] Failed to create directory {skill_local_path_prefix}: {e}")
            return False

        from storage import get_storage_provider

        all_success = True
        for skill in self.skill_info:
            skill_name = skill.get("name")
            skill_path = skill.get("skill_path")

            logger.info(f"[SkillDownload] Processing skill: name='{skill_name}', path='{skill_path}'")

            if not skill_name or not skill_path:
                logger.error(f"Skill missing name or path: {skill}. Skill config is invalid.")
                all_success = False
                continue

            # 检查 SKILL.md 是否已存在，避免重复下载
            skill_dir_local = os.path.join(skill_local_path_prefix, skill_name)
            skill_md_path = os.path.join(skill_dir_local, "SKILL.md")
            if os.path.isfile(skill_md_path):
                logger.info(f"Skill {skill_name} already exists locally at {skill_md_path}, skip download")
                continue

            # 构建 zip 本地保存路径
            local_zip_path = os.path.join(skill_local_path_prefix, f"{skill_name}.zip")

            try:
                logger.info(f"Downloading skill {skill_name} from OBS path {skill_path} to {local_zip_path}")
                provider = get_storage_provider()
                await provider.download_to_file(object_key=skill_path, local_path=local_zip_path)

                # 解压 zip 到 skill 目录
                with zipfile.ZipFile(local_zip_path, "r") as zip_ref:
                    for member in zip_ref.infolist():
                        member.filename = member.filename.replace("\\", "/")
                        zip_ref.extract(member, skill_local_path_prefix)

                # 解压后删除 zip 文件
                try:
                    os.remove(local_zip_path)
                except Exception as e:
                    logger.warning(f"Failed to delete zip file {local_zip_path}: {e}")

                # 校验 SKILL.md 是否存在
                if not os.path.isfile(skill_md_path):
                    logger.error(
                        f"Skill {skill_name} downloaded and extracted, but SKILL.md not found at {skill_md_path}. "
                        f"Skill zip package may not contain SKILL.md."
                    )
                    all_success = False
                else:
                    logger.info(f"Successfully downloaded and extracted skill: {skill_name}")

            except Exception as e:
                logger.error(
                    f"Failed to download/extract skill {skill_name} from OBS path {skill_path}: {e}. "
                    f"Agent will not be able to read SKILL.md for this skill."
                )
                all_success = False

        return all_success
