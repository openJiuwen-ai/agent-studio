#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""层次化智能体组"""

from typing import Union, AsyncGenerator, Optional, Dict, Any

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.utils.utils import format_exception_reason
from jiuwen.controller.agent.agent import Agent
from jiuwen.multi_agent.agent_group.base_agent_group import BaseAgentGroup
from jiuwen.multi_agent.agent_group.config import AgentGroupConfig
from jiuwen.multi_agent.agent_group.group_state import AgentGroupState
from jiuwen.multi_agent.agent_group.hierarchical_group.control_agent import (
    HierarchicalControlAgent,
)
from jiuwen.multi_agent.core.member import MemberMessageType
from jiuwen.multi_agent.core.runner.standalone_runner import StandaloneRunner
from jiuwen.orchestration.flow.enum import StreamDataMsg
from jiuwen.orchestration.flow.stream.base import StreamData, StreamCode
from jiuwen.serve.controllers.execution.utils import AgentIrUtils


class HierarchicalAgentGroup(BaseAgentGroup):
    """层次化智能体组 - 支持多层控制器的Agent系统"""

    def __init__(self, config: AgentGroupConfig) -> None:
        super().__init__(config)
        # 获取所有agent对应task_id，用于删除template
        self.task_ids: Dict[str, str] = {}
        self._get_task_ids(config)

    async def start(self, state: Optional[AgentGroupState] = None) -> None:
        """启动智能体组"""
        try:
            if self._running:
                raise JiuWenBaseException(
                    error_code=StatusCode.MULTI_AGENT_GROUP_ALREADY_STARTED.code,
                    message="Agent group already running",
                )
            self._group_state = state
            if state is None:
                self._group_state = AgentGroupState()

            logger.info(f"Starting AgentGroup {self.config.group_id}")

            if self.runner is None:
                self.runner = StandaloneRunner()
            # 初始化所有Agent
            await self._register_agents()

            # 创建控制Agent
            self.create_control_agent()

            # 加载状态
            if state:
                await self.load_state(state)
                await self.runner.start(state.run_state)
            else:
                await self.runner.start()

            self._running = True
            logger.debug(f"AgentGroup {self.config.group_id} started successfully")

        except Exception as e:
            logger.error(
                f"Failed to start AgentGroup: {e}",
                simple_log="Failed to start AgentGroup",
            )
            raise

    async def stop(self) -> None:
        """停止智能体组"""
        if not self._running:
            logger.warning(f"Agent group {self.config.group_id} not running")
            return

        try:
            logger.debug(f"Stopping AgentGroup {self.config.group_id}")
            self._running = False
            await self.runner.stop()
            logger.info(f"AgentGroup {self.config.group_id} stopped successfully")
        except Exception as e:
            logger.error(
                f"Failed to stop AgentGroup: {e}",
                simple_log="Failed to stop AgentGroup",
            )
            raise

    async def astream(self, inputs: Union[dict, str], **kwargs) -> AsyncGenerator:
        pass
        """
        执行AgentGroup的流式处理 - 核心任务循环

        Args:
            inputs: 用户输入指令
            **kwargs: 额外参数

        Yields:
            处理结果的流式输出
        """
        if not self._running or not self.control_agent:
            raise RuntimeError("AgentGroup is not running or not properly initialized")

        try:
            async for result in self.control_agent.execute(inputs, **kwargs):
                if result.type == MemberMessageType.STREAM:
                    yield result.data
                elif result.type == MemberMessageType.INTERRUPT:
                    logger.info(
                        "Received INTERRUPT message, saving state and stopping stream"
                    )
                    await self._group_state.save_agent_group_state(
                        self.runner, self.control_agent
                    )
                    break
                elif result.type == MemberMessageType.ERROR:
                    _inner = getattr(result.data, "data", None)
                    _err_msg = _inner.get("message") if isinstance(_inner, dict) else None
                    _err_code = _inner.get("code") if isinstance(_inner, dict) else None
                    logger.error(
                        f"Received ERROR message from agent: code={_err_code}, "
                        f"message={_err_msg}, raw={result.data}",
                        simple_log="Received ERROR message",
                    )
                    yield result.data

        except Exception as e:
            logger.error(
                f"Error in AgentGroup execution: {e}, "
                f"group_id: {self.config.group_id}, group_name: {self.config.group_name}",
                simple_log="Error in AgentGroup execution",
            )
            yield StreamData(
                code=StreamCode.ERROR.value,
                msg=StreamDataMsg.FAIL.value,
                data=dict(
                    code=StatusCode.MULTI_AGENT_GROUP_EXECUTE_ERROR.code,
                    message=StatusCode.MULTI_AGENT_GROUP_EXECUTE_ERROR.errmsg.format(
                        reason="Error in AgentGroup execution"
                    ),
                ),
                execution_id="",
            )
            raise JiuWenBaseException(
                error_code=StatusCode.MULTI_AGENT_GROUP_EXECUTE_ERROR.code,
                message=StatusCode.MULTI_AGENT_GROUP_EXECUTE_ERROR.errmsg.format(
                    reason=format_exception_reason(
                        e, reason="Error in AgentGroup execution"
                    )
                ),
            ) from e
        finally:
            await self.stop()

    async def get_state(self) -> AgentGroupState:
        """获取Agent Group状态"""
        await self._group_state.save_agent_group_state(self.runner, self.control_agent)
        return self._group_state

    async def load_state(self, state: AgentGroupState) -> None:
        """加载Agent Group状态"""
        await self._group_state.restore_agent_group_state(
            self.runner, self.control_agent
        )

    def create_control_agent(self):
        """创建层次化控制Agent"""
        self.control_agent = HierarchicalControlAgent(
            agents=self.agents,
            config=self.config,
            runner=self.runner,
        )
        logger.info("Hierarchical control agent created successfully")

    def update_group_prompt(self, agent_info_map: Dict[str, Dict[str, Any]]):
        """注册prompt"""
        for _, agent_info in agent_info_map.items():
            AgentIrUtils.build_prompt(agent_info["task_id"], agent_info["task_model"])

    def get_task_end(self):
        """
        获取任务状态
        Returns: task_end
        """
        return self.control_agent.task_end

    def clear_state(self):
        """
        清除实例状态
        Returns:

        """
        pass

    async def _register_agents(self):
        """初始化所有Agent"""
        try:
            # main agent
            self.agents.add(self.config.main_agent.metadata.id)
            self.runner.register_member(
                self.config.main_agent.metadata.id, Agent, self.config.main_agent
            )

            # sub agent
            for cfg in self.config.agents:
                self.agents.add(cfg.metadata.id)
                self.runner.register_member(cfg.metadata.id, Agent, cfg)
            logger.info(f"Registered {len(self.agents)} agents")
        except Exception as e:
            logger.error("Failed to initialize agents")
            raise JiuWenBaseException(
                error_code=StatusCode.MULTI_AGENT_GROUP_AGENT_REGISTRATION_ERROR.code,
                message=StatusCode.MULTI_AGENT_GROUP_AGENT_REGISTRATION_ERROR.errmsg.format(
                    reason=format_exception_reason(e)
                ),
            ) from e

    def _get_task_ids(self, config: AgentGroupConfig):
        """获取所有agent对应task_id"""
        self.task_ids[config.main_agent.metadata.id] = config.main_agent.task_id
        for cfg in self.config.agents:
            self.task_ids[cfg.metadata.id] = cfg.task_id
