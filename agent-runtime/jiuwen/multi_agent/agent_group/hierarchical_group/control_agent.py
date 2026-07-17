#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""控制Agent"""

import asyncio
import time
from typing import Union, Any, AsyncGenerator, List, Optional, Set, Tuple

from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.context.history import ConversationHistory, ConversationMessage
from jiuwen.multi_agent.agent_group.base_control_agent import BaseControlAgent
from jiuwen.multi_agent.agent_group.config import AgentGroupConfig
from jiuwen.multi_agent.agent_group.enum import ExecutionAction
from jiuwen.multi_agent.agent_group.group_state import AgentGroupState
from jiuwen.multi_agent.core.member import MemberMessageType, Message
from jiuwen.multi_agent.core.stream.stream_handler import StreamHandler
from jiuwen.orchestration.flow.enum import StreamDataMsg
from jiuwen.orchestration.flow.stream.base import StreamData, StreamCode


class HierarchicalControlAgent(BaseControlAgent):
    """分层控制Agent"""

    def __init__(self, agents: Set[str], config: AgentGroupConfig, runner: Any):
        super().__init__(agents, config, runner)
        self.current_agent_calls_count: int = 0
        self.interrupted_agents: List[str] = []
        self.call_agent_history: List[str] = []
        self.message_context: ConversationHistory = ConversationHistory()

    @staticmethod
    def _create_error_message(
        error_msg: str, agent_id: str = "control_agent", execution_id: str = ""
    ) -> Message:
        """创建标准化的错误消息"""
        return Message(
            type=MemberMessageType.ERROR,
            agent_id=agent_id,
            data=StreamData(
                code=StreamCode.ERROR.value,
                msg=StreamDataMsg.FAIL.value,
                data=dict(
                    code=StatusCode.MULTI_AGENT_GROUP_EXECUTE_ERROR.code,
                    message=error_msg,
                ),
                execution_id=execution_id,
            ),
            timestamp=time.time(),
        )

    async def execute(self, inputs: Union[dict, str], **kwargs) -> AsyncGenerator:
        """执行任务 - 简化的agent调用循环"""
        try:
            current_inputs = {"inputs": inputs, **kwargs}
            # 从req获取对话历史 初始化 message_context
            self._init_message_context(current_inputs)

            # 如果是新的执行，重置计数器
            if kwargs.get("reset_count", False):
                self.current_agent_calls_count = 0
                self.call_agent_history = []

            while self.current_agent_calls_count <= self.config.max_agent_calls:
                # 1. 进行循环检测，选择agent
                (
                    agent_id,
                    force_default_workflow,
                ) = await self._select_agent_with_cycle_check(current_inputs)
                self.current_agent_calls_count += 1
                logger.info(
                    f"Agent call count: {self.current_agent_calls_count}/{self.config.max_agent_calls}"
                )

                if not agent_id:
                    logger.info("No more agents available for execution")
                    break
                self.call_agent_history.append(agent_id)
                # 2. 调用agent
                stream_handler = StreamHandler()
                send_task = None
                try:
                    # 更新聊天历史到inputs
                    self._prepare_agent_inputs(
                        current_inputs, agent_id, force_default_workflow
                    )
                    logger.info(
                        f"load conv_history related to agent_id {agent_id}: {self._get_history(current_inputs)}",
                        simple_log=f"load conv_history related to agent_id {agent_id}",
                    )
                    send_task = asyncio.create_task(
                        self.runner.send_message(
                            message=current_inputs,
                            recipient=agent_id,
                            sender="control_agent",
                            stream_handler=stream_handler,
                        )
                    )
                    # 3. 处理agent响应并更新状态
                    action = ExecutionAction.CONTINUE
                    should_break = False
                    target_agent_info = {}
                    async for chunk in stream_handler.stream_output():
                        # 直接yield原始Message格式
                        if action == ExecutionAction.CONTINUE:
                            action, should_break = self.handle_agent_response(
                                agent_id, chunk, target_agent_info
                            )
                        yield chunk

                    if should_break:
                        break

                    if action == ExecutionAction.HANDOFF:
                        current_inputs = self.prepare_handoff_inputs(
                            target_agent_info.get("agent_id", ""),
                            current_inputs,
                            agent_id,
                        )

                except Exception as e:
                    error_msg = f"Agent execution failed: {str(e)}"
                    yield self._log_and_yield_error(error_msg, agent_id)
                    break
                finally:
                    if send_task and not send_task.done():
                        await send_task

                    if stream_handler.is_running():
                        await stream_handler.stop()

            # 如果达到最大调用次数，返回Error消息
            if (
                self.current_agent_calls_count > self.config.max_agent_calls
                and not force_default_workflow
            ):
                error_msg = (
                    f"Reached maximum agent calls limit ({self.config.max_agent_calls})"
                )
                yield self._log_and_yield_error(error_msg)

        except Exception as e:
            error_msg = f"Error in ControlAgent execution: {e}"
            yield self._log_and_yield_error(error_msg)

    def handle_agent_response(
        self, agent_id: str, message: Message, target_agent_info: dict
    ) -> (tuple)[ExecutionAction, bool]:
        """
        处理agent响应并更新状态

        Returns:
            tuple: (执行动作, 是否应该跳出循环)
        """
        # 检查Message中的类型并直接处理
        if not isinstance(message, Message) or message is None:
            return ExecutionAction.CONTINUE, False

        # 更新对话历史 只更新intermediate_message
        if message.data.code == StreamCode.CONTROLLER_INTERMEDIATE_MESSAGE.value:
            self._update_message_context(message)

        if message.type == MemberMessageType.HANDOFF:
            target_agent = self._extract_handoff_target(message)
            if target_agent and target_agent in self.agents:
                logger.info(f"Handoff from {agent_id} to {target_agent}")
                target_agent_info["agent_id"] = target_agent
                return ExecutionAction.HANDOFF, False
            logger.warning(f"Invalid handoff target: {target_agent}")
            return ExecutionAction.ERROR, True

        if message.type == MemberMessageType.INTERRUPT:
            logger.info(f"Agent {agent_id} requested interrupt")
            # 直接处理中断逻辑
            self._handle_agent_interrupt(agent_id)
            return ExecutionAction.INTERRUPT, True

        if message.type == MemberMessageType.ERROR:
            _inner = getattr(message.data, "data", None)
            _err_msg = _inner.get("message") if isinstance(_inner, dict) else None
            logger.error(
                f"Agent {agent_id} returned error: message={_err_msg}, raw={message.data}"
            )
            return ExecutionAction.ERROR, True

        if (
            message.type == MemberMessageType.STREAM
            and message.data.code == StreamCode.CONTROLLER_FINISH_MESSAGE.value
        ):
            logger.info(f"Agent {agent_id} finished control")
            self.task_end = True
            return ExecutionAction.FINISH, True

        # 默认继续执行
        return ExecutionAction.CONTINUE, False

    def prepare_handoff_inputs(
        self, target_agent: str, current_inputs: Union[dict, str], from_agent: str
    ) -> Union[dict, str]:
        """
        准备handoff输入 - 合并了所有handoff相关的逻辑

        Args:
            target_agent: 目标agent
            current_inputs: 当前输入
            from_agent: 发起handoff的agent ID

        Returns:
            为目标agent准备的输入
        """
        if not target_agent:
            logger.warning("No target agent found in handoff response")
            return current_inputs

        # 准备handoff上下文
        handoff_context = {
            "to_agent": target_agent,
            "from_agent": from_agent,
            "reason": "explicit_handoff_request",
        }

        # 根据输入类型设置handoff信息
        if isinstance(current_inputs, dict):
            # 直接在字典中设置handoff上下文
            current_inputs["handoff_context"] = handoff_context
            return current_inputs
        # 如果输入不是字典，创建一个包含handoff上下文的字典
        return {"original_input": current_inputs, "handoff_context": handoff_context}

    async def select_agent(self, inputs: Union[dict, str]) -> Optional[str]:
        """agent选择方法"""
        # 1. 检查handoff上下文 - 最高优先级
        if isinstance(inputs, dict) and "handoff_context" in inputs:
            target_agent = inputs["handoff_context"].get("to_agent")
            if target_agent and target_agent in self.agents:
                logger.info(f"Selected agent from handoff context: {target_agent}")
                # 清除handoff上下文，避免重复使用
                del inputs["handoff_context"]
                return target_agent

        # 2. 如果有中断的agent，优先执行最近一次中断的agent (LIFO)
        if self.interrupted_agents:
            recent_interrupted_agent = self.interrupted_agents.pop()

            if recent_interrupted_agent in self.agents:
                logger.info(f"Resuming interrupted agent: {recent_interrupted_agent}")
                return recent_interrupted_agent

        # 3. 默认选择main_agent
        main_agent_id = self.config.main_agent.metadata.id
        if main_agent_id in self.agents:
            logger.info(f"Selected main agent: {main_agent_id}")
            return main_agent_id

        logger.warning("No available agents found")
        return None

    async def get_state(self) -> AgentGroupState:
        """获取控制Agent状态"""
        state = AgentGroupState()
        state.current_agent_calls_count = self.current_agent_calls_count
        state.interrupted_agents = self.interrupted_agents.copy()
        return state

    async def load_state(self, state: AgentGroupState) -> None:
        """加载控制Agent状态"""
        self.current_agent_calls_count = (
            state.current_agent_calls_count
            if (state.current_agent_calls_count is not None)
            else 0
        )
        self.interrupted_agents = (
            state.interrupted_agents.copy() if state.interrupted_agents else []
        )
        logger.info(
            f"Loaded state: calls={self.current_agent_calls_count}, "
            f"interrupted_agents={len(self.interrupted_agents)}"
        )

    def reset_execution_state(self) -> None:
        """重置执行状态"""
        self.current_agent_calls_count = 0
        self.interrupted_agents.clear()
        logger.info("Execution state reset")

    def _log_and_yield_error(
        self, error_msg: str, agent_id: str = "control_agent", execution_id: str = ""
    ) -> Message:
        """记录日志并生成错误消息"""
        logger.error(
            f"Error in agent {agent_id}: {error_msg}",
            simple_log=f"Error in agent {agent_id}",
        )
        return self._create_error_message(error_msg, agent_id, execution_id)

    def _handle_agent_interrupt(self, agent_id: str) -> None:
        """处理agent中断逻辑"""
        # 如果agent已经在中断列表中，移除它（避免重复）
        if agent_id in self.interrupted_agents:
            self.interrupted_agents.remove(agent_id)

        # 将agent添加到中断列表末尾（最新中断的在最后）
        self.interrupted_agents.append(agent_id)
        # 中断时不消耗调用次数，回退计数器
        self.current_agent_calls_count -= 1
        logger.info(
            f"Agent {agent_id} interrupted. Total interrupted: {len(self.interrupted_agents)}"
        )

    def _extract_handoff_target(self, message: Message) -> Optional[str]:
        """从handoff消息中提取目标agent"""
        if isinstance(message.data, StreamData) and isinstance(message.data.data, dict):
            return message.data.data.get("target_agent").get("id")
        return None

    def _init_message_context(self, current_inputs) -> None:
        chat_from_req: List[ConversationMessage] = (
            current_inputs["runtime_context"]
            .agent_workflow_context.get("workflow_chat_history")
            .get_all_messages()
        )
        self.message_context.add_messages(chat_from_req)

    def _update_message_context(self, message: Message) -> None:
        """更新所有agent聊天历史到intermediate_message返回"""
        chat_history = message.data.data["answer"] or []

        if not chat_history:
            logger.warning("chat_history is empty, skipping update")
            return

        # 提取 agent_id
        first_msg = chat_history[0]
        agent_id = getattr(first_msg, "agent_id", None)

        # 替换该 agent_id 的所有消息
        self.message_context.msgs = [
            msg
            for msg in self.message_context.msgs
            if getattr(msg, "agent_id", None) != agent_id
        ]
        self.message_context.add_messages(chat_history)

        # message_context作为intermediate_message返回
        message.data.data["answer"] = self.message_context.msgs
        final_intermediate_message = message.data.data["answer"]
        logger.info(
            f"updated intermediate_message: {final_intermediate_message}",
            simple_log="updated intermediate_message",
        )

    def _prepare_agent_inputs(self, current_inputs, agent_id, force_default_workflow):
        """更新发送给member agent的input为当前agent相关对话历史"""
        selected_chat_history = [
            msg.__dict__
            for msg in self.message_context.msgs
            if msg.agent_id == agent_id
        ]
        logger.info(
            f"get chat_history for agent: {agent_id} chat_history: {selected_chat_history}",
            simple_log=f"get chat_history for agent: {agent_id}",
        )
        context = current_inputs["runtime_context"].agent_workflow_context
        context["workflow_chat_history"] = ConversationHistory(selected_chat_history)
        context["force_default_workflow"] = force_default_workflow

    def _get_history(self, inputs: dict):
        """获取conversation_history的值"""
        return (
            inputs["runtime_context"]
            .agent_workflow_context.get("workflow_chat_history")
            .msgs
        )

    async def _select_agent_with_cycle_check(
        self, current_inputs: dict
    ) -> Tuple[Optional[str], bool]:
        """
        选择下一个要调用的agent, 当调用次数达到最大时进行循环检测。

        Returns:
            Tuple[Optional[str], bool]: 调用的agent_id(可为None), 是否存在调用agent循环
        """
        if self.current_agent_calls_count > self.config.max_agent_calls:
            if self._detect_cycle():
                logger.warning(
                    f"Cyclic repeated calls, call chain: {self.call_agent_history}",
                    simple_log="Cyclic repeated calls.",
                )
                return self.config.main_agent.metadata.id, True
            return None, False
        return await self.select_agent(current_inputs), False

    def _detect_cycle(self) -> bool:
        """检测调用历史中是否存在死循环"""
        history = self.call_agent_history
        history_len = len(history)
        if history_len < 2:
            return False

        # 从末尾开始检查可能的子串长度
        for sub_len in range(1, history_len // 2 + 1):
            # 检查末尾的子串是否在前面出现过
            end_substring = history[-sub_len:]
            if history[-2 * sub_len : -sub_len] == end_substring:
                return True

        return False
