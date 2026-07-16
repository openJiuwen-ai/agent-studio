# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import List, Optional, Dict

from pydantic import BaseModel, Field


class RolloutWithReward(BaseModel):
    """A standard structure for a single turn rollout."""

    turn_id: Optional[int] = None
    task_id: Optional[str] = None
    rollout_id: Optional[str] = None
    input_prompt_ids: List[int] = []
    output_response_ids: List[int] = []
    reward: Optional[float] = None


class Rollout(BaseModel):
    """A standard structure for a single turn rollout."""

    # 对话轮数下标
    turn_id: Optional[int] = None
    input_prompt: Optional[Dict] = None
    output_response: Optional[Dict] = None


class RolloutMessage(BaseModel):
    """The standard reporting rollout message."""

    task_id: Optional[str] = None
    origin_task_id: Optional[str] = None
    rollout_id: Optional[str] = None
    # rollout采样开始时间
    start_time: Optional[str] = None
    # rollout采样结束时间
    end_time: Optional[str] = None
    # rollout信息列表
    rollout_info: List[Rollout] = Field(default_factory=list)
    # 细粒度奖励列表，长度等于turn_count
    reward_list: List[float] = Field(default_factory=list)
    # 全局奖励
    global_reward: Optional[float] = None
    # 当前对话总轮数
    turn_count: int = 0
    # ada采样次数下标，对应Task中的round_num
    rollout_index: Optional[int] = None
    message_flag: bool = True
