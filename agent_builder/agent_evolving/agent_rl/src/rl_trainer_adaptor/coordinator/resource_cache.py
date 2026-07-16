# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import asyncio
from typing import Dict

from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.coordinator.base import (
    RLTask,
)
from agent_builder.agent_evolving.agent_rl.src.runtime_and_sampler_adaptor.base import (
    RolloutMessage,
)
from agent_builder.agent_evolving.agent_rl.src.runtime_and_sampler_adaptor.base import (
    RolloutWithReward,
)
from agent_builder.agent_evolving.agent_rl.src.utils.logging import get_logger

logger = get_logger(__name__)


class DataStore:
    """A lightweight asynchronous data store that manages rollout tasks,
    tracks in-processing tasks, and buffers completed rollout messages.
    """

    def __init__(self):
        """Initialize task queues, rollout cache, and internal synchronization primitives."""
        self._task_queue: asyncio.Queue[RLTask] = asyncio.Queue()
        self._in_processing_task: Dict[str, RLTask] = {}
        self.rollouts: Dict[str, RolloutMessage] = {}
        self._queue_lock = asyncio.Lock()
        self._rollout_lock = asyncio.Lock()

    async def queue_task(self, task):
        """Enqueue a new task and return its task identifier."""
        async with self._queue_lock:
            await self._task_queue.put(task)
            logger.info(f"Task {task.task_id} queued.")
            return task.task_id

    async def get_task(self):
        """Retrieve the next task for processing, updating its round number."""
        try:
            async with self._queue_lock:
                processing_task = self._task_queue.get_nowait()
                self._in_processing_task[processing_task.task_id] = processing_task
                return processing_task
        except asyncio.QueueEmpty:
            return None

    async def requeue_task(self, task):
        """Re-enqueue a task and remove it from the in-processing pool if present."""
        async with self._queue_lock:
            await self._task_queue.put(task)
            if task.task_id in self._in_processing_task:
                del self._in_processing_task[task.task_id]
                logger.info(f"Task {task.task_id} re-queued.")

    async def delete_task(self, task):
        """Delete a task directly from the in-processing pool if present."""
        async with self._queue_lock:
            if task.task_id in self._in_processing_task:
                del self._in_processing_task[task.task_id]
                logger.info(f"Task {task.task_id} delete directly.")

    async def add_rollout(self, rollout: RolloutMessage):
        """Store a completed rollout and clear its corresponding in-processing task entry."""
        rollout_id = rollout.rollout_id
        task_id = rollout.task_id
        async with self._queue_lock:
            if task_id and task_id in self._in_processing_task:
                del self._in_processing_task[task_id]
                logger.info(f"Task {task_id} removed from in_processing_task")

        async with self._rollout_lock:
            self.rollouts[rollout_id] = rollout
            logger.info(f"Rollout {rollout_id} added to rollouts cache.")
            return rollout_id

    async def get_rollouts(self):
        """Retrieve and clear all cached rollouts in a single atomic operation."""
        async with self._rollout_lock:
            rollouts = self.rollouts.copy()
            self.rollouts.clear()
            logger.info(f"Retrieved {len(rollouts)} rollouts from cache")
            return rollouts

    def is_finished(self):
        """Check whether all tasks have been processed and no rollouts remain pending."""
        if self._task_queue.empty() and len(self._in_processing_task) == 0:
            logger.info("All tasks finished.")
            return True
        return False


class ProcessRolloutMsg:
    def __init__(self, tokenizer) -> None:
        self.tokenizer = tokenizer

    def build(self, rolloutmsg):
        """Build rollout training samples."""
        res_list = []
        for i, (rollout, reward) in enumerate(
            zip(rolloutmsg.rollout_info, rolloutmsg.reward_list)
        ):
            try:
                res_list.append(
                    self.build_input_output(
                        rollout,
                        i,
                        reward,
                        rolloutmsg.origin_task_id,
                        rolloutmsg.rollout_id,
                    )
                )
            except Exception as e:
                logger.warning(f"Error occurred when calling apply_chat_template: {e}")
                logger.warning(f"The rollout message is {rolloutmsg.model_dump_json()}")
                return []
        return res_list

    def build_input_output(self, rollout, turn_id, reward, task_id, rollout_id):
        """Build a single input-output rollout sample."""
        input_messages = rollout.input_prompt["message"]
        output_messages = [rollout.output_response]
        full_messages = input_messages + output_messages
        tools_info = rollout.input_prompt["tools"]
        full_text = self.tokenizer.apply_chat_template(
            full_messages,
            tokenize=False,
            add_generation_prompt=False,
            tools=tools_info,
        )
        prompt_text = self.tokenizer.apply_chat_template(
            input_messages,
            tokenize=False,
            add_generation_prompt=True,
            tools=tools_info,
        )
        output_text = full_text[len(prompt_text) :]
        input_prompt_ids = self.tokenizer.encode(prompt_text, add_special_tokens=True)
        output_response_ids = self.tokenizer.encode(
            output_text, add_special_tokens=True
        )
        return RolloutWithReward(
            turn_id=turn_id,
            task_id=task_id,
            rollout_id=rollout_id,
            input_prompt_ids=input_prompt_ids,
            output_response_ids=output_response_ids,
            reward=reward,
        )
