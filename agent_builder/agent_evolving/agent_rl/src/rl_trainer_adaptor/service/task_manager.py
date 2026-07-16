# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Optional, Dict, Any, List

from agent_builder.agent_evolving.agent_rl.config.runtime_config import (
    RolloutConfig,
    TrainingConfig,
)
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.coordinator.base import (
    TaskStatus,
)
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.verl.entrypoint import (
    get_trainer_status,
    get_trainer_error,
)
from agent_builder.agent_evolving.agent_rl.src.utils.logging import get_logger
from pydantic import BaseModel, Field

logger = get_logger(__name__)


class TrainingTask(BaseModel):
    """
    Core data structure representing a single training task.
    Stores task status, progress, model service info, training configs,
    and error details.
    """

    task_id: str = Field(
        pattern=r"^[a-zA-Z0-9_\-]+$",
        description="Only letters, numbers, underscores and hyphens are allowed in task id.",
    )
    status: Optional[TaskStatus] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Model service fields
    testing_service_address: List[str] = None  # host:port
    proxy_endpoint: Optional[str] = None

    # Training config fields
    train_config: TrainingConfig = None
    rollout_config: RolloutConfig = None

    # Error info
    error_message: Optional[str] = None

    def update_status(
        self, status: TaskStatus, error_message: Optional[str] = None
    ) -> None:
        """Update task status and timestamps."""
        current = self.status if hasattr(self, "status") else None
        valid_transitions = {
            None: [TaskStatus.INITIALIZING, TaskStatus.FAILED],
            TaskStatus.INITIALIZING: [TaskStatus.MODEL_READY, TaskStatus.FAILED],
            TaskStatus.MODEL_READY: [TaskStatus.RUNNING, TaskStatus.FAILED],
            TaskStatus.RUNNING: [TaskStatus.FAILED, TaskStatus.FINISHED],
        }
        allowed = valid_transitions.get(current, [])
        if status not in allowed:
            raise ValueError(f"Invalid status transition from {current} to {status}")
        self.status = status
        self.updated_at = datetime.now(tz=timezone.utc)
        if error_message:
            self.error_message = error_message
        logger.info(f"Task {self.task_id} status updated to {status}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert task data to a dict for API responses."""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "testing_service_address": self.testing_service_address,
            "proxy_endpoint": self.proxy_endpoint,
            "train_config": self.train_config.model_dump(),
            "rollout_config": self.rollout_config.model_dump(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error_message": self.error_message,
        }


class TrainingTaskManager:
    """
    Thread-safe manager for training task creation, update, and lookup.
    """

    def __init__(self):
        self._tasks: Dict[str, TrainingTask] = {}
        self._lock = Lock()

    def create_task(
        self, task_id: str, train_config: TrainingConfig, rollout_config: RolloutConfig
    ) -> Optional[str]:
        """Create a new training task and return its task ID."""
        if task_id in self._tasks:
            logger.info(f"Training task {task_id} already exist, skip create task.")
            return task_id
        if self._tasks:
            raise RuntimeError(
                f"The training task {next(iter(self._tasks))} already exist,"
                "only support one training task running."
            )
        if not task_id:
            task_id = str(uuid.uuid4())
            logger.info(f"task_id is empty, create task_id {task_id} for this task.")
        task = TrainingTask(
            task_id=task_id,
            status=None,
            train_config=train_config,
            rollout_config=rollout_config,
        )
        with self._lock:
            self._tasks[task_id] = task
        logger.info(f"Created new task {task_id}.")
        return task_id

    def get_task(self, task_id: str) -> Optional[TrainingTask]:
        """Retrieve a task by task ID."""
        with self._lock:
            if task_id not in self._tasks:
                raise ValueError(f"Task {task_id} not found.")
            task = self._tasks.get(task_id)
            if task.status == TaskStatus.RUNNING:
                task.status = get_trainer_status(task_id)
                if task.status == TaskStatus.FAILED:
                    if not task.error_message:
                        task.error_message = get_trainer_error(task_id)
            return self._tasks.get(task_id)

    def update_task_status(
        self, task_id: str, status: TaskStatus, error_message: Optional[str] = None
    ):
        """Update the status of an existing task."""
        task = self.get_task(task_id)
        if task.status == TaskStatus.FAILED and status == TaskStatus.FAILED:
            logger.info(f"Task {task_id} already failed, ignore new failure.")
            return
        if task.status == TaskStatus.FINISHED:
            logger.info(f"Task {task_id} already finished, ignore new status {status}.")
            return
        task.update_status(status, error_message)

    def set_model_service(
        self, task_id: str, service_address: List[str], proxy_endpoint: str
    ) -> None:
        """Bind model inference service address to a task."""
        task = self.get_task(task_id)
        task.testing_service_address = service_address
        if proxy_endpoint:
            task.proxy_endpoint = proxy_endpoint
        task.updated_at = datetime.now(tz=timezone.utc)

    def delete_task(self, task_id: str) -> TrainingTask:
        """Remove a task from the manager."""
        task = self.get_task(task_id)
        if task.status not in [TaskStatus.FAILED, TaskStatus.FINISHED]:
            raise RuntimeError(
                f"Cannot delete task {task_id} with status {task.status}. "
                f"Only FAILED or FINISHED tasks can be deleted, please stop the training first."
            )
        with self._lock:
            self._tasks.pop(task_id)
        logger.info(f"Task {task_id} is deleted.")
        return task
