# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from abc import ABC
from typing import List

import requests
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.coordinator.base import (
    TaskStatus,
)
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.coordinator.data_coordinator import (
    RLTrainerDaemon,
)
from agent_builder.agent_evolving.agent_rl.src.utils.logging import get_logger
from agent_builder.agent_evolving.agent_rl.src.utils.sampler import create_rl_sampler
from omegaconf import DictConfig
from torchdata.stateful_dataloader import StatefulDataLoader
from tqdm import tqdm

logger = get_logger(__name__)


class MainTrainer(ABC):
    """Abstract main trainer class implemented through specific RL trainer instances."""

    def __init__(
        self, rl_trainer, config: DictConfig, collate_fn=None, train_sampler=None
    ):
        self.rl_trainer = rl_trainer
        self.config = config
        self.train_dataset = rl_trainer.train_dataset
        self.val_dataset = rl_trainer.val_dataset
        self.agent_mode_daemon = RLTrainerDaemon(config, rl_trainer.tokenizer)

        num_workers = self.config.data["dataloader_num_workers"]
        gen_batch_size = self.config.data["train_batch_size"]
        if train_sampler is None:
            train_sampler = create_rl_sampler(self.config.data, self.train_dataset)
        self.train_dataloader = StatefulDataLoader(
            dataset=self.train_dataset,
            batch_size=gen_batch_size,
            num_workers=num_workers,
            drop_last=True,
            collate_fn=collate_fn,
            sampler=train_sampler,
        )
        self.val_dataloader = StatefulDataLoader(
            dataset=self.val_dataset,
            batch_size=len(self.val_dataset),
            num_workers=num_workers,
            shuffle=self.config.data["validation_shuffle"],
            drop_last=False,
            collate_fn=collate_fn,
        )
        self.status = TaskStatus.RUNNING
        self.error_msg = ""

    def validate(self, proxy_endpoint, env_info):
        """Validation method to get validation metrics."""
        server_addresses = self.rl_trainer.wake_up_rollout()
        self.update_backends(proxy_endpoint, server_addresses)
        if len(self.val_dataloader) != 1:
            raise ValueError("please set the validation dataset in one batch")
        validation_rl_data = next(iter(self.val_dataloader))
        validation_metrics = self.agent_mode_daemon.validate_sync(
            validation_rl_data, env_info
        )
        logger.info(
            f"Global step {self.rl_trainer.global_steps} validation result: {validation_metrics}"
        )
        self.rl_trainer.sleep_rollout()

    def update_backends(self, proxy_endpoint: str, servers: List[str]) -> None:
        """Update backend server list via proxy service.
        Raises:
            requests.RequestException: HTTP / network error
            ValueError: invalid response content
        """
        if isinstance(servers, str):
            servers = [servers]
        url = f"{proxy_endpoint}/proxy/backends"
        payload = {"servers": servers}
        try:
            resp = requests.post(url, json=payload, timeout=5)
            resp.raise_for_status()
        except Exception as e:
            logger.error("Failed to update backends: %s", e)
            raise
        logger.info("Update backends success: %s", servers)

    def fit(self, proxy_endpoint, env_info):
        """Main training loop with progress tracking and validation."""
        if hasattr(self.rl_trainer, "setup_logger"):
            self.rl_trainer.setup_logger()

        self.rl_trainer.global_steps = 0
        if hasattr(self.rl_trainer, "load_checkpoint"):
            self.rl_trainer.load_checkpoint()

        total_training_steps = (
            len(self.train_dataloader) * self.config.trainer["total_epochs"]
        )
        progress_bar = tqdm(
            total=total_training_steps,
            initial=self.rl_trainer.global_steps,
            desc="Training Progress",
        )
        self.rl_trainer.global_steps += 1
        if self.config["trainer"]["val_before_train"]:
            logger.info("Validate before training.")
            self.validate(proxy_endpoint, env_info)
        for epoch in range(self.config.trainer["total_epochs"]):
            for batch_dict in self.train_dataloader:
                try:
                    logger.info(
                        f"Training Started at step {self.rl_trainer.global_steps}."
                    )
                    origin_batch = self.rl_trainer.get_rl_format_data(batch_dict)
                    is_last_step = self.rl_trainer.global_steps >= total_training_steps
                    self.update_backends(
                        proxy_endpoint, self.rl_trainer.wake_up_rollout()
                    )
                    device = batch_dict["fake_ids"].device
                    assembled_batch, non_tensor_dict = (
                        self.agent_mode_daemon.run_demon_loop_sync(
                            rl_data=batch_dict,
                            device=device,
                            env_info=env_info,
                        )
                    )
                    batch = self.rl_trainer.get_rl_format_data(assembled_batch)
                    batch.non_tensor_batch.update(non_tensor_dict)
                    self.rl_trainer.sleep_rollout()
                    metrics = self.rl_trainer.train_step(origin_batch, batch)
                    if self.config.trainer["test_freq"] > 0 and (
                        is_last_step
                        or self.rl_trainer.global_steps
                        % self.config.trainer["test_freq"]
                        == 0
                    ):
                        self.validate(proxy_endpoint, env_info)
                    if self.config.trainer["save_freq"] > 0 and (
                        is_last_step
                        or self.rl_trainer.global_steps
                        % self.config.trainer["save_freq"]
                        == 0
                    ):
                        self.rl_trainer.save_checkpoint()
                    metrics.update(
                        {
                            "training/global_step": self.rl_trainer.global_steps,
                            "training/epoch": epoch,
                        }
                    )
                    if hasattr(self.rl_trainer, "log_metrics"):
                        self.rl_trainer.log_metrics(
                            metrics, self.rl_trainer.global_steps
                        )
                    progress_bar.update(1)
                    self.rl_trainer.global_steps += 1
                    if is_last_step:
                        progress_bar.close()
                        logger.info(
                            f"Training finished at step {self.rl_trainer.global_steps}."
                        )
                        self.status = TaskStatus.FINISHED
                        return
                except IndexError as e:
                    logger.warning(
                        f"Exception occurred, IndexError during batch assembling: {e}"
                    )
                except Exception as e:
                    logger.error(
                        f"Unexpected exception occurred, save checkpoint and exit: {e}"
                    )
                    self.rl_trainer.save_checkpoint()
                    self.error_msg = str(e)
                    self.status = TaskStatus.FAILED
                    raise
