# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import asyncio
import uuid
from typing import Dict, List, Any, Tuple

import numpy as np
import torch
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.coordinator.base import (
    RLTask,
)
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.coordinator.processors_registry import (
    ProcessorsRegistry,
)
from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.coordinator.resource_cache import (
    DataStore,
    ProcessRolloutMsg,
)
from agent_builder.agent_evolving.agent_rl.src.runtime_and_sampler_adaptor.adaptor import (
    ParallelRuntimeExecutor,
)
from agent_builder.agent_evolving.agent_rl.src.utils.logging import get_logger
from tensordict import TensorDict

logger = get_logger(__name__)


class RLDataProto:
    """A utility class for converting rollout data into padded token sequences,
    attention masks, reward-aligned token-level scores, and structured
    TensorDict batches required for RL training.

    It provides:
    - Left/right padding utilities for prompts and responses
    - Token-level reward score construction
    - Component generation from raw rollout objects
    - Assembly of full tensor batches and associated metadata

    This class serves as the preprocessing bridge between collected rollout
    trajectories and the model-facing training data format.
    """

    def __init__(self, max_prompt_length, pad_token_id, max_response_length):
        self.max_prompt_length = max_prompt_length
        self.pad_token_id = pad_token_id
        self.max_response_length = max_response_length

    @staticmethod
    def get_left_padded_ids_and_attention_mask(
        ids: List[int], max_length: int, pad_token_id: int
    ):
        """Left-pads the input ID sequence to a fixed length and returns
        the padded IDs along with the corresponding attention mask.
        """
        seq_len = len(ids)

        if seq_len >= max_length:
            trimmed = ids[-max_length:]
            attention_mask = [1] * max_length
            return trimmed, attention_mask

        pad_len = max_length - seq_len
        padded_ids = [pad_token_id] * pad_len + ids
        attention_mask = [0] * pad_len + [1] * seq_len
        return padded_ids, attention_mask

    @staticmethod
    def get_right_padded_ids_and_attention_mask(
        ids: List[int], max_length: int, pad_token_id: int
    ):
        """Right-pads the input ID sequence to a fixed length and returns
        the padded IDs along with the corresponding attention mask.
        """

        seq_len = len(ids)

        if seq_len >= max_length:
            trimmed = ids[:max_length]
            attention_mask = [1] * max_length
            return trimmed, attention_mask

        pad_len = max_length - seq_len
        padded_ids = ids + [pad_token_id] * pad_len
        attention_mask = [1] * seq_len + [0] * pad_len
        return padded_ids, attention_mask

    @staticmethod
    def create_token_level_scores(
        attention_mask: torch.Tensor,
        position_ids: torch.Tensor,
        scores: torch.Tensor,
        response_length: int,
    ) -> torch.Tensor:
        """Generates token-level reward scores by assigning each transition's
        reward to its final valid token position.
        """
        n_transition = attention_mask.size(0)
        token_scores = torch.zeros_like(attention_mask, dtype=scores.dtype)

        eos_positions = torch.argmax(position_ids * attention_mask, dim=-1)
        token_scores[torch.arange(n_transition), eos_positions] = scores

        return token_scores[:, -response_length:]

    @classmethod
    def _init_components(cls) -> Dict[str, List[Any]]:
        return {
            "input_ids": [],
            "input_attention_mask": [],
            "response_ids": [],
            "response_attention_mask": [],
            "rewards": [],
            "turn_indices": [],
            "is_drop": [],
            "data_ids": [],
        }

    @classmethod
    def _truncate_prompt_and_response(
        cls,
        prompt_ids: List[int],
        response_ids: List[int],
        max_prompt_length: int,
        max_response_length: int,
    ) -> Tuple[List[int], List[int], bool]:
        is_drop = len(prompt_ids) > max_prompt_length
        if is_drop:
            prompt_ids = prompt_ids[:max_prompt_length]

        if len(response_ids) > max_response_length:
            response_ids = response_ids[:max_response_length]

        return prompt_ids, response_ids, is_drop

    @classmethod
    def _append_component_item(
        cls,
        components: Dict[str, List[Any]],
        item: Dict[str, Any],
        data_id: Any,
    ) -> None:
        components["input_ids"].append(item["input_ids"])
        components["input_attention_mask"].append(item["input_attention_mask"])
        components["response_ids"].append(item["response_ids"])
        components["response_attention_mask"].append(item["response_attention_mask"])
        components["rewards"].append(item["rewards"])
        components["turn_indices"].append(item["turn_indices"])
        components["is_drop"].append(item["is_drop"])
        components["data_ids"].append(data_id)

    def assemble_tensor_batch(self, components: Dict[str, List], device) -> TensorDict:
        """Assembles padded input, response, masks, and computed token-level
        scores into a structured TensorDict batch for model training.
        """
        n_transition = len(components["input_ids"])

        input_ids = torch.LongTensor(components["input_ids"]).to(device)
        input_mask = torch.LongTensor(components["input_attention_mask"]).to(device)
        response_ids = torch.LongTensor(components["response_ids"]).to(device)
        response_mask = torch.LongTensor(components["response_attention_mask"]).to(
            device
        )

        seq_ids = torch.cat([input_ids, response_ids], dim=-1)
        attention_mask = torch.cat([input_mask, response_mask], dim=-1)
        position_ids = torch.clamp(torch.cumsum(attention_mask, dim=-1) - 1, min=0)

        scores = torch.tensor(components["rewards"], dtype=torch.bfloat16).to(device)
        token_scores = self.create_token_level_scores(
            attention_mask, position_ids, scores, response_ids.size(-1)
        )

        return TensorDict(
            {
                "prompts": input_ids,
                "responses": response_ids,
                "input_ids": seq_ids,
                "attention_mask": attention_mask,
                "position_ids": position_ids,
                "is_drop_mask": torch.BoolTensor(components["is_drop"]).to(device),
                "token_level_scores": token_scores.contiguous(),
            },
            batch_size=n_transition,
        )

    def generate_rl_batch(self, rollout_dict, device):
        """Builds the full RL training batch by generating components, assembling tensor structures,
        and returning both tensor and non-tensor metadata.
        """
        components = self.generate_components(
            rollout_dict, self.max_prompt_length, self.max_response_length
        )
        assembled_batch = self.assemble_tensor_batch(components, device)
        non_tensor_dict = {
            "data_id_list": np.array(components["data_ids"]),
            "turn_index_list": np.array(components["turn_indices"]),
        }
        return assembled_batch, non_tensor_dict

    def generate_components(self, rollout_dict, max_prompt_length, max_response_length):
        """Converts rollout sequences into padded token IDs, attention masks, rewards,
        and metadata components required for RL batch construction.
        """
        components = self._init_components()
        truncation_count = 0

        for task_id, rollout_list in rollout_dict.items():
            truncation_count += self._process_rollout_list(
                components=components,
                data_id=task_id,
                rollout_list=rollout_list,
                max_prompt_length=max_prompt_length,
                max_response_length=max_response_length,
            )

        components["truncation_count"] = truncation_count
        logger.info(
            f"Processed {len(components['input_ids'])} samples, truncated {truncation_count}"
        )
        return components

    def _process_rollout_list(
        self,
        components: Dict[str, List[Any]],
        data_id: Any,
        rollout_list: List[Any],
        max_prompt_length: int,
        max_response_length: int,
    ) -> int:
        truncation_count = 0
        for rollout in rollout_list:
            item, truncated = self._build_one_component_item(
                rollout=rollout,
                max_prompt_length=max_prompt_length,
                max_response_length=max_response_length,
            )
            self._append_component_item(components, item, data_id=data_id)
            if truncated:
                truncation_count += 1
        return truncation_count

    def _build_one_component_item(
        self,
        rollout: Any,
        max_prompt_length: int,
        max_response_length: int,
    ) -> Tuple[Dict[str, Any], bool]:
        prompt_ids, response_ids, is_drop = self._truncate_prompt_and_response(
            prompt_ids=rollout.input_prompt_ids,
            response_ids=rollout.output_response_ids,
            max_prompt_length=max_prompt_length,
            max_response_length=max_response_length,
        )

        padded_prompt, prompt_mask = self.get_left_padded_ids_and_attention_mask(
            prompt_ids, max_prompt_length, self.pad_token_id
        )
        padded_response, response_mask = self.get_right_padded_ids_and_attention_mask(
            response_ids, max_response_length, self.pad_token_id
        )

        item = {
            "input_ids": padded_prompt,
            "input_attention_mask": prompt_mask,
            "response_ids": padded_response,
            "response_attention_mask": response_mask,
            "rewards": rollout.reward,
            "turn_indices": rollout.turn_id,
            "is_drop": is_drop,
        }
        truncated = len(rollout.output_response_ids) > max_response_length
        return item, truncated


class RLTrainerDaemon:
    """A controller class that orchestrates the full rollout–feedback–update cycle
    for reinforcement learning with LLMs.

    This daemon manages:
    - Parallel rollout generation through worker executors
    - Multi-round task scheduling and state tracking
    - Rollout classification, validation, and sampling
    - Batch assembly for RL training via RLDataProto
    - Synchronous and asynchronous validation routines
    - Caching and merging of positive/negative rollouts across rounds

    It acts as the core loop coordinator, handling task submission,
    rollout collection, stop-condition checking, and construction of
    training-ready RL batches.
    """

    def __init__(self, config, tokenizer):
        self.config = config
        self._total_positive = 0
        self._total_negative = 0
        self._total_activate_num = 0
        self.round_state = []
        self._rollout_state = {}
        self.positive_cache = {}
        self.negative_cache = {}
        # Store parallel executor configuration
        self.tokenizer = tokenizer
        self.datastore = DataStore()
        self.processors_registry = ProcessorsRegistry()
        self.rldata_proto = RLDataProto(
            config["data"]["max_prompt_length"],
            tokenizer.pad_token_id,
            config["data"]["max_response_length"],
        )
        self.parallel_executor = None
        self._is_parallel_setup = False
        self.message_processer = ProcessRolloutMsg(tokenizer=tokenizer)

    @staticmethod
    def merge_caches(pos_cache, neg_cache):
        """Merges positive and negative rollout caches into a unified rollout dictionary keyed by UID."""
        rollout_dict = {}
        for uid in set(pos_cache.keys()) | set(neg_cache.keys()):
            rollout_dict[uid] = pos_cache.get(uid, []) + neg_cache.get(uid, [])
        return rollout_dict

    @classmethod
    def _infer_batch_size(cls, rl_data) -> int:
        """Infer batch size from rl_data."""
        return len(next(iter(rl_data.values())))

    @classmethod
    def _build_task_sample(cls, rl_data, index: int) -> Dict[str, Any]:
        """Build one task sample from rl_data."""
        return {key: rl_data[key][index] for key in rl_data}

    async def run_demon_loop(self, rl_data, device, env_info):
        """Run demon loop with parallel rollout generation."""
        logger.info("Setting up RL trainer data to datastore.")

        await self._setup_parallel(env_info)
        tasks_dic = self._build_initial_tasks(rl_data)

        self.clear_up_data()
        logger.info("Starting RL trainer demon loop with parallel execution.")

        try:
            await self._run_rounds(tasks_dic)
        except Exception as e:
            logger.error(f"Error in demon loop: {str(e)}")
            raise
        finally:
            await self._stop_parallel_executor_if_needed()

        rl_batch, merged_dict = self._build_rl_batch_from_caches(device)
        logger.info(
            f"Demon loop completed. Generated RL batch with data from {len(merged_dict)} rollouts"
        )
        return rl_batch

    def run_demon_loop_sync(self, rl_data, device, env_info):
        """Synchronous wrapper for run_demon_loop"""
        return asyncio.run(self.run_demon_loop(rl_data, device, env_info))

    async def validate(self, rl_data, env_info):
        """Performs a full validation pass by executing one batch of rollout tasks and computing validation metrics."""
        await self._initialize_parallel_processing(env_info)
        batch_size = len(next(iter(rl_data.values())))
        self.clear_up_data()
        tasks_dic = {}
        for i in range(batch_size):
            task = {key: rl_data[key][i] for key in rl_data}
            task_id = str(uuid.uuid4())
            tasks_dic[task_id] = RLTask(
                task_id=task_id, origin_task_id=task_id, task_sample=task, round_num=0
            )

        try:
            await self._submit_tasks_for_round(tasks_dic)
            collected_data = await self._wait_for_tasks_completion(round_id=0)
        except Exception as e:
            logger.error(f"Error in demon loop: {str(e)}")
            raise
        finally:
            if self.parallel_executor and self.parallel_executor.is_running():
                await self.parallel_executor.stop()
                logger.info("Parallel executor stopped during validation")

        global_rewards = []
        turn_num = []
        rewards = []
        for _, rollout_msg in collected_data.items():
            reward_list = rollout_msg.reward_list
            rewards.append(reward_list)
            turn_num.append(len(rollout_msg.rollout_info))
            global_rewards.append(rollout_msg.global_reward)
        return {
            "val/global_reward_mean": float(np.mean(global_rewards)),
            "val/sample_count": len(global_rewards),
            "val/average_turn_num": float(np.mean(turn_num)),
            "val/turn_num": turn_num,
            "val/reward_list": rewards,
        }

    def validate_sync(self, rl_data, env_info):
        """Synchronous wrapper for the asynchronous validation routine."""
        return asyncio.run(self.validate(rl_data, env_info))

    def clear_up_data(self):
        """Resets rollout-related caches, counters, and state for a fresh training or validation cycle."""
        self.round_state.clear()
        self._rollout_state.clear()
        self._total_positive = 0
        self._total_negative = 0
        self._total_activate_num = 0
        self.positive_cache.clear()
        self.negative_cache.clear()
        self.datastore.rollouts.clear()

    def _setup_parallel_executor(self):
        """Setup parallel executor with stored configuration."""
        if self._is_parallel_setup and self.parallel_executor is not None:
            return
        num_workers = self.config["trainer"]["runtime_parallel_num"]
        self.parallel_executor = ParallelRuntimeExecutor(
            data_store=self.datastore,
            num_workers=num_workers,
        )
        self._is_parallel_setup = True
        logger.info(f"Parallel executor setup with {num_workers} workers")

    async def _initialize_parallel_processing(self, env_info):
        """Initialize and start parallel processing."""
        self._setup_parallel_executor()
        if not self.parallel_executor.is_running():
            await self.parallel_executor.start(env_info)
            logger.info("Parallel executor started")

    async def _submit_tasks_for_round(self, tasks_dic):
        """Submit unfinished tasks for current round."""
        task_list = list(tasks_dic.values())
        await self._initialize_tasks(task_list)
        logger.info(f"Submitted {len(task_list)} tasks for current round")

    async def _initialize_tasks(self, task_list):
        """Queues tasks into the datastore and initializes rollout state tracking for each task."""
        for task in task_list:
            task_id = await self.datastore.queue_task(task)
            logger.info(f"Task {task_id} queued for execution")
            if task.origin_task_id not in self._rollout_state:
                self._rollout_state[task.origin_task_id] = {
                    "neg": 0,
                    "pos": 0,
                    "finished": False,
                }

    async def _wait_for_tasks_completion(
        self, round_id, max_wait_time: float = 300, poll_interval: float = 1
    ):
        """Waits for all rollout tasks to complete for a given round,
        polling the datastore and collecting results.
        """
        logger.info(f"Waiting for tasks completion in round {round_id}.")
        collected_data = {}

        while True:
            if self.datastore.is_finished():
                logger.info(f"All tasks complete ir execution in round {round_id}.")
                break

            current_data = await self.datastore.get_rollouts()
            if current_data:
                collected_data.update(current_data)
                logger.info(
                    f"Collected {len(current_data)} new rollouts in round {round_id}"
                )

            await asyncio.sleep(poll_interval)
        final_data = await self.datastore.get_rollouts()
        if final_data:
            collected_data.update(final_data)
            logger.info(
                f"Final collection: {len(final_data)} rollouts in round {round_id}"
            )
        logger.info(
            f"Total collected {len(collected_data)} rollouts in round {round_id}"
        )
        return collected_data

    def _update_rollout_state(self, round_id, collected_mdp):
        """Updates rollout caches, completion flags, and training
        statistics based on newly collected rollout results.
        """
        classifier_func = self.processors_registry.get_classifier(
            self.config["JiuwenRL"]["custom_fn"]["classifier"]
        )
        valid_func = self.processors_registry.get_validator(
            self.config["JiuwenRL"]["custom_fn"]["validator"]
        )
        finished_task = sum(len(m) for m in collected_mdp.values())
        active_task = 0

        for task_id, mdp_list in collected_mdp.items():
            pos_rollouts_with_reward, neg_rollouts_with_reward = classifier_func(
                mdp_list
            )
            active_task += 1
            self._total_activate_num += 1
            self._total_positive += len(pos_rollouts_with_reward)
            self._total_negative += len(neg_rollouts_with_reward)

            if neg_rollouts_with_reward:
                if task_id not in self.negative_cache:
                    self.negative_cache[task_id] = neg_rollouts_with_reward
                else:
                    self.negative_cache[task_id].extend(neg_rollouts_with_reward)
            if pos_rollouts_with_reward:
                if task_id not in self.positive_cache:
                    self.positive_cache[task_id] = pos_rollouts_with_reward
                else:
                    self.positive_cache[task_id].extend(pos_rollouts_with_reward)

            is_finish = valid_func(
                self.positive_cache.get(task_id, []),
                self.negative_cache.get(task_id, []),
            )

            if task_id not in self._rollout_state:
                self._rollout_state[task_id] = {"neg": 0, "pos": 0, "finished": False}
            self._rollout_state[task_id]["finished"] = is_finish
            self._rollout_state[task_id]["pos"] += len(pos_rollouts_with_reward)
            self._rollout_state[task_id]["neg"] += len(neg_rollouts_with_reward)

        self.round_state.append(
            {
                "round_id": round_id,
                "active_num_this_round": active_task,
                "finished_task_this_round": finished_task,
                "_total_activate_num": self._total_activate_num,
            }
        )

    async def _setup_parallel(self, env_info) -> None:
        await self._initialize_parallel_processing(env_info)

    def _build_initial_tasks(self, rl_data) -> Dict[str, Any]:
        """Build initial task dictionary from rl_data."""
        batch_size = self._infer_batch_size(rl_data)
        tasks_dic: Dict[str, Any] = {}

        for i in range(batch_size):
            task_id = str(uuid.uuid4())
            for _ in range(self.config["actor_rollout_ref"]["rollout"]["n"]):
                rollout_n_id = str(uuid.uuid4())
                task_sample = self._build_task_sample(rl_data, i)
                tasks_dic[rollout_n_id] = RLTask(
                    task_id=rollout_n_id,
                    origin_task_id=task_id,
                    task_sample=task_sample,
                    round_num=0,
                )

        return tasks_dic

    async def _run_rounds(self, tasks_dic: Dict[str, Any]) -> None:
        """Run rollout rounds until all tasks are finished or max rounds reached."""
        max_round = self.config["trainer"]["rollout_max_round"]

        for round_id in range(max_round):
            if not tasks_dic:
                logger.info("All tasks finished, ending demon loop")
                break

            logger.info(
                f"Starting round {round_id} with {len(tasks_dic)} unfinished tasks"
            )
            await self._submit_tasks_for_round(tasks_dic)

            collected_mdp = await self._collect_round_mdp(round_id)
            self._update_rollout_state(round_id, collected_mdp)

            tasks_dic, finished_count = self._filter_unfinished_tasks(tasks_dic)
            logger.info(
                f"Round {round_id}: {finished_count} tasks finished, {len(tasks_dic)} remaining"
            )

    async def _collect_round_mdp(self, round_id: int) -> Dict[str, Any]:
        """Collect rollout messages and build mdp data grouped by task_id."""
        collected_data = await self._wait_for_tasks_completion(round_id)
        collected_mdp: Dict[str, list] = {}

        for _, rollout_msg in collected_data.items():
            if len(rollout_msg.rollout_info):
                if rollout_msg.origin_task_id not in collected_mdp:
                    collected_mdp[rollout_msg.origin_task_id] = []
                collected_mdp[rollout_msg.origin_task_id].extend(
                    self.message_processer.build(rollout_msg)
                )

        return collected_mdp

    def _filter_unfinished_tasks(
        self, tasks_dic: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """Filter unfinished tasks and update their round numbers."""
        unfinished_tasks: Dict[str, Any] = {}

        for task_id, task in tasks_dic.items():
            if (
                task.origin_task_id in self._rollout_state
                and not self._rollout_state[task.origin_task_id]["finished"]
            ):
                task.round_num += 1
                unfinished_tasks[task_id] = task

        finished_count = len(tasks_dic) - len(unfinished_tasks)
        return unfinished_tasks, finished_count

    async def _stop_parallel_executor_if_needed(self) -> None:
        """Stop parallel executor if it is running."""
        if self.parallel_executor and self.parallel_executor.is_running():
            await self.parallel_executor.stop()
            logger.info("Parallel executor stopped")

    def _build_rl_batch_from_caches(self, device):
        """Sample rollouts from caches and build RL batch."""
        sampling_func = self.processors_registry.get_sampler(
            self.config["JiuwenRL"]["custom_fn"]["sampler"]
        )
        pos_rollout_dict, neg_rollout_dict = sampling_func(
            self.positive_cache, self.negative_cache
        )
        merged_dict = self.merge_caches(pos_rollout_dict, neg_rollout_dict)
        rl_batch = self.rldata_proto.generate_rl_batch(merged_dict, device)
        return rl_batch, merged_dict
