# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
agent builder chain Template optimizer
"""

from typing import Dict, Optional, Any, List

from agent_builder.common.status import TaskStatus
from pydantic import BaseModel, Field


class JobInfo(BaseModel):
    """
    A class for storing basic information about a job.
    This class is used to represent the metadata of a job,
    such as its ID, name, description, and related model information.
    """

    id: str = Field(default="")
    name: str = Field(default="")
    desc: str = Field(default="")
    num_iter: int = Field(default=0)
    created_at: str = Field(default="")
    optimized_model: str = Field(default="")
    assistant_model: str = Field(default="")


class Progress(BaseModel):
    job_info: Optional[JobInfo] = Field(default={})
    original_prompt: str = Field(default="")
    best_prompt: str = Field(default="")
    original_placeholder: Dict[str, Any] = Field(default={})
    best_placeholder: Dict[str, Any] = Field(default={})
    examples: List = Field(default=[])
    filled_prompt: str = Field(default="")
    success_rate: float = Field(default=0.0)
    error_msg: str = Field(default="")
    progress_rate: float = Field(default=0.0)
    time_cost: int = Field(default=0)
    status: str = Field(default=TaskStatus.TASK_FAILED)
    evaluation_method: str = Field(default="")


class History(BaseModel):
    optimized_prompt: str = Field(default="")
    original_placeholder: Dict[str, str] = Field(default={})
    optimized_placeholder: Dict[str, str] = Field(default={})
    examples: List[str] = Field(default=[])
    filled_prompt: str = Field(default="")
    success_rate: float = Field(default=0.0)
    iteration_round: int = Field(default=0)
    evaluations: List[Dict] = Field(default=[])


class SingleTaskInfo(BaseModel):
    """SingleTaskInfo"""

    progress: Progress = Field(default=Progress())
    history: List[History] = Field(default=[])


class JobDetail(BaseModel):
    """JobDetail"""

    job_info: Optional[JobInfo] = Field(default=None)
    status: str = Field(default=TaskStatus.TASK_FAILED)
    error_msg: str = Field(default="")
    progress_rate: float = Field(default=0.0)
    time_cost: int = Field(default=0)


class TotalJobDetails(BaseModel):
    """JobDetails"""

    total_jobs: int = Field(default=0)
    failed_jobs: int = Field(default=0)
    stopped_jobs: int = Field(default=0)
    finished_jobs: int = Field(default=0)
    running_jobs: int = Field(default=0)
    data: List[JobDetail] = Field(default=[])


class BatchTaskInfo(BaseModel):
    """BatchTaskInfo"""

    job_details: TotalJobDetails = Field(default=None)
