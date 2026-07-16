# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from agent_builder.agent_evolving.agent_rl.src.runtime_and_sampler_adaptor.trajectory_collector import (
    SpanBuilder,
)
from agent_builder.agent_evolving.agent_rl.src.utils.logging import get_logger

logger = get_logger(__name__)


class RuntimeExecutor:
    """Executes a single rollout task by generating IR spans, processing them into
    structured rollout steps, and computing rewards for the final rollout output.
    It returns a fully populated RolloutMessage containing rollout steps,
    token-level reward values, execution timestamps, and the final global reward.
    This class is designed to be called repeatedly inside parallel worker loops.
    """

    def __init__(self):
        self.span_builder = SpanBuilder()

    async def execute_async(self, rollout_task, agent_info):
        """Execute a rollout task asynchronously by generating IR spans,
        parsing rollout steps, computing rewards, and returning a populated RolloutMessage.
        """
        pass
