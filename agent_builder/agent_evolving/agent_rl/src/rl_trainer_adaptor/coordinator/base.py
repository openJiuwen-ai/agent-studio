# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from enum import Enum

from pydantic import BaseModel


class RLTask(BaseModel):
    """The standard single rollout task."""

    task_id: str
    origin_task_id: str
    task_sample: dict = {}
    round_num: int = 0


class TaskStatus(str, Enum):
    """
    Training task lifecycle states.
    Typical flow: NONE -> INITIALIZING -> MODEL_READY -> RUNNING -> FINISHED 或 RUNNING -> FAILED

    INITIALIZING: 标识训练任务已正确初始化，在正常调用ModelService.start_model_service后，任务会被标记为该状态
    MODEL_READY：标识当前训练任务代理已经正确启动，在正常调用ModelService.start_proxy_server后，任务会被标记为该状态
    RUNNING：标识当前任务正在训练，在正常调用TrainingService.start_training后，任务会被标记为该状态
    FINISHED：标识当前任务已完成训练，当所有的epoch执行完成后该任务会被标记成该状态
    FAILED：训练过程出现错误后当前任务会被标记为该状态，或调用TrainingService.stop_training以后也会被标记为该状态
    """

    INITIALIZING = "initializing"
    MODEL_READY = "model_ready"
    RUNNING = "running"
    FAILED = "failed"
    FINISHED = "finished"
