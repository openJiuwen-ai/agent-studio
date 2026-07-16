# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Optional

from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.coordinator.base import (
    TaskStatus,
)
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.service.task_manager import (
    TrainingTaskManager,
    TrainingTask,
)
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.verl.entrypoint import (
    start_trainer,
    stop_ray_service,
)
from agent_builder.agent_evolving.agent_rl.src.utils.logging import get_logger

logger = get_logger(__name__)


class TrainingService:
    """
    Training service.
    Responsible for starting training task and stopping.
    Acts as the second step of the two-phase training workflow.
    """

    def __init__(self, task_manager: TrainingTaskManager):
        """Initialize training service with a task manager."""
        self.task_manager = task_manager

    def start_training(self, task_id: str, env_info) -> Optional[str]:
        """Start the training task when the rollout proxy is ready."""
        try:
            task = self.task_manager.get_task(task_id)
            if task.status != TaskStatus.MODEL_READY:
                logger.warning(
                    f"Skipping training start for task {task_id}: "
                    f"current status is {task.status}, must be {TaskStatus.MODEL_READY}."
                )
                return task_id
            self.task_manager.update_task_status(task_id, TaskStatus.RUNNING)
            logger.info(f"Training started for task {task_id}.")
            start_trainer(task_id, task.proxy_endpoint, env_info)
            return task_id
        except Exception as e:
            error_msg = f"Failed to start training for task {task_id}: {e}."
            logger.error(error_msg)
            self.task_manager.update_task_status(task_id, TaskStatus.FAILED, error_msg)
            raise RuntimeError(error_msg) from e

    def stop_training(self, task_id: str) -> Optional[TrainingTask]:
        """Stop a running training task."""
        try:
            task = self.task_manager.get_task(task_id)
            error_msg = f"The task {task_id} has been stopped manually."
            logger.info(
                f"Stop the task {task_id}, the info of this task: {task.to_dict()}."
            )
            stop_ray_service(task_id)
            self.task_manager.update_task_status(task_id, TaskStatus.FAILED, error_msg)
            self.task_manager.delete_task(task_id)
            return task
        except Exception as e:
            error_msg = f"Failed to stop training for task {task_id}: {e}."
            logger.error(error_msg)
            self.task_manager.update_task_status(task_id, TaskStatus.FAILED, error_msg)
            raise RuntimeError(error_msg) from e
