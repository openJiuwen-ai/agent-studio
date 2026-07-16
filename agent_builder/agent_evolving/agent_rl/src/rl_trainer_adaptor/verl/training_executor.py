# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from copy import deepcopy

import torch
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.coordinator.executor import (
    TrainingExecutor,
)
from omegaconf import OmegaConf
from tensordict import TensorDict
from verl import DataProto
from verl.protocol import pad_dataproto_to_divisor, unpad_dataproto
from verl.trainer.ppo.core_algos import agg_loss
from verl.trainer.ppo.metric_utils import (
    compute_data_metrics,
    compute_throughout_metrics,
)
from verl.trainer.ppo.ray_trainer import AdvantageEstimator, RayPPOTrainer
from verl.trainer.ppo.ray_trainer import (
    apply_kl_penalty,
    compute_response_mask,
    compute_advantage,
)
from verl.utils.metric import reduce_metrics
from verl.utils.tracking import Tracking


class VerlTrainingExecutor(TrainingExecutor, RayPPOTrainer):
    """Verl training executor implementing TrainingExecutor abstract class"""

    def __init__(
        self,
        config,
        tokenizer,
        processor,
        role_worker_mapping,
        resource_pool_manager,
        ray_worker_group_cls,
        reward_fn,
        val_reward_fn,
        train_dataset,
        val_dataset,
        collate_fn,
        train_sampler,
    ):

        TrainingExecutor.__init__(
            self, config.actor_rollout_ref.actor.ppo_mini_batch_size
        )
        RayPPOTrainer.__init__(
            self,
            config=config,
            tokenizer=tokenizer,
            processor=processor,
            role_worker_mapping=role_worker_mapping,
            resource_pool_manager=resource_pool_manager,
            ray_worker_group_cls=ray_worker_group_cls,
            reward_fn=reward_fn,
            val_reward_fn=val_reward_fn,
            train_dataset=train_dataset,
            val_dataset=val_dataset,
            collate_fn=collate_fn,
            train_sampler=train_sampler,
        )

        self.global_steps = 0
        self.use_reference_policy = (
            hasattr(config, "use_reference_policy") and config.use_reference_policy
        )
        self.use_critic = hasattr(config, "use_critic") and config.use_critic
        self.use_rm = hasattr(config, "use_rm") and config.use_rm
        self.pad_size = None

    def sleep_rollout(self):
        """Puts the asynchronous rollout manager into a sleep state to pause rollout generation."""
        self.async_rollout_manager.sleep()

    def wake_up_rollout(self):
        """Wakes up the asynchronous rollout manager and returns the active rollout server addresses."""
        self.async_rollout_manager.wake_up()
        return self.async_rollout_manager.server_addresses

    def setup_logger(self):
        """Initializes the experiment logger with the current
        training configuration and returns the Tracking instance.
        """
        self.logger = Tracking(
            project_name=self.config.trainer.project_name,
            experiment_name=self.config.trainer.experiment_name,
            default_backend=self.config.trainer.logger,
            config=OmegaConf.to_container(self.config, resolve=True),
        )
        return self.logger

    def log_metrics(self, metrics, step):
        """Logs the given metrics to the configured tracking backend at the specified global step."""
        if self.logger:
            self.logger.log(data=metrics, step=step)

    def compute_baseline(self, origin_batch, batch):
        """Optionally computes a REMAX-style baseline by generating
        non-sampled sequences and attaching baseline rewards to the batch.
        """
        if self.config.algorithm.adv_estimator == AdvantageEstimator.REMAX:
            gen_baseline_batch = deepcopy(origin_batch)
            gen_baseline_batch.meta_info["do_sample"] = False
            gen_baseline_output = self.actor_rollout_wg.generate_sequences(
                gen_baseline_batch
            )
            batch = batch.union(gen_baseline_output)
            reward_baseline_tensor = self.reward_fn(batch)
            reward_baseline_tensor = reward_baseline_tensor.sum(dim=-1)
            batch.pop(batch_keys=list(gen_baseline_output.batch.keys()))
            batch.batch["reward_baselines"] = reward_baseline_tensor
            del gen_baseline_batch, gen_baseline_output
        return batch

    def compute_reward(self, batch, metrics):
        """Prepares response masks and global token statistics,
        and optionally computes reward model scores for the batch.
        """
        batch.non_tensor_batch["uid"] = batch.non_tensor_batch["data_id_list"]
        batch.batch["response_mask"] = compute_response_mask(batch)
        batch.meta_info["global_token_num"] = torch.sum(
            batch.batch["attention_mask"], dim=-1
        ).tolist()
        if self.use_rm:
            reward_tensor = self.rm_wg.compute_rm_score(batch)
            batch = batch.union(reward_tensor)
        return batch

    def compute_old_log_prob(self, batch, metrics):
        """Pads the batch, computes the actor's log probabilities and entropy,
        logs entropy metrics, and merges results back into the batch.
        """
        batch, pad_size = pad_dataproto_to_divisor(
            batch, self.actor_rollout_wg.world_size
        )
        self.pad_size = pad_size
        old_log_prob = self.actor_rollout_wg.compute_log_prob(batch)
        entropys = old_log_prob.batch["entropys"]
        response_masks = batch.batch["response_mask"]

        loss_agg_mode = self.config.actor_rollout_ref.actor.loss_agg_mode
        entropy_loss = agg_loss(
            loss_mat=entropys, loss_mask=response_masks, loss_agg_mode=loss_agg_mode
        )
        old_log_prob_metrics = {"actor/entropy_loss": entropy_loss.detach().item()}
        metrics.update(old_log_prob_metrics)

        old_log_prob.batch.pop("entropys")
        batch = batch.union(old_log_prob)
        return batch

    def compute_reference_log_prob(self, batch):
        """Computes and attaches reference policy log probabilities
        to the batch when a reference policy is enabled.
        """
        if self.use_reference_policy:
            ref_log_prob = self.ref_policy_wg.compute_ref_log_prob(batch)
            batch = batch.union(ref_log_prob)
        return batch

    def compute_values(self, batch):
        """Computes and attaches critic value estimates to the batch when a critic is enabled."""
        if self.use_critic:
            values = self.critic_wg.compute_values(batch)
            batch = batch.union(values)
        return batch

    def compute_advantages(self, batch, metrics):
        """Unpads the batch, optionally applies a KL penalty, and computes
        token-level advantages according to the configured estimator.
        """
        batch = unpad_dataproto(batch, pad_size=self.pad_size)
        if (
            hasattr(self.config.algorithm, "use_kl_in_reward")
            and self.config.algorithm.use_kl_in_reward
        ):
            batch, kl_metrics = apply_kl_penalty(
                batch,
                kl_ctrl=getattr(self, "kl_ctrl_in_reward", None),
                kl_penalty=self.config.algorithm.kl_penalty,
            )
            metrics.update(kl_metrics)
        else:
            batch.batch["token_level_rewards"] = batch.batch["token_level_scores"]

        batch = compute_advantage(
            batch,
            adv_estimator=self.config.algorithm.adv_estimator,
            gamma=self.config.algorithm.gamma,
            lam=self.config.algorithm.lam,
            num_repeat=self.config.actor_rollout_ref.rollout.n,
            norm_adv_by_std_in_grpo=self.config.algorithm.get(
                "norm_adv_by_std_in_grpo", True
            ),
            config=self.config.algorithm,
        )
        return batch

    def update_critic(self, batch, metrics):
        """Updates the critic network with the current batch and merges
        the resulting metrics into the global metrics dictionary.
        """
        if self.use_critic:
            critic_output = self.critic_wg.update_critic(batch)
            critic_output_metrics = reduce_metrics(critic_output.meta_info["metrics"])
            metrics.update(critic_output_metrics)
        return metrics

    def update_actor(self, batch, metrics):
        """Updates the actor policy after the critic warmup phase and merges
        the resulting metrics into the global metrics dictionary.
        """
        if self.config.trainer.critic_warmup <= self.global_steps:
            actor_output = self.actor_rollout_wg.update_actor(batch)
            actor_output_metrics = reduce_metrics(actor_output.meta_info["metrics"])
            metrics.update(actor_output_metrics)
        return metrics

    def process_metrics(self, batch, metrics, timing_raw):
        """Augments the metrics dictionary with data statistics and throughput
        metrics derived from the current batch and timing information.
        """
        metrics.update(compute_data_metrics(batch=batch, use_critic=self.use_critic))
        n_gpus = self.resource_pool_manager.get_n_gpus()
        metrics.update(
            compute_throughout_metrics(
                batch=batch, timing_raw=timing_raw, n_gpus=n_gpus
            )
        )
        return metrics

    def get_rl_format_data(self, batch_dict):
        """Convert batch data from dict format to rl training format,
        for example, in VERL the data will be converted to DataProto.
        """
        if isinstance(batch_dict, TensorDict):
            return DataProto(batch=batch_dict)
        if isinstance(batch_dict, dict):
            return DataProto.from_single_dict(batch_dict)
        raise TypeError(f"unsupported data type: {type(batch_dict)}")

    def save_checkpoint(self):
        """Saves the current training state and model parameters
        using the base trainer checkpointing logic.
        """
        super()._save_checkpoint()

    def load_checkpoint(self):
        """Restores training state and model parameters from
        the latest checkpoint using the base trainer logic.
        """
        super()._load_checkpoint()

    def balance_batch(self, batch, metrics):
        """Optionally rebalances the batch according to trainer configuration
        by delegating to the base batch balancing routine.
        """
        if (
            hasattr(self.config.trainer, "balance_batch")
            and self.config.trainer.balance_batch
        ):
            super()._balance_batch(batch, metrics=metrics)
