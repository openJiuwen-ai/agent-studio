#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
PlanExecute 控制模式

职责：
- 继承 BaseMode，实现 stream() 和 invoke() 方法
- 管理任务执行的整体流程
- 输出 PE Agent 专属的 SSE 事件（scene_match, plan_end, step_start, step_end, task_complete）
"""

import json
import time
import uuid
from collections.abc import AsyncGenerator
from typing import List, Tuple, Dict

from jiuwen.common.log.base import logger
from jiuwen.context.history import ConversationHistory
from jiuwen.controller.agent.control_mode.base_mode import BaseMode
from jiuwen.controller.common.config import StreamRequest
from jiuwen.controller.common.constants import WorkflowConstants
from jiuwen.controller.common.enum import WorkflowType
from jiuwen.controller.common.message import Message
from jiuwen.controller.common.message_type import MessageType, MessageSubType
from jiuwen.controller.common.task import Task
from jiuwen.controller.common.task_type import TaskType, TaskSubType
from jiuwen.controller.task_planner.planners.plan_execute_planner import (
    SceneMatchEvent,
    PlanEndEvent,
)
from jiuwen.controller.task_planner.planning_modules.plan_tracker import (
    StepStatus,
    ExecutionPlan,
    PlanStep,
)
from jiuwen.controller.utils.utils import MessageConverter, ToolFormatter
from jiuwen.orchestration.flow.stream.base import StreamData, StreamCode



class PlanExecuteMode(BaseMode):
    """
    PlanExecute 控制模式

    实现动态规划逻辑：场景匹配 -> 任务规划 -> 逐步执行
    """

    def __init__(self, **kwargs):
        """初始化 PlanExecute 控制模式"""
        super(PlanExecuteMode, self).__init__(**kwargs)
        self.terminate = False
        self._interrupted_by_workflow = False
        self._workflow_completed = False  # 标记工作流是否已完成（用于跳过 LLM 判断）
        self._last_workflow_result = ""  # 保存工作流执行结果
        self._skill_context = None
        self._final_content = None

    def __call__(self, **kwargs):
        """兼容性方法，实际调用 invoke"""
        return self.invoke(**kwargs)

    def invoke(self, **kwargs):
        """
        同步调用（不推荐使用，PlanExecute 模式建议使用流式）

        Returns:
            执行结果
        """
        logger.warning("PlanExecute mode should use stream() instead of invoke()")
        return {
            "ret_code": "FAILED",
            "result": "PlanExecute mode only supports streaming",
        }

    async def stream(self, **kwargs) -> AsyncGenerator:
        """
        流式调用 PlanExecute 控制模式

        Args:
            **kwargs: 包含 query, runtime_context 等参数

        Yields:
            StreamData: 流式事件数据
        """
        # 初始化状态变量（不会抛出异常）
        self.terminate = False
        self._interrupted_by_workflow = False
        self._workflow_completed = False
        self._last_workflow_result = ""
        self._final_content = None
        self._current_round_msg_start_idx = self._get_message_count()
        # 初始化任务级别的工具失败状态
        self._tool_failure_count = {}  # {tool_name: consecutive_failure_count}
        self._current_step_tool_errors = []  # 当前步骤的工具错误列表
        from jiuwen.controller.common.config import SkillInjectionContext

        skill_ctx = kwargs.get("skill_context") or SkillInjectionContext.empty()
        self._skill_context = skill_ctx
        if getattr(self, "task_planner", None) is not None:
            self.task_planner.skill_context = skill_ctx
        # 记录开始时间用于统计
        self._plan_start_time = time.time()

        try:
            # 更新 plugins（从 Agent 传入的运行时 plugins）
            if kwargs.get("plugins"):
                self.plugins = kwargs["plugins"]
                # 同步更新 task_planner 的 plugins
                if hasattr(self, "task_planner") and self.task_planner:
                    self.task_planner.plugins = kwargs["plugins"]
                    self.task_planner.skill_context = skill_ctx

            # 创建流式请求对象
            request = StreamRequest(**kwargs)

            # 保存当前请求上下文，便于工具执行时使用
            self._current_query = request.query
            self._runtime_context = request.runtime_context
            self._workflow_req_params = {}
            self._conversation_id = None
            if request.runtime_context and hasattr(
                request.runtime_context, "agent_workflow_context"
            ):
                self._conversation_id = getattr(
                    request.runtime_context, "conversation_id", None
                )
                self._workflow_req_params = (
                    request.runtime_context.agent_workflow_context.get(
                        WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, {}
                    )
                )
                # 同步到上下文全局变量，供工作流执行模块使用
                self.context_manager.set_global_variables(
                    WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, self._workflow_req_params
                )

            # 创建初始用户输入消息
            runtime_data = {
                "task_id": self.task_id,
                "prompt_info": request.prompt_info,
                "plugins": request.plugins,
                "workflows": request.workflows,
                "contexts": request.contexts,
                "runtime_context": request.runtime_context,
                "multimodal_image": request.multimodal_image,
                "trace_handlers": request.trace_handlers,
            }

            message = MessageConverter.create_user_input_message(
                request.query, runtime_data
            )

            # 执行流式任务循环
            async for item in self._stream_task_loop(message):
                yield item

            # 每轮请求结束时返回 intermediate_message（用于保存对话历史以便下一轮恢复）
            yield self._create_intermediate_stream_data({})

            # 发送控制消息给 Agent Group
            if self.terminate and self._interrupted_by_workflow:
                # ask_user 或 workflow blocked 中断 → AgentGroup 保留 PE Agent 中断状态，等待下一轮对话
                yield self._create_interrupt_stream_data()
            else:
                # 正常完成，任务结束
                yield self._create_task_end_stream_data()

        except Exception as e:
            error_msg = f"task_id: {self.task_id}| PlanExecute 模式执行失败: {e}"
            logger.error(error_msg)
            yield StreamData(
                code=StreamCode.ERROR.value,
                msg="PlanExecute execution failed",
                data={"error": error_msg},
                execution_id=self.task_id,
            )

    async def _stream_task_loop(self, message: Message) -> AsyncGenerator:
        """
        执行任务循环

        Args:
            message: 初始用户消息

        Yields:
            StreamData: 流式事件
        """
        # 若已有未完成计划，直接继续执行，不重新规划
        if (
            self.task_planner.plan_tracker.plan
            and not self.task_planner.plan_tracker.is_completed()
        ):
            if message.message_type == MessageType.USER_INPUT:
                self.context_manager.add_user_message(message.content)
            async for step_event in self._execute_steps(
                self.task_planner.plan_tracker.plan
            ):
                yield step_event
                if self.terminate:
                    break
            return
        # 调用规划器的 stream 方法
        async for item in self.task_planner.stream(message):
            # 处理不同类型的事件
            if isinstance(item, SceneMatchEvent):
                # 场景匹配事件
                yield self._create_scene_match_stream_data(item)
            elif isinstance(item, PlanEndEvent):
                # 任务规划完成事件
                yield self._create_plan_end_stream_data(item)

                # 开始逐步执行
                async for step_event in self._execute_steps(item.plan):
                    yield step_event
                if self.terminate:
                    break
            else:
                # 其他类型的流式输出
                yield item
            if self.terminate:
                break

    async def _execute_steps(self, plan: ExecutionPlan) -> AsyncGenerator:
        """执行计划中的步骤"""
        self.task_planner.plan_tracker.init_plan(plan)
        self._step_exec_ctx = {
            "hint_builder": self.task_planner.hint_builder,
            "filtered_tools": self._get_filtered_tools(plan),
            "max_iterations": getattr(self.plan_config, "max_iterations", 50),
            "plan": plan,
        }
        self._temp_messages_start_idx = self._get_message_count()
        self._all_step_results = []

        async for event in self._iterate_steps():
            if isinstance(event, StreamData):
                self._all_step_results.append(event)
            yield event

        if not self.terminate:
            await self._finalize_plan_execution()
            final_data = self._final_content

            # 先发送 task_complete 事件和基础统计数据
            yield self._create_task_complete_stream_data(plan)
            yield self._create_statistic_data_stream_data()
            # 如果有最终汇总数据，生成汇总数据
            if final_data:
                yield self._create_summary_response_stream_data(final_data)
        # 任务被中途终止时，发送完整的结束事件序列和执行详情 。
        else:
            yield self._create_task_complete_stream_data(plan)
            yield self._create_statistic_data_stream_data()
            latest_msg = self.context_manager.get_latest_assistant_message()
            summary_content = latest_msg.content if latest_msg and latest_msg.content else "任务执行完成"
            yield self._create_summary_response_stream_data(summary_content)

    async def _iterate_steps(self) -> AsyncGenerator:
        """迭代执行所有步骤"""
        ctx = self._step_exec_ctx
        iteration_count = 0

        while (
            not self.task_planner.plan_tracker.is_completed()
            and iteration_count < ctx["max_iterations"]
        ):
            iteration_count += 1
            if self.terminate:
                break

            current_step = self.task_planner.plan_tracker.get_current_step()
            if not current_step:
                break

            yield self._create_step_start_stream_data(
                current_step, len(ctx["plan"].steps)
            )

            async for item in self._execute_single_step(current_step, ctx):
                if isinstance(item, tuple) and len(item) == 2:
                    pass  # 内部状态信号，吞掉不往外传
                else:
                    yield item  # 中间流式事件，实时yield

            # 无论事件是否提前终止 生成step_end事件 step_start和step_end成对出现
            yield self._create_step_end_stream_data(current_step)

            if self.terminate:
                break

    async def _execute_single_step(self, step: PlanStep, ctx: dict) -> AsyncGenerator:
        """执行单个步骤，yield流式事件，最后汇总结果通过step.result返回"""
        result_content = ""
        step_done = False
        max_iterations = 5
        step_iteration = 0
        # last_error_content 、 consecutive_same_error_count 、 max_same_error_retries 用于死循环检测
        last_error_content = None
        consecutive_same_error_count = 0
        max_same_error_retries = 3
        # 工具切换时重置迭代计数器
        last_tool_name = None
        
        while not step_done:
            step_iteration += 1
            if self.terminate:
                break

            if step.interrupted_workflow_name and step_iteration == 1:
                llm_result = self._build_workflow_resume_call(step)
            else:
                hint_message = self._build_step_hint(step_iteration, ctx)
                self._log_step_iteration(step, step_iteration, hint_message)
                llm_result = await self._call_llm_with_hint(
                    hint_message, ctx["filtered_tools"]
                )

            async for item in self._process_llm_result(
                llm_result, step, step_iteration, ctx["plan"]
            ):
                if isinstance(item, tuple) and len(item) == 2:
                    step_done, result_content = item
                else:
                    yield item

            if step_done:
                break

            # 工具切换检测：当LLM调用了不同的工具时，重置迭代计数器
            if not step_done and llm_result.get("has_tool_calls"):
                current_tool_names = [tc.get("name", "") for tc in llm_result.get("tool_calls", [])]
                current_tool_name = current_tool_names[0] if current_tool_names else None
                if current_tool_name and current_tool_name != last_tool_name:
                    logger.info(
                        f"task_id: {self.task_id}| Step {step.step_idx} tool switched from "
                        f"'{last_tool_name}' to '{current_tool_name}', resetting iteration counter"
                    )
                    step_iteration = 0
                    last_tool_name = current_tool_name
                elif current_tool_name:
                    last_tool_name = current_tool_name
                
                # 如果切换到的工具之前已经连续失败3次，给出警告
                broken_tools = {k for k, v in self._tool_failure_count.items() if v >= 3}
                if current_tool_name and current_tool_name in broken_tools:
                    failure_count = self._tool_failure_count[current_tool_name]
                    logger.warning(
                        f"task_id: {self.task_id}| Tool '{current_tool_name}' "
                        f"failed {failure_count} times, temporarily unavailable"
                    )

            if not step_done and result_content:
                error_key = self._extract_error_signature(result_content)
                if error_key and error_key == last_error_content:
                    consecutive_same_error_count += 1
                    if consecutive_same_error_count >= max_same_error_retries:
                        logger.warning(
                            f"task_id: {self.task_id}| Step {step.step_idx} "
                            f"same error repeated {consecutive_same_error_count} times, "
                            f"stopping tool retry. Error: {error_key[:200]}"
                        )
                        # 不终止整个任务，只停止当前工具的重试
                        # 将错误信息写入context，让模型在下一轮迭代中能看到并决定下一步
                        error_notice = f"工具连续报错{consecutive_same_error_count}次，已停止重试。最后错误：{result_content}"
                        self.context_manager.add_function_message(
                            name=last_tool_name or "unknown",
                            intent=last_tool_name or "unknown",
                            content=error_notice,
                            tool_call_id="dead_loop_detection",
                        )
                        # 重置计数器，让模型有机会尝试其他工具
                        consecutive_same_error_count = 0
                        last_error_content = None
                        step_iteration = 0
                        last_tool_name = None
                else:
                    last_error_content = error_key
                    consecutive_same_error_count = 1
            
            if step_iteration == max_iterations:
                last_iteration_had_tool_call = llm_result.get("has_tool_calls", False)
                if last_iteration_had_tool_call:
                    logger.info(
                        f"task_id: {self.task_id}| Step {step.step_idx} iteration {step_iteration} "
                        f"completed with tool call, adding extra iteration to process result"
                    )
                    step_iteration = max_iterations + 1
                    hint_message = self._build_step_hint(step_iteration, ctx)
                    self._log_step_iteration(step, step_iteration, hint_message)
                    llm_result = await self._call_llm_with_hint(
                        hint_message, ctx["filtered_tools"]
                    )
                    
                    async for item in self._process_llm_result(
                        llm_result, step, step_iteration, ctx["plan"]
                    ):
                        if isinstance(item, tuple) and len(item) == 2:
                            step_done, result_content = item
                        else:
                            yield item
                    
                    if step_done:
                        break

    def _extract_error_signature(self, content: str) -> str:
        """提取错误信息的特征签名，用于判断是否为重复出现的相同错误"""
        if not content:
            return None
        import re as re_module
        patterns = [
            r"NameError:\s*name\s+'[^']+'\s+is\s+not\s+defined",
            r"SyntaxError:\s*.*",
            r"TypeError:\s*.*",
            r"ValueError:\s*.*",
            r"ImportError:\s*.*",
            r"exit_code:\s*\d+",
            r"stderr:\s*.*",
        ]
        for pattern in patterns:
            match = re_module.search(pattern, content)
            if match:
                return match.group(0)[:200]
        return content[:200] if len(content) > 10 else None

    def _build_workflow_resume_call(self, step: PlanStep) -> dict:
        """工作流中断恢复时，直接构造 tool call 结果（跳过 LLM 调用）"""
        workflow_name = step.interrupted_workflow_name
        step.interrupted_workflow_name = None

        tool_call_id = str(uuid.uuid4())
        content = f"继续执行工作流 {workflow_name}"
        query = self._current_query or step.description

        func_call = {
            "name": workflow_name,
            "arguments": json.dumps({"query": query}, ensure_ascii=False),
            "tool_call_id": tool_call_id,
        }
        self.context_manager.add_assistant_message(content, workflow_name, func_call)

        tool_calls = [
            {
                "name": workflow_name,
                "arguments": {"query": query},
                "tool_call_id": tool_call_id,
            }
        ]

        logger.info(
            f"task_id: {self.task_id}| Step {step.step_idx} "
            f"resuming workflow '{workflow_name}' directly (skipping LLM)",
            simple_log=f"task_id: {self.task_id}| Step {step.step_idx} resuming workflow directly",
        )

        return {"content": content, "has_tool_calls": True, "tool_calls": tool_calls}

    def _build_step_hint(self, step_iteration: int, ctx: dict) -> str:
        """构建步骤hint消息"""
        if step_iteration == 1:
            return ctx["hint_builder"].build_hint_start_step(ctx["plan"])
        
        # 检查是否有工具失败
        tool_errors = getattr(self, "_current_step_tool_errors", [])
        if tool_errors:
            return self._build_hint_with_tool_error(ctx, tool_errors)
        
        return ctx["hint_builder"].build_hint_step_in_progress(ctx["plan"])

    def _build_hint_with_tool_error(self, ctx: dict, tool_errors: list) -> str:
        """构建带有工具错误提示的 hint"""
        plan = ctx["plan"]
        current_step = plan.steps[plan.current_step_idx - 1]
        
        # 构建错误信息
        error_parts = []
        for err in tool_errors:
            count = self._tool_failure_count.get(err["tool"], 0)
            error_parts.append(f"- {err['tool']}: {err['error']} (已连续失败{count}次)")
        error_summary = "\n".join(error_parts)
        
        # 构建可用工具列表提示（排除连续失败3次的）
        broken_tools = {k for k, v in self._tool_failure_count.items() if v >= 3}
        broken_tools_hint = ""
        if broken_tools:
            broken_tools_hint = f"\n注意：以下工具已连续失败3次，暂时不可用：{', '.join(broken_tools)}"
        
        # 通过 hint_builder 构建步骤状态信息
        steps_text = ctx["hint_builder"].build_steps_text(plan, mark_in_progress=True)
        
        hint_template = f"""当前执行进度：
{steps_text}

当前正在执行第{plan.current_step_idx}步：{current_step.step_name}，{current_step.description}

上一步工具执行失败：
{error_summary}
{broken_tools_hint}

请选择以下操作之一：
1. 调整参数后重试（如果失败次数<3）
2. 使用其他工具完成相同功能
3. 使用代码编写方式直接实现

完成后必须输出 [STEP_DONE]"""
        
        return hint_template

    def _log_step_iteration(self, step: PlanStep, iteration: int, hint: str):
        """记录步骤迭代日志"""
        step_log = (
            f"task_id: {self.task_id}| Step {step.step_idx} iteration {iteration}"
        )
        logger.info(f"{step_log}, hint: {hint[:100]}...", simple_log=step_log)

    async def _process_llm_result(
        self, llm_result: dict, step: PlanStep, step_iteration: int, plan: ExecutionPlan
    ) -> AsyncGenerator:
        """处理LLM响应结果，yield流式事件，最后yield完成状态"""
        if llm_result.get("has_tool_calls"):
            # 透传工具调用的所有yield（包括流式事件和最终状态）
            async for item in self._handle_tool_calls(llm_result, step, plan):
                yield item
        else:
            result = self._handle_no_tool_calls(llm_result, step, step_iteration)
            # 如果是用户提问场景，先yield提问消息给前端
            if result[0] and self._interrupted_by_workflow:
                content = llm_result.get("content", "")
                question = self._extract_question_content(content)
                for event in self._yield_question_stream(question):
                    yield event
            yield result

    async def _handle_tool_calls(
        self, llm_result: dict, step: PlanStep, plan: ExecutionPlan
    ) -> AsyncGenerator:
        """处理带工具调用的LLM响应，yield流式事件，最后yield完成状态"""
        self._workflow_completed = False
        self._last_workflow_result = ""
        self._current_query = step.description
        tool_calls = llm_result.get("tool_calls", [])
        self._inject_query_to_workflow_calls(tool_calls)

        # 收集工具执行结果，使用字典跟踪每个工具的状态
        tool_execution_results = {}  # {tool_name: {"success": bool, "error": str}}
        tool_execution_errors = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "unknown")
            tool_execution_results[tool_name] = {"success": False, "error": None}
            
            async for execute_result in self._execute_tool_call(tool_call, plan, step):
                # 检查是否是 api_exec_data 类型的结果
                if isinstance(execute_result, StreamData):
                    data = execute_result.data or {}
                    answer = data.get("answer", {})
                    if isinstance(answer, dict):
                        error_code = answer.get("error_code")
                        result_data = answer.get("result", {})
                        if isinstance(result_data, dict):
                            stderr = result_data.get("stderr", "")
                            exit_code = result_data.get("exit_code", 0)
                            
                            # 判断工具是否成功：error_code == 0 且 exit_code == 0（或者没有exit_code字段）
                            is_success = (error_code == 0) and (exit_code == 0 or result_data.get("exit_code") is None)
                            # 判断工具是否失败：有错误码且非0，或者有exit_code且非0且有stderr
                            is_failed = (error_code != 0) or (exit_code != 0 and stderr)
                            
                            if is_failed:
                                # 工具执行失败
                                error_msg = stderr or str(answer)
                                tool_execution_results[tool_name] = {
                                    "success": False, 
                                    "error": error_msg
                                }
                                if tool_name not in [e["tool"] for e in tool_execution_errors]:
                                    tool_execution_errors.append({
                                        "tool": tool_name,
                                        "error": error_msg,
                                        "result": result_data
                                    })
                                # 更新失败计数
                                self._tool_failure_count[tool_name] = \
                                    self._tool_failure_count.get(tool_name, 0) + 1
                            elif is_success:
                                # 工具执行成功，清零失败计数
                                self._tool_failure_count[tool_name] = 0
                                tool_execution_results[tool_name] = {"success": True, "error": None}
                yield execute_result
            
            if self.terminate:
                break

        # 记录当前步骤的错误，供 hint 构建使用
        self._current_step_tool_errors = tool_execution_errors

        content = llm_result.get("content", "")
        if self.terminate and self._interrupted_by_workflow:
            # 工作流提问器中断：不标记步骤完成，保持当前步骤以便恢复时注入继续执行该工作流
            final_result = (False, content or self._last_workflow_result or "")
        elif content and self._is_step_completed_by_llm(content, step):
            # 出口1：LLM 明确标记步骤完成
            final_result = self._mark_step_done(step, content)
        elif content and self._is_asking_user_input(content):
            # 出口2：LLM 需要向用户提问，中断任务
            self._handle_user_question(step, content)
            question = self._extract_question_content(content)
            for event in self._yield_question_stream(question):
                yield event
            final_result = (True, content)
        else:
            # 出口3：继续下一次迭代 比如执行完workflow和plugin
            # workflow中断已经self.terminate break出去了
            final_result = (False, content)

        # 最后yield完成状态
        yield final_result

    def _handle_no_tool_calls(
        self, llm_result: dict, step: PlanStep, step_iteration: int
    ) -> tuple:
        """处理无工具调用的LLM响应"""
        content = llm_result.get("content", "")

        if self._is_step_completed_by_llm(content, step):
            return self._mark_step_done(step, content)

        if self._is_asking_user_input(content):
            self._handle_user_question(step, content)
            return True, content

        logger.warning(
            f"task_id: {self.task_id}| Step {step.step_idx} "
            f"LLM output without tool_calls and not marking complete"
        )

        return False, content

    def _mark_step_done(self, step: PlanStep, content: str) -> tuple:
        """标记步骤完成，优先使用工具执行结果作为step.result"""
        # 优先从工具执行结果中提取有意义的summary
        tool_summary = self._generate_step_summary(step)
        if tool_summary and tool_summary != f"{step.step_name}完成":
            result = tool_summary
        else:
            result = self._extract_step_result(content)
        self.task_planner.plan_tracker.mark_step_completed(step.step_idx, result=result)
        self._log_step_completed(step, result)
        return True, result

    def _mark_step_completed_with_log(self, step: PlanStep, result: str, source: str):
        """标记步骤完成并记录日志"""
        self.task_planner.plan_tracker.mark_step_completed(step.step_idx, result=result)
        step_log = f"task_id: {self.task_id}| Step {step.step_idx}"
        logger.info(
            f"{step_log} completed by {source}: {result}",
            simple_log=f"{step_log} completed by {source}",
        )

    def _log_step_completed(self, step: PlanStep, result: str):
        """记录步骤完成日志"""
        step_log = f"task_id: {self.task_id}| Step {step.step_idx}"
        logger.info(
            f"{step_log} completed: {result}", simple_log=f"{step_log} completed"
        )

    def _handle_user_question(self, step: PlanStep, content: str):
        """处理用户提问中断"""
        logger.info(
            f"task_id: {self.task_id}| Step {step.step_idx} "
            f"LLM asking user input, interrupting execution"
        )
        self.terminate = True
        self._interrupted_by_workflow = True
        step.result = content
        step.status = StepStatus.IN_PROGRESS

    async def _finalize_plan_execution(self):
        """完成计划执行的收尾工作

        Returns:
            str: 最终结果（通过self._final_content存储）
            None: 如果计划未完成
        """
        if not self.task_planner.plan_tracker.is_completed():
            # 计划未完成时，仍需返回汇总响应，确保用户始终能得到最终回答
            ctx = self._step_exec_ctx
            final_hint = ctx["hint_builder"].build_hint_incomplete(ctx["plan"])
            final_result = await self._call_llm_with_hint(final_hint, ctx["filtered_tools"])
            self._final_content = (final_result or {"content": "任务执行未完成，请稍后重试"}).get("content", "任务执行未完成，请稍后重试")
            self.context_manager.set_result_message(self._final_content)
            return

        ctx = self._step_exec_ctx
        final_hint = ctx["hint_builder"].build_hint_all_completed(ctx["plan"])
        finalize_tools = ctx["filtered_tools"] if len(ctx["plan"].steps) == 0 else []

        final_result = await self._call_llm_with_hint(final_hint, finalize_tools)
        self._final_content = (final_result or {"content": "任务执行完成"}).get("content", "任务执行完成")
        self.context_manager.set_result_message(self._final_content)

    def _get_filtered_tools(self, plan: ExecutionPlan) -> List:
        """获取过滤后的工具列表"""
        plugins_source = self._get_plugins_source()
        filtered_plugins = self._filter_plugins_by_scene(
            plugins_source, plan.matched_scene
        )
        filtered_workflows = self._filter_workflows_by_scene(plan.matched_scene)
        
        all_tools = ToolFormatter.format_tools(
            plugins=filtered_plugins, mcps=None, workflow_contexts=filtered_workflows
        )
        
        # 动态过滤连续失败3次的工具
        broken_tools = {k for k, v in self._tool_failure_count.items() if v >= 3}
        if broken_tools:
            logger.info(
                f"task_id: {self.task_id}| [StepExecute] Filtering out broken tools: {broken_tools}",
                simple_log=f"task_id: {self.task_id}| [StepExecute] Filtering broken tools",
            )
        
        filtered_tools = [
            t for t in all_tools 
            if self._get_plugin_name(t) not in broken_tools
        ]
        
        # 如果所有工具都被过滤掉了，保留原列表让模型知道情况
        if not filtered_tools and all_tools:
            logger.warning(
                f"task_id: {self.task_id}| [StepExecute] All tools filtered out, using original list"
            )
            filtered_tools = all_tools
        
        return filtered_tools

    def _get_plugins_source(self) -> List:
        """获取插件来源"""
        return self.plugins if self.plugins else self.task_planner.plugins

    def _filter_plugins_by_scene(self, plugins_source: List, matched_scene) -> List:
        """根据场景过滤插件"""
        if matched_scene is None:
            filtered = plugins_source if plugins_source else []
            logger.info(
                f"task_id: {self.task_id}| [StepExecute] No scene, using all {len(filtered)} plugins",
                simple_log=f"task_id: {self.task_id}| [StepExecute] Using all plugins",
            )
            return filtered

        scene_tool_names = set(matched_scene.tools) if matched_scene.tools else set()
        injected_names = (
            self._skill_context.tool_names if self._skill_context else set()
        )
        allowed_names = scene_tool_names | injected_names
        filtered = [
            p
            for p in (plugins_source or [])
            if self._get_plugin_name(p) in allowed_names
        ]
        logger.info(
            f"task_id: {self.task_id}| [StepExecute] Filtered {len(filtered)} plugins by scene",
            simple_log=f"task_id: {self.task_id}| [StepExecute] Filtered {len(filtered)} plugins",
        )
        return filtered

    def _filter_workflows_by_scene(self, matched_scene) -> Dict:
        """根据场景过滤工作流"""
        all_workflows = (
            getattr(self.context_manager, "workflow_contexts", None)
            if self.context_manager
            else None
        )
        if matched_scene is None:
            logger.info(
                f"task_id: {self.task_id}| [StepExecute] No scene, using all {len(all_workflows)} workflows",
                simple_log=f"task_id: {self.task_id}| [StepExecute] Using all workflows",
            )
            return all_workflows

        scene_tool_names = set(matched_scene.tools) if matched_scene.tools else set()
        filtered = {
            k: ctx
            for k, ctx in all_workflows.items()
            if ctx.workflow_name in scene_tool_names
        }
        logger.info(
            f"task_id: {self.task_id}| [StepExecute] Filtered {len(filtered)} workflows by scene"
        )
        return filtered

    def _get_plugin_name(self, plugin) -> str:
        """
        获取插件名称，支持多种类型

        Args:
            plugin: 插件对象

        Returns:
            插件名称
        """
        # 内联实现，避免访问受保护成员
        if hasattr(plugin, "name"):
            return plugin.name
        if hasattr(plugin, "get_name"):
            return plugin.get_name()
        if isinstance(plugin, dict):
            return plugin.get("name", "")
        return ""

    def _get_message_count(self) -> int:
        """获取当前消息数量"""
        try:
            return len(self.context_manager.engine.get_messages())
        except Exception:
            return 0

    def _get_current_round_function_messages(self) -> list:
        """获取当前轮次的function消息，避免跨轮次污染"""
        try:
            all_msgs = self.context_manager.engine.get_messages()
            start_idx = getattr(self, "_current_round_msg_start_idx", 0)
            return [msg for msg in all_msgs[start_idx:] if msg.role == "function"]
        except Exception:
            return []

    async def _call_llm_with_hint(self, hint_message: str, tools: List) -> dict:
        """使用 hint 消息调用 LLM"""
        messages = self._build_llm_messages(hint_message)
        llm_output = await self._stream_llm_response(messages, tools)

        tool_calls, has_tool_calls = self._parse_tool_calls(llm_output)
        self._save_llm_response_to_context(llm_output, has_tool_calls, tool_calls)
        return {
            "content": llm_output.get("content", ""),
            "has_tool_calls": has_tool_calls,
            "tool_calls": tool_calls,
        }



    def _build_llm_messages(self, hint_message: str) -> List[dict]:
        """构建LLM消息列表"""
        raw_messages = self.context_manager.get_latest_k_chat_history(
            getattr(self.plan_config, "reserved_max_chat_rounds", 100)
        )
        messages = [m for m in raw_messages if isinstance(m, dict) and m.get("role")]
        messages.append({"role": "user", "content": hint_message})
        sys_prompt = getattr(
            self.plan_config, "sysPromptTemplate", self._get_default_sys_prompt()
        )
        if self._skill_context and self._skill_context.prompt_suffix:
            sys_prompt = f"{sys_prompt}\n\n{self._skill_context.prompt_suffix}"
        return [{"role": "system", "content": sys_prompt}] + messages

    def _get_default_sys_prompt(self) -> str:
        """获取默认系统提示词"""
        return """你是一个智能任务执行助手，擅长将复杂任务分解为多个步骤并逐步完成。

重要规则：
1. 当需要完成某个步骤时，你必须调用相关工具来执行，不要只是描述要做什么
2. 根据 <system-hint> 中的提示，调用合适的工具完成当前步骤
3. 每次只执行当前步骤，不要跳过步骤
4. 当确认当前步骤已完成时，必须在回复末尾输出 [STEP_DONE] 标记
5. 当需要向用户收集信息或确认时，必须在回复末尾输出 [ASK_USER] 标记"""

    async def _stream_llm_response(self, messages: List[dict], tools: List) -> dict:
        """流式调用LLM并收集响应"""
        llm_output = {"content": "", "role": "assistant"}
        content_parts = []

        try:
            from jiuwen.common.llm_service.language_model.base import LanguageModelInput
            from jiuwen.common.llm_service.model_util import ModelUtil
            from jiuwen.common.llm_service.messages import AIMessage
            from jiuwen.planner.common.stream_post_utils import (
                convert_ai_message_to_llm_output,
            )

            llm_messages = ModelUtil.switch_message(messages)
            llm_input = LanguageModelInput(
                messages=llm_messages, tools=tools if tools else None
            )
            self._log_llm_input(messages, tools)

            async for item in self.model.astream(llm_input):
                self._process_stream_item(
                    item,
                    llm_output,
                    content_parts,
                    convert_ai_message_to_llm_output,
                    AIMessage,
                )

            if not llm_output.get("content") and content_parts:
                llm_output["content"] = "".join(content_parts)
        except Exception as e:
            logger.exception(
                f"task_id: {self.task_id}| [StepExecute] LLM call failed: {e}"
            )
            llm_output["content"] = ""
            llm_output["error"] = str(e)

        self._log_llm_output(llm_output)
        return llm_output

    def _process_stream_item(
        self, item, llm_output: dict, content_parts: list, convert_func, ai_message_cls
    ):
        """处理流式响应中的单个项"""
        if isinstance(item, ai_message_cls):
            finish_reason = (
                item.usage_metadata.finish_reason if item.usage_metadata else None
            )
            if finish_reason in ["stop", "function_call"]:
                llm_output.update(convert_func(item).dict(exclude_defaults=True))
            elif item.content:
                content_parts.append(item.content)
        elif isinstance(item, dict):
            if item.get("content"):
                content_parts.append(item["content"])
            for key in ["function_call", "function_call_list"]:
                if key in item:
                    llm_output[key] = item[key]

    def _log_llm_input(self, messages: List, tools: List):
        """记录LLM输入日志，逐条打印每条消息的原始内容"""
        tools_count = len(tools) if tools else 0
        tool_names = [t.get("name", "") for t in (tools or []) if isinstance(t, dict)]
        logger.info(
            f"task_id: {self.task_id}| [StepExecute] <LLM Input> "
            f"messages_count={len(messages)}, tools_count={tools_count}, tool_names={tool_names}"
        )
        for idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                logger.info(
                    f"task_id: {self.task_id}| [StepExecute] <LLM Input> msg[{idx}] {msg}"
                )
                continue
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            func_call = msg.get("function_call") or msg.get("tool_calls")
            name = msg.get("name", "")
            extra = ""
            if name:
                extra += f", name={name}"
            if func_call:
                extra += f", function_call={json.dumps(func_call, ensure_ascii=False, default=str)}"
            logger.info(
                f"task_id: {self.task_id}| [StepExecute] <LLM Input> "
                f"msg[{idx}] role={role}{extra}, content={content}"
            )
        if tools:
            raw_tools = json.dumps(tools, ensure_ascii=False, default=str)
            logger.info(
                f"task_id: {self.task_id}| [StepExecute] <LLM Input> tools={raw_tools}"
            )

    def _log_llm_output(self, llm_output: dict):
        """记录LLM输出日志，打印原始输出内容"""
        content = llm_output.get("content", "")
        has_func_call = (
            "function_call" in llm_output or "function_call_list" in llm_output
        )
        func_names = []
        if llm_output.get("function_call_list"):
            func_names = [f.get("name", "") for f in llm_output["function_call_list"]]
        elif llm_output.get("function_call"):
            func_names = [llm_output["function_call"].get("name", "")]
        logger.info(
            f"task_id: {self.task_id}| [StepExecute] <LLM Output> "
            f"content_len={len(content)}, has_func_call={has_func_call}, func_names={func_names}, "
            f"content={content}"
        )
        if has_func_call:
            func_call_str = json.dumps(
                llm_output.get("function_call_list")
                or llm_output.get("function_call", {}),
                ensure_ascii=False,
                default=str,
            )
            logger.info(
                f"task_id: {self.task_id}| [StepExecute] <LLM Output> function_calls={func_call_str}"
            )

    def _parse_tool_calls(self, llm_output: dict) -> tuple:
        """解析工具调用"""
        func_call = llm_output.get("function_call")
        func_list = llm_output.get("function_call_list", [])
        has_calls = bool(func_call) or bool(func_list)
        calls = func_list if func_list else ([func_call] if func_call else [])
        return calls, has_calls

    def _inject_query_to_workflow_calls(self, tool_calls: List):
        """为工作流调用注入query，优先使用LLM自身生成的query"""
        if not tool_calls:
            return
        for call in tool_calls:
            if not self._find_workflow_by_name(call.get("name", "")):
                continue
            args = call.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args else {}
                except json.JSONDecodeError:
                    args = {}
            if not isinstance(args, dict):
                args = {}
            existing_query = args.get("query", "")
            if not existing_query and self._current_query:
                args["query"] = self._current_query
            call["arguments"] = args
            logger.info(f"inject query for workflow: {args.get('query', '')}")

    def _save_llm_response_to_context(
        self, llm_output: dict, has_tool_calls: bool, tool_calls: List
    ):
        """保存LLM响应到上下文"""
        content = llm_output.get("content", "")
        if not has_tool_calls:
            if not content and llm_output.get("error"):
                logger.warning(
                    f"task_id: {self.task_id}| Skipping empty LLM error response from context"
                )
                return
            if not content:
                logger.warning(
                    f"task_id: {self.task_id}| Skipping empty LLM response from context"
                )
                return
            self.context_manager.add_assistant_message(content)
            return
        func_list = llm_output.get("function_call_list", [])
        if func_list:
            intent_list = [c.get("name", "") for c in func_list]
            self.context_manager.add_assistant_message_with_multi_function_call(
                content, intent_list, func_list
            )
        else:
            func_call = llm_output.get("function_call", {})
            self.context_manager.add_assistant_message(
                content, func_call.get("name", ""), func_call
            )

    def _normalize_plugin_stream_result(
        self, result: dict, start_time: float
    ) -> Tuple[str, dict]:
        """
        标准化 plugin_handler 的流式结果

        Args:
            result: plugin_handler 返回的字典结果
            start_time: 任务开始时间，用于计算 overall_latency

        Returns:
            - event_type: 'function_call' | 'api_exec_data' | 'error' | 'unknown'
            - normalized_data: 标准化后的数据字典
        """
        end_time = time.time()

        # function_call 事件：LLM 生成的函数调用
        if result.get("function_call") is not None:
            time_consumption = dict(result["time_consumption"])
            time_consumption["overall_latency"] = round(end_time - start_time, 2)
            return "function_call", {
                "function_call": result["function_call"],
                "time_consumption": time_consumption,
            }

        # api_exec_data 事件：插件执行结果
        if result.get("result") is not None:
            return "api_exec_data", {
                "role": "function",
                "name": result.get("function_name", ""),
                "content": result.get("result", {}),
                "time_consumption": {
                    "plugin_latency": result.get("latency", 0.0),
                    "overall_latency": round(end_time - start_time, 2),
                },
            }

        # error 事件：插件执行错误
        if result.get("error_msg") is not None:
            return "error", {
                "role": "function",
                "name": result.get("function_name", ""),
                "content": result.get("error_msg", ""),
                "time_consumption": {
                    "plugin_latency": result.get("latency", 0.0),
                    "overall_latency": round(end_time - start_time, 2),
                },
            }

        # 未知类型，直接返回原数据
        return "unknown", result

    async def _handle_plugin_dict_result(
        self, result: dict, start_time: float
    ) -> AsyncGenerator:
        """
        处理插件返回的 dict 类型结果

        职责：
        - 标准化 plugin_handler 的返回数据，包装为 StreamData 并发送

        Args:
            result: plugin_handler 返回的字典
            start_time: 任务开始时间

        Yields:
            StreamData: 包装后的流式数据
        """
        event_type, normalized_data = self._normalize_plugin_stream_result(
            result, start_time
        )

        if event_type == "function_call":
            yield StreamData(
                code=StreamCode.PE_FUNCTION_CALL.value,
                msg="function_call",
                data={"answer": normalized_data},
                execution_id=self.task_id,
            )

        elif event_type == "api_exec_data":
            yield StreamData(
                code=StreamCode.PE_API_EXEC_DATA.value,
                msg="api_exec_data",
                data={"answer": normalized_data},
                execution_id=self.task_id,
            )

        elif event_type == "error":
            # 插件执行错误
            yield StreamData(
                code=StreamCode.PE_API_EXEC_DATA.value,
                msg="api_exec_data",
                data={"answer": normalized_data},
                execution_id=self.task_id,
            )

        elif event_type == "unknown":
            # 其他未知类型，记录日志
            logger.warning(
                f"task_id: {self.task_id}| Unknown dict result type: {result}",
                simple_log=f"task_id: {self.task_id}| Unknown dict result",
            )

    async def _execute_tool_call(
        self, tool_call: dict, plan: ExecutionPlan, step: PlanStep
    ) -> AsyncGenerator:
        """
        执行工具调用

        Args:
            tool_call: 工具调用信息
            plan: 执行计划
            step: 当前步骤（用于工作流中断时持久化 interrupted_workflow_name）

        Yields:
            工具执行相关的流式事件（复用 plugin_handler 原有的流式消息输出）
        """
        function_name = tool_call.get("name", "")
        arguments = tool_call.get("arguments", {})
        tool_call_id = tool_call.get("tool_call_id", str(uuid.uuid4()))

        logger.info(f"task_id: {self.task_id}| Executing tool: {function_name}")

        plugin = self._find_plugin_by_name(function_name)
        if plugin:
            async for stream_data in self._execute_plugin_tool(
                plugin, arguments, tool_call_id
            ):
                yield stream_data
        else:
            workflow_context = self._find_workflow_by_name(function_name)
            if workflow_context:
                args_query = (
                    arguments.get("query", "") if isinstance(arguments, dict) else ""
                )
                if args_query:
                    self._current_query = args_query
                async for stream_data in self._execute_workflow_tool(
                    workflow_context, tool_call_id, step, arguments
                ):
                    yield stream_data
            else:
                self._handle_tool_not_found(function_name, tool_call_id)
                # 工具未找到时向前端发送错误事件，确保用户能看到反馈
                yield StreamData(
                    code=StreamCode.ERROR.value,
                    msg="tool_not_found",
                    data={"message": f"工具 {function_name} 未找到", "error_type": "tool_not_found"},
                    execution_id=self.task_id,
                )

    async def _execute_plugin_tool(
        self, plugin, arguments: dict, tool_call_id: str
    ) -> AsyncGenerator:
        """
        执行插件工具

        Args:
            plugin: 插件对象
            arguments: 工具参数
            tool_call_id: 工具调用ID

        Yields:
            StreamData: 插件执行的流式事件
        """
        task_execution = self.task_dispatcher.dispatch(
            self._create_plugin_task(plugin, arguments, tool_call_id)
        )
        start_time = time.time()

        # 执行任务并收集结果
        # 注意：plugin_handler 的 stream_wrap_result 已经会调用 add_function_message
        # 所以这里不需要再调用 _add_tool_result_to_context，避免重复添加 ToolMessage
        async for result in self.task_executor.stream_execute(task_execution):
            # 处理 StreamData（包括工作流中断）
            if isinstance(result, StreamData):
                if self._handle_workflow_interrupt_stream(result):
                    yield result
                    return
                yield result
                continue

            # 处理 dict 类型的中间消息
            if isinstance(result, dict):
                async for stream_data in self._handle_plugin_dict_result(
                    result, start_time
                ):
                    yield stream_data
                continue

            if isinstance(result, Message):
                # Message 类型的结果在工具执行过程中不需要发送 intermediate_message
                # 只在请求结束时统一发送一次 intermediate_message
                logger.info(
                    f"task_id: {self.task_id}| Plugin message received: {result.message_type}",
                    simple_log=f"task_id: {self.task_id}| Plugin message received",
                )
                # 当收到插件完成消息时，发送 function_call_end 事件
                if result.message_type == MessageType.PLUGIN_COMPLETION:
                    yield StreamData(
                        code=StreamCode.PE_FUNCTION_CALL_END.value,
                        msg="function_call_end",
                        data={},
                        execution_id=self.task_id,
                    )
                continue

            # 其他类型日志
            logger.info(
                f"task_id: {self.task_id}| Plugin result type: {type(result)}",
                simple_log=f"task_id: {self.task_id}| Plugin result received",
            )

    async def _execute_workflow_tool(
        self, workflow_context, tool_call_id: str, step: PlanStep, arguments: dict = None
    ) -> AsyncGenerator:
        """
        执行工作流工具

        Args:
            workflow_context: 工作流上下文
            tool_call_id: 工具调用ID
            step: 当前步骤（用于工作流中断时持久化 interrupted_workflow_name）
            arguments: 完整的工具调用参数（包含 query 及其他业务字段）

        Yields:
            StreamData: 工作流执行的流式事件
        """
        task_execution = self.task_dispatcher.dispatch(
            self._create_workflow_task(workflow_context, tool_call_id, arguments)
        )

        async for result in self.task_executor.stream_execute(task_execution):
            # 处理 StreamData（包括工作流中断）
            if isinstance(result, StreamData):
                if self._handle_workflow_interrupt_stream(result):
                    step.interrupted_workflow_name = workflow_context.workflow_name
                    yield result
                    return
                if result.code == StreamCode.ERROR.value:
                    error_msg = result.data.get("message", "工作流执行失败")
                    error_type = result.data.get("error_type", "")
                    enhanced_msg = f"{workflow_context.workflow_name}执行失败: {error_msg}"
                    if error_type:
                        enhanced_msg = f"{workflow_context.workflow_name}({error_type})执行失败: {error_msg}"
                    self.context_manager.add_function_message(
                        name=workflow_context.workflow_name,
                        intent=workflow_context.workflow_name,
                        content=enhanced_msg,
                        tool_call_id=tool_call_id,
                    )
                    yield result
                    return  # 工作流ERROR后结束当前generator，_handle_tool_calls会继续出口判断
                yield result
                continue

            # 处理 Message 类型
            if isinstance(result, Message):
                # 检测工作流完成消息
                if result.is_workflow_completion:
                    self._workflow_completed = True
                    workflow_result = result.content
                    if isinstance(workflow_result, dict):
                        answer = workflow_result.get("exec_res", {}).get("answer", "")
                        self._last_workflow_result = answer or (
                            workflow_result.get("workflow_name", "") + " 执行完成"
                        )
                    else:
                        self._last_workflow_result = (
                            str(workflow_result)
                            if workflow_result
                            else "工作流执行完成"
                        )
                    logger.info(
                        f"task_id: {self.task_id}| Workflow completed: {self._last_workflow_result}",
                        simple_log=f"task_id: {self.task_id}| Workflow completed",
                    )

                # 处理工作流中断消息（如提问器）
                interrupt_streams = self._handle_workflow_interrupt_message(result)
                if interrupt_streams is not None:
                    self.terminate = True
                    self._interrupted_by_workflow = True
                    step.interrupted_workflow_name = workflow_context.workflow_name
                    self.context_manager.add_function_message(
                        name=workflow_context.workflow_name,
                        intent=workflow_context.workflow_name,
                        content="WaitingUserInput",
                        tool_call_id=tool_call_id,
                    )
                    for interrupt_stream in interrupt_streams:
                        yield interrupt_stream
                    continue

                # Message 类型的结果在工具执行过程中不需要发送 intermediate_message
                # 只在请求结束时统一发送一次 intermediate_message
                logger.debug(
                    f"task_id: {self.task_id}| Workflow message received: {result.message_type}",
                    simple_log=f"task_id: {self.task_id}| Workflow message received",
                )
                continue

            # 其他类型日志
            logger.debug(
                f"task_id: {self.task_id}| Workflow result type: {type(result)}",
                simple_log=f"task_id: {self.task_id}| Workflow result received",
            )

    def _handle_tool_not_found(self, function_name: str, tool_call_id: str):
        """
        处理工具未找到的情况

        Args:
            function_name: 工具名称
            tool_call_id: 工具调用ID
        """
        logger.warning(f"task_id: {self.task_id}| Plugin not found: {function_name}")
        self.context_manager.add_function_message(
            name=function_name,
            intent=function_name,
            content=f"工具 {function_name} 未找到",
            tool_call_id=tool_call_id,
        )

    def _find_workflow_by_name(self, name: str):
        """根据名称查找工作流上下文"""
        if not name:
            return None
        return self.context_manager.get_workflow_context_by_name_and_type(
            name, workflow_type=WorkflowType.GENERAL
        )

    def _create_workflow_task(self, workflow_context, tool_call_id: str, arguments: dict = None) -> Task:
        """创建工作流执行任务"""
        task_unique_id = f"{self.task_id}_workflow_{workflow_context.workflow_id}_{uuid.uuid4().hex[:8]}"
        workflow_req_params = (
            self.context_manager.get_global_variables(
                WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY, {}
            )
            or self._workflow_req_params
        )

        # 过滤对话历史中的 <system-hint>
        if isinstance(workflow_req_params, dict):
            conversation_history = workflow_req_params.get("conversationHistory")
            if isinstance(conversation_history, list):
                filtered_history = []
                for item in conversation_history:
                    if isinstance(item, dict):
                        content = item.get("content", "")
                    else:
                        content = str(item)
                    if "<system-hint>" in content:
                        continue
                    filtered_history.append(item)
                workflow_req_params = dict(workflow_req_params)
                workflow_req_params["conversationHistory"] = filtered_history

        input_data = {
            "query": self._current_query,
            "arguments": arguments or {},
            WorkflowConstants.WORKFLOW_REQ_PARAMS_KEY: workflow_req_params,
            "tool_call_id": tool_call_id,
            "conversation_id": self._conversation_id,
            "runtime_context": self._runtime_context,
        }

        # 增加工作流意图标签，便于状态恢复
        self.context_manager.add_intent_to_latest_user_message(
            workflow_context.workflow_name
        )

        return Task(
            id=task_unique_id,
            task_type=TaskType.WORKFLOW_START,
            input_data=input_data,
            sub_task_type=TaskSubType.STARTED_FROM_PLAN_EXECUTE,
            workflow_context=workflow_context,
        )

    def _find_plugin_by_name(self, name: str):
        """根据名称查找插件"""
        if not self.plugins:
            return None
        for plugin in self.plugins:
            if hasattr(plugin, "name") and plugin.name == name:
                return plugin
        return None

    def _create_plugin_task(self, plugin, arguments: dict, tool_call_id: str) -> Task:
        """创建插件执行任务"""
        task_unique_id = f"{self.task_id}_plugin_{plugin.name}_{uuid.uuid4().hex[:8]}"

        # 使用 json.dumps 序列化 arguments，确保是合法的 JSON 字符串
        arguments_str = (
            json.dumps(arguments, ensure_ascii=False)
            if isinstance(arguments, dict)
            else str(arguments)
        )

        input_data = {
            "plugin_name": plugin.name,
            "function_name": plugin.name,
            "function_call": {
                "name": plugin.name,
                "arguments": arguments_str,
                "tool_call_id": tool_call_id,
            },
            "arguments": arguments_str,
            "plugin": plugin,
            "tool_call_id": tool_call_id,
            "runtime_data": {"plugins": [plugin]},
            "time_dict": {},
        }

        return Task(
            id=task_unique_id, task_type=TaskType.PLUGIN_START, input_data=input_data
        )

    def _create_intermediate_stream_data(self, data: dict) -> StreamData:
        """将中间结果包装为 StreamData，返回对话历史"""
        try:
            msgs = self.context_manager.engine.get_messages()
        except Exception:
            msgs = []
        logger.info(
            f"task_id: {self.task_id}| Intermediate message count: {len(msgs)}",
            simple_log=f"task_id: {self.task_id}| Intermediate message count: {len(msgs)}",
        )
        formatted_msgs = ConversationHistory.convert_messages_to_chat_history_dict(msgs)
        return StreamData(
            code=StreamCode.CONTROLLER_INTERMEDIATE_MESSAGE.value,
            msg="intermediate message",
            data={"answer": formatted_msgs},
            execution_id=self.task_id,
        )

    def _handle_workflow_interrupt_message(self, message: Message):
        """处理工作流中断消息，必要时返回提问流"""
        if not message or not message.is_workflow_interrupt:
            return None

        user_interaction_types = [
            MessageSubType.PLUGIN_CALL_CONFIRM,
            MessageSubType.PLUGIN_PARAM_MISS,
            MessageSubType.QUESTIONER_ASK,
            MessageSubType.CONTROLLER_ASK,
        ]
        if message.sub_type not in user_interaction_types:
            return None

        if message.sub_type == MessageSubType.CONTROLLER_ASK:
            question = ""
            if isinstance(message.content, dict):
                question = message.content.get("question", "")
            if question:
                return list(self._yield_question_stream(question))
        return []

    def _handle_workflow_interrupt_stream(self, stream_data: StreamData) -> bool:
        """处理工作流中断相关的流式事件"""
        if not stream_data:
            return False
        if stream_data.code == StreamCode.WORKFLOW_BLOCKED_MESSAGE.value:
            self.terminate = True
            self._interrupted_by_workflow = True
            return True
        return False

    def _yield_question_stream(self, question: str):
        """生成提问流数据 - 与 React Agent 输出格式保持一致

        最终 SSE 格式: {"event": "message", "data": {"answer": "..."}}
        """
        # 与 React Agent 一致，只包含 answer 字段
        data = {"answer": question}
        yield StreamData(
            code=StreamCode.PARTIAL_CONTENT.value,
            msg="",
            data=data,
            execution_id=self.task_id,
        )
        yield StreamData(
            code=StreamCode.MESSAGE_END.value,
            msg="",
            data=data,
            execution_id=self.task_id,
        )

    # 步骤完成标识常量
    STEP_DONE_MARKER = "[STEP_DONE]"
    # 用户提问标识常量
    ASK_USER_MARKER = "[ASK_USER]"

    def _is_asking_user_input(self, content: str) -> bool:
        """
        判断 LLM 输出是否是向用户提问（需要等待用户输入）

        通过检测约定的精简标识 [ASK_USER] 来判断，节省 token 消耗。

        Args:
            content: LLM 输出内容

        Returns:
            是否需要向用户提问
        """
        if not content:
            return False

        # 检测约定标识
        if self.ASK_USER_MARKER in content:
            return True

        # 不再使用问号结尾作为降级检测，避免模型在陈述/推理中使用问号时误判为提问中断
        # 模型应严格使用 [ASK_USER] 标记来表示需要用户输入

        return False

    def _extract_question_content(self, content: str) -> str:
        """
        从 LLM 输出中提取问题内容（移除标记）

        Args:
            content: LLM 输出内容

        Returns:
            清理后的问题内容
        """
        return content.replace(self.ASK_USER_MARKER, "").strip()

    def _extract_final_content(self, content: str) -> str:
        """
        从所有步骤完成后的总结结果中提取内容（移除标记）

        Args:
            content: 所有步骤完成后的总结结果

        Returns:
            所有步骤完成后的最终结果（移除标记）
        """
        return content.replace(self.STEP_DONE_MARKER, "").strip()

    def _is_step_completed_by_llm(self, content: str, step: PlanStep) -> bool:
        """
        判断 LLM 输出是否表示步骤完成

        通过检测约定的精简标识 [STEP_DONE] 来判断，节省 token 消耗。
        同时支持 JSON 格式的完成信号检测（补充方式）。

        Args:
            content: LLM 输出内容
            step: 当前步骤

        Returns:
            是否标记步骤完成
        """
        # 优先检测约定的精简标识（推荐方式，节省 token）
        if self.STEP_DONE_MARKER in content:
            return True

        # 补充检测：JSON 格式完成信号（如 {"step_done": true}）
        if self._detect_json_step_done(content):
            return True

        # 兼容旧版本：仅匹配与当前步骤索引精确对应的完成标记
        # 注意：不使用"已完成"、"步骤完成"等宽泛标记，避免误判其他步骤的完成声明
        fallback_markers = [
            f"第{step.step_idx}步完成",
            f"第{step.step_idx}步已完成",
            f"step {step.step_idx} done",
            f"step {step.step_idx} completed",
            "[step_done]",
            "[done]",
        ]

        content_lower = content.lower()
        for marker in fallback_markers:
            if marker.lower() in content_lower:
                return True

        return False

    def _detect_json_step_done(self, content: str) -> bool:
        """检测 LLM 输出中的 JSON 格式步骤完成信号"""
        import re
        try:
            # 尝试从内容中提取 JSON 对象
            json_match = re.search(r'\{[^{}]*"step_done"\s*:\s*(true|True|1)\s*[^{}]*\}', content)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                if parsed.get("step_done") in (True, "true", 1, "1"):
                    logger.info(
                        f"task_id: {self.task_id}| Detected JSON step_done signal: {json_str[:100]}"
                    )
                    return True
        except json.JSONDecodeError:
            pass
        return False

    def _extract_step_result(self, content: str) -> str:
        """
        从 LLM 输出中提取步骤结果

        Args:
            content: LLM 输出内容

        Returns:
            步骤结果（保留完整内容，供最终总结LLM参考）
        """
        clean_content = content.replace(self.STEP_DONE_MARKER, "").strip()
        return clean_content if clean_content else "步骤执行完成"

    def _create_scene_match_stream_data(self, event: SceneMatchEvent) -> StreamData:
        """创建场景匹配事件数据"""
        data = {
            "matched": event.matched_scene is not None,
            "scene_id": event.matched_scene.id if event.matched_scene else None,
            "scene_name": event.matched_scene.name if event.matched_scene else None,
            "confidence": event.confidence,
        }
        return StreamData(
            code=StreamCode.PE_SCENE_MATCH.value,
            msg="scene_match",
            data=data,
            execution_id=self.task_id,
        )

    def _create_plan_end_stream_data(self, event: PlanEndEvent) -> StreamData:
        """创建任务规划完成事件数据"""
        steps_data = [
            {
                "step_idx": step.step_idx,
                "step_name": step.step_name,
                "description": step.description,
            }
            for step in event.plan.steps
        ]

        data = {
            "plan_id": event.plan.plan_id,
            "total_steps": len(event.plan.steps),
            "steps": steps_data,
        }
        return StreamData(
            code=StreamCode.PE_PLAN_END.value,
            msg="plan_end",
            data=data,
            execution_id=self.task_id,
        )

    def _create_step_start_stream_data(self, step, total_steps: int) -> StreamData:
        """创建步骤开始事件数据"""
        data = {
            "step_idx": step.step_idx,
            "step_name": step.step_name,
            "current_step": step.step_idx,
            "total_steps": total_steps,
        }
        return StreamData(
            code=StreamCode.PE_STEP_START.value,
            msg="step_start",
            data=data,
            execution_id=self.task_id,
        )

    def _create_step_end_stream_data(self, step) -> StreamData:
        """创建步骤结束事件数据"""
        result_summary = self._generate_step_summary(step)
        
        data = {
            "step_idx": step.step_idx,
            "step_name": step.step_name,
            "status": step.status.value
            if hasattr(step.status, "value")
            else str(step.status),
            "result_summary": result_summary,
        }
        return StreamData(
            code=StreamCode.PE_STEP_END.value,
            msg="step_end",
            data=data,
            execution_id=self.task_id,
        )

    def _generate_step_summary(self, step) -> str:
        """生成步骤执行总结，优先使用工具调用结果而非LLM过渡文本"""
        current_round_funcs = self._get_current_round_function_messages()

        # 尝试从所有function消息中提取有意义的工具执行结果
        tool_result_summary = self._extract_tool_results_summary(current_round_funcs, step)
        if tool_result_summary:
            return tool_result_summary

        # 无工具结果时 fallback 到 step.result
        return step.result if step.result else f"{step.step_name}完成"

    def _extract_tool_results_summary(self, function_msgs: list, step) -> str:
        """从function消息列表中提取工具执行结果摘要"""
        if not function_msgs:
            return ""

        parts = []
        for func_msg in function_msgs:
            try:
                content = func_msg.content
                if isinstance(content, str):
                    result = json.loads(content)
                else:
                    result = content

                if isinstance(result, dict):
                    summary = self._format_dict_result(result, step.step_name)
                    if summary:
                        parts.append(summary)
                elif isinstance(result, str) and result.strip():
                    # 非JSON的纯文本结果（如workflow返回的文本内容）
                    truncated = result.strip()[:500]
                    parts.append(truncated)
            except (json.JSONDecodeError, TypeError, KeyError):
                # JSON解析失败，尝试直接使用原始文本
                if isinstance(content, str) and content.strip():
                    truncated = content.strip()[:500]
                    parts.append(truncated)

        return "\n\n".join(parts) if parts else ""

    def _format_dict_result(self, result: dict, step_name: str) -> str:
        """格式化字典类型的工具执行结果"""
        if "result" in result:
            inner_result = result.get("result", {})
            if isinstance(inner_result, dict):
                stdout = inner_result.get("stdout", "")
                stderr = inner_result.get("stderr", "")
                exit_code = inner_result.get("exit_code", 0)
                code_content = inner_result.get("code_content", "")

                if exit_code == 0 and stdout:
                    return self._format_success_summary(stdout, code_content, step_name)
                elif exit_code != 0:
                    return self._format_error_summary(stdout, stderr, code_content, step_name)

        code_result = result.get("code_content", "")
        if code_result:
            return f"代码执行完成\n\n```python\n{code_result}\n```"

        # 尝试提取其他常见字段（如workflow返回的content/output等）
        for key in ("content", "output", "text", "response", "data"):
            val = result.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()[:500]
            elif isinstance(val, dict):
                inner_text = val.get("content") or val.get("output") or val.get("text")
                if isinstance(inner_text, str) and inner_text.strip():
                    return inner_text.strip()[:500]

        return ""

    def _format_success_summary(
        self, stdout: str, code_content: str, step_name: str
    ) -> str:
        """格式化成功执行结果"""
        parts = []
        
        if stdout.strip():
            stdout_lines = stdout.strip().split("\n")
            if len(stdout_lines) > 10:
                summary_lines = stdout_lines[:5]
                summary_lines.append("...")
                summary_lines.extend(stdout_lines[-3:])
                parts.append(f"执行结果：\n```\n" + "\n".join(summary_lines) + "\n```")
            else:
                parts.append(f"执行结果：\n```\n{stdout.strip()}\n```")
        
        if code_content.strip():
            parts.insert(0, f"执行的代码：\n```python\n{code_content.strip()}\n```")
        
        parts.append(f"✅ {step_name} 执行成功")
        
        return "\n\n".join(parts)

    def _format_error_summary(
        self, stdout: str, stderr: str, code_content: str, step_name: str
    ) -> str:
        """格式化错误执行结果"""
        parts = []
        
        if code_content.strip():
            parts.append(f"执行的代码：\n```python\n{code_content.strip()}\n```")
        
        output = stdout.strip() if stdout.strip() else ""
        if stderr.strip():
            if output:
                output += "\n\n错误信息：\n" + stderr.strip()
            else:
                output = "错误信息：\n" + stderr.strip()
        
        if output:
            parts.append(f"执行结果：\n```\n{output}\n```")
        
        parts.append(f"⚠️ {step_name} 执行失败\n\n")
        parts.append("说明：代码执行过程中出现错误。请检查代码语法或逻辑后重试。")
        
        return "\n\n".join(parts)

    def _create_task_complete_stream_data(self, plan) -> StreamData:
        """创建任务完成事件数据"""
        completed_steps = [
            step for step in plan.steps if step.status == StepStatus.COMPLETED
        ]

        data = {
            "status": "success",
            "total_steps": len(plan.steps),
            "completed_steps": len(completed_steps),
            "final_result": "任务执行完成",
        }
        return StreamData(
            code=StreamCode.PE_TASK_COMPLETE.value,
            msg="task_complete",
            data=data,
            execution_id=self.task_id,
        )

    def _create_interrupt_stream_data(self) -> StreamData:
        """创建中断消息的流数据

        当 PE Agent 被中断（如等待用户输入）时调用，
        用于通知 Agent Group 将 PE Agent 加入 interrupted_agents 列表，
        以便下一轮对话时直接路由到 PE Agent 继续执行。

        Returns:
            StreamData: 中断消息的流数据
        """
        interrupt_data = {
            "reason": "waiting_user_input",
            "state": "interrupted",
            "task_id": self.task_id,
        }

        logger.info(f"task_id: {self.task_id}| Creating interrupt stream data")

        return StreamData(
            code=StreamCode.CONTROLLER_AGENT_INTERRUPT_MESSAGE.value,
            msg="plan_execute_agent_interrupt",
            data=interrupt_data,
            execution_id=self.task_id,
        )

    def _create_task_end_stream_data(self) -> StreamData:
        """创建任务结束消息的流数据

        当 PE Agent 任务正常完成时调用，
        用于通知 Agent Group 任务已结束，可以清理状态，
        下一轮对话时将路由回 Controller Agent。

        Returns:
            StreamData: 任务结束消息的流数据
        """
        logger.info(f"task_id: {self.task_id}| Creating task end stream data")

        return StreamData(
            code=StreamCode.CONTROLLER_FINISH_MESSAGE.value,
            msg="task end",
            data={},
            execution_id=self.task_id,
        )

    def _create_statistic_data_stream_data(self) -> StreamData:
        """创建统计数据事件

        包含时间消耗等统计信息

        Returns:
            StreamData: 统计数据事件
        """
        overall_latency = None
        if hasattr(self, "_plan_start_time"):
            overall_latency = round(time.time() - self._plan_start_time, 2)

        # 构造时间统计数据
        time_consumption = {
            "total_latency": overall_latency,
            "model_latency": None,
            "wait_latency": None,
            "overall_latency": overall_latency,
        }

        return StreamData(
            code=StreamCode.STATISTIC_DATA.value,
            msg="statistic_data",
            data={"answer": time_consumption},
            execution_id=self.task_id,
        )

    def _create_step_timeout_stream_data(self, step: PlanStep, error_msg: str) -> StreamData:
        """创建步骤超时/终止事件数据"""
        if error_msg and "相同错误重复出现" in error_msg:
            content = f"⚠️ 步骤执行终止\n\n{error_msg}\n\n说明：由于相同错误重复出现多次，系统判定无法通过重试修复，已终止任务。"
        else:
            content = f"⚠️ 步骤执行超时\n\n{error_msg}\n\n说明：由于步骤执行超出最大迭代次数，系统强制终止任务。请检查代码逻辑或增加迭代次数。"
        data = {
            "answer": {
                "role": "assistant",
                "content": content
            }
        }
        return StreamData(
            code=StreamCode.SUMMARY_RESPONSE.value,
            msg="step_timeout",
            data=data,
            execution_id=self.task_id,
        )

    def _create_summary_response_stream_data(self, final_data: str) -> StreamData:
        """创建最终汇总响应事件

        包含LLM生成的最终总结内容

        Args:
            final_data: 所有步骤完成的总结数据

        Returns:
            StreamData: 最终汇总事件
        """
        summary_answer = {
            "role": "assistant",
            "content": self._extract_final_content(final_data),
        }

        return StreamData(
            code=StreamCode.SUMMARY_RESPONSE.value,
            msg="summary_response",
            data={"answer": summary_answer},
            execution_id=self.task_id,
        )
