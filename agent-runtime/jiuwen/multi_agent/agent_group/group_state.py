#!/usr/bin/env python
# coding=utf-8
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from jiuwen.multi_agent.core.state_manager.run_state import RunState


@dataclass
class AgentGroupState:
    """智能体组状态 - 合并简化版"""

    # 当前执行状态
    current_agent_id: Optional[str] = None
    interrupted_agents: List[str] = field(default_factory=list)
    current_agent_calls_count: int = 0
    # 运行时状态
    run_state: RunState = field(default_factory=RunState)
    # 时间戳
    last_updated_at: datetime = field(default_factory=datetime.now)

    async def restore_agent_group_state(self, runner, control_agent) -> None:
        """Restore the state of the agent group."""
        await runner.load_state(self.run_state)
        await control_agent.load_state(self)

    async def save_agent_group_state(self, runner, control_agent) -> None:
        """Save the state of the agent group."""
        self.run_state = await runner.get_state() or RunState()
        self.interrupted_agents = control_agent.interrupted_agents.copy()
        self.current_agent_calls_count = control_agent.current_agent_calls_count
