# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Tuple, Optional, List

from agent_builder.agent_evolving.agent_rl.config.runtime_config import (
    RolloutConfig,
    TrainingConfig,
)
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.service.backend_proxy import (
    FlaskProxyServer,
)
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.service.task_manager import (
    TrainingTaskManager,
    TaskStatus,
)
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.verl.entrypoint import (
    init_inf,
)
from agent_builder.agent_evolving.agent_rl.src.utils.logging import get_logger

logger = get_logger(__name__)


class ModelService:
    """
    Model Service对基线模型、检查点进行管理，并对Rollout代理进行管理：
        1. 基线模型、检查点加载和保存
        2. 训练服务初始化
        3. 维护Rollout推理代理，在给定的proxy_endpoint上提供Rollout代理服务
    """

    def __init__(
        self, task_manager: TrainingTaskManager, llm_timeout_seconds: float = 30000
    ) -> None:
        """Initialize the model service manager."""
        self.task_manager = task_manager
        self.proxy_server = FlaskProxyServer(llm_timeout_seconds=llm_timeout_seconds)

    @classmethod
    def load_checkpoint(cls, s3_model_path: str, s3_ckpt_path) -> Tuple[str, str]:
        """Load pre-training model and checkpoint from s3 bucket to efs."""
        pass

    @classmethod
    def save_checkpoint(cls, efs_ckpt_path: str, s3_ckpt_path: str) -> None:
        """Transfer the checkpoint from efs to s3 bucket."""
        pass

    async def start_proxy_server(
        self, task_id: str, service_address: List[str], proxy_endpoint: str
    ) -> Optional[str]:
        """
        Configure the proxy endpoint and start the rollout proxy for the given task.
        The proxy can implement llm request forwarding and routing.
        """
        try:
            task = self.task_manager.get_task(task_id)
            if task.status != TaskStatus.INITIALIZING:
                logger.warning(
                    f"Skipping start proxy for task {task_id}: "
                    f"invalid status {task.status}, must be {TaskStatus.INITIALIZING}."
                )
                return task_id
            logger.info(f"Start proxy for task {task_id}.")
            self.proxy_server.update_endpoint(proxy_endpoint)
            await self.proxy_server.start()
            self.proxy_server.update_backend_servers(service_address)
            self.task_manager.set_model_service(
                task_id, service_address, proxy_endpoint
            )
            self.task_manager.update_task_status(task_id, TaskStatus.MODEL_READY)
            return task_id
        except Exception as e:
            error_msg = (
                f"Failed to start rollout proxy service for task {task_id}: {e}."
            )
            logger.error(error_msg)
            self.task_manager.update_task_status(task_id, TaskStatus.FAILED, error_msg)
            raise RuntimeError(error_msg) from e

    def start_model_service(
        self, task_id: str, train_config: TrainingConfig, rollout_config: RolloutConfig
    ) -> Optional[Tuple[str, List[str]]]:
        """Start and register testing rollout service for a task and return the testing service address."""
        task_id = self.task_manager.create_task(task_id, train_config, rollout_config)
        try:
            task = self.task_manager.get_task(task_id)
            if task is None:
                logger.error(f"Task {task_id} not found after creation")
                raise RuntimeError("Failed to create task")
            if task.status:
                logger.warning(
                    f"The status of task {task_id} is already {task.status}, "
                    f"skipping this calling."
                )
                return task_id, self.task_manager.get_task(
                    task_id
                ).testing_service_address
            service_address = init_inf(
                task_id=task_id, train_cfg=train_config, rollout_cfg=rollout_config
            )
            self.task_manager.update_task_status(task_id, TaskStatus.INITIALIZING)
            return task_id, service_address
        except Exception as e:
            error_msg = f"Failed to start model service for task {task_id}: {e}."
            logger.error(error_msg)
            self.task_manager.update_task_status(task_id, TaskStatus.FAILED, error_msg)
            raise RuntimeError(error_msg) from e
