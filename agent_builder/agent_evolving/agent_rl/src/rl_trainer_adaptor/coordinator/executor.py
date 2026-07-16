# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import random
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Dict

import torch
from agent_builder.agent_evolving.agent_rl.src.utils.logging import get_logger
from codetiming import Timer

logger = get_logger(__name__)


@contextmanager
def _timer(name: str, timing_raw: Dict[str, float]):
    """Context manager for timing code execution."""
    with Timer(name=name, logger=None) as timer:
        yield
    if name not in timing_raw:
        timing_raw[name] = 0
    timing_raw[name] += timer.last


class TrainingExecutor(ABC):
    """Abstract base class for training executors with common training workflow."""

    def __init__(self, mini_batch_size):
        self.mini_batch_size = mini_batch_size

    @abstractmethod
    def sleep_rollout(self):
        """Puts the asynchronous rollout manager into a sleep state to pause rollout generation."""
        pass

    @abstractmethod
    def wake_up_rollout(self):
        """Wakes up the asynchronous rollout manager and returns the active rollout server addresses."""
        pass

    @abstractmethod
    def save_checkpoint(self):
        """Saves the current training state and model parameters
        using the base trainer checkpointing logic.
        """
        pass

    @abstractmethod
    def setup_logger(self):
        """Initializes the experiment logger with the current
        training configuration and returns the Tracking instance.
        """
        pass

    @abstractmethod
    def log_metrics(self, metrics, step):
        """Logs the given metrics to the configured tracking backend at the specified global step."""
        pass

    @abstractmethod
    def compute_baseline(self, origin_batch, batch):
        """Optionally computes a REMAX-style baseline by generating
        non-sampled sequences and attaching baseline rewards to the batch.
        """
        pass

    @abstractmethod
    def compute_reward(self, batch, metrics):
        """Prepares response masks and global token statistics,
        and optionally computes reward model scores for the batch.
        """
        pass

    @abstractmethod
    def compute_old_log_prob(self, batch, metrics):
        """Pads the batch, computes the actor's log probabilities and entropy,
        logs entropy metrics, and merges results back into the batch.
        """
        pass

    @abstractmethod
    def compute_reference_log_prob(self, batch):
        """Computes and attaches reference policy log probabilities
        to the batch when a reference policy is enabled.
        """
        pass

    @abstractmethod
    def compute_values(self, batch):
        """Computes and attaches critic value estimates to the batch when a critic is enabled."""
        pass

    @abstractmethod
    def compute_advantages(self, batch, metrics):
        """Unpads the batch, optionally applies a KL penalty, and computes
        token-level advantages according to the configured estimator.
        """
        pass

    @abstractmethod
    def update_critic(self, batch, metrics):
        """Updates the critic network with the current batch and merges
        the resulting metrics into the global metrics dictionary.
        """
        pass

    @abstractmethod
    def update_actor(self, batch, metrics):
        """Updates the actor policy after the critic warmup phase and merges
        the resulting metrics into the global metrics dictionary.
        """
        pass

    @abstractmethod
    def process_metrics(self, batch, metrics, timing_raw):
        """Augments the metrics dictionary with data statistics and throughput
        metrics derived from the current batch and timing information.
        """
        pass

    @abstractmethod
    def balance_batch(self, batch, metrics):
        """Optionally rebalances the batch according to trainer configuration
        by delegating to the base batch balancing routine.
        """
        pass

    @abstractmethod
    def get_rl_format_data(self, batch_dict):
        """Convert batch data from dict format to rl training format,
        for example, in VERL the data will be converted to DataProto.
        """
        pass

    def train_step(self, origin_batch, batch):
        """Main training step broken down into sub-steps with timing."""
        metrics = {}
        timing_raw = {}
        logger.info("Starting training step...")
        with _timer("step", timing_raw):
            with _timer("gen_max", timing_raw):
                batch = self.compute_baseline(origin_batch, batch)
            with _timer("reward", timing_raw):
                batch = self.compute_reward(batch, metrics)
            with _timer("old_log_prob", timing_raw):
                batch = self.compute_old_log_prob(batch, metrics)
            with _timer("ref", timing_raw):
                batch = self.compute_reference_log_prob(batch)
            with _timer("values", timing_raw):
                batch = self.compute_values(batch)
            with _timer("adv", timing_raw):
                batch = self.compute_advantages(batch, metrics)
            logger.info(f"Before data alignment, Batch size: {len(batch)}")
            with _timer("data_alignment", timing_raw):
                if "is_drop_mask" in batch.batch:
                    keep_indices = (~batch.batch["is_drop_mask"]).nonzero(
                        as_tuple=True
                    )[0]
                    metrics["training/n_triplets_prompt_too_long"] = (
                        batch.batch["is_drop_mask"].shape[0] - keep_indices.shape[0]
                    )
                    batch = batch[keep_indices]
                    logger.info(
                        f"Dropped {metrics['training/n_triplets_prompt_too_long']} samples with long prompts"
                    )
                mini_batch_size = self.mini_batch_size
                n_transition = len(batch)
                if n_transition % mini_batch_size != 0:
                    random_indices = list(range(n_transition))
                    random.shuffle(random_indices)
                    batch.reorder(torch.tensor(random_indices).type(torch.int32))
                    n_remained_transition = (
                        n_transition // mini_batch_size * mini_batch_size
                    )
                    batch = batch[list(range(n_remained_transition))]
                    metrics["training/n_triplets_dropped_remainder"] = (
                        n_transition - n_remained_transition
                    )
                    logger.info(
                        f"Data alignment: {n_transition} -> {n_remained_transition} samples"
                    )
                else:
                    metrics["training/n_triplets_dropped_remainder"] = 0
            with _timer("balance_batch", timing_raw):
                self.balance_batch(batch, metrics)
            with _timer("update_critic", timing_raw):
                self.update_critic(batch, metrics)
            with _timer("update_actor", timing_raw):
                self.update_actor(batch, metrics)
        metrics = self.process_metrics(batch, metrics, timing_raw)
        return metrics
