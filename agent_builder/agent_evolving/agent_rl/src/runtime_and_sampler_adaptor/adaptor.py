# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import asyncio
import multiprocessing as mp

from agent_builder.agent_evolving.agent_rl.src.rl_trainer_adaptor.coordinator.resource_cache import (
    DataStore,
)
from agent_builder.agent_evolving.agent_rl.src.runtime_and_sampler_adaptor.agent_runtime import (
    RuntimeExecutor,
)
from agent_builder.agent_evolving.agent_rl.src.utils.logging import get_logger

logger = get_logger(__name__)


class ParallelRuntimeExecutor:
    """A parallel rollout execution engine that manages multiple asynchronous
    worker loops to process rollout tasks concurrently. It serves as the core
    parallelization module for RL-based rollout generation in the training loop.
    """

    def __init__(self, data_store: DataStore, num_workers):
        self.data_store = data_store
        self.num_workers = num_workers or mp.cpu_count()

        self._is_running = False
        self._runtime_tasks = []

    async def start(self, env_info):
        """Launch all worker loops asynchronously and begin parallel execution."""
        if self._is_running:
            logger.warning("ParallelRuntimeExecutor is already running")
            return
        self._is_running = True
        logger.info(f"Starting ParallelRuntimeExecutor with {self.num_workers} workers")
        for i in range(self.num_workers):
            runtime_task = asyncio.create_task(
                self._worker_loop(worker_id=i, env_info=env_info)
            )
            self._runtime_tasks.append(runtime_task)

    async def stop(self):
        """Stop all workers, wait for their completion, and clean runtime state."""
        self._is_running = False
        if self._runtime_tasks:
            await asyncio.gather(*self._runtime_tasks, return_exceptions=True)
            self._runtime_tasks.clear()
        logger.info("ParallelRuntimeExecutor stopped")

    def is_running(self):
        """Return True if the executor workers are currently running."""
        return self._is_running

    async def _worker_loop(self, worker_id: int, env_info):
        """Main execution loop for an individual worker. Continuously pulls tasks
        from the datastore, executes rollouts, and sends the results back to the datastore.
        """
        logger.info(f"Worker {worker_id} started")
        executor = RuntimeExecutor()
        while self._is_running:
            try:
                task = await self.data_store.get_task()
                if task is None:
                    await asyncio.sleep(0.1)
                    continue
                logger.info(f"Worker {worker_id} START task {task.task_id}")
                rollout_message = await executor.execute_async(
                    task, env_info.agent_info
                )
                rollout_message.rollout_id = task.task_id
                await self.data_store.add_rollout(rollout_message)
                logger.info(
                    f"Worker {worker_id} completed task {task.task_id},"
                    f"reward: {rollout_message.global_reward}"
                )
            except Exception as e:
                logger.error(
                    f"Worker {worker_id} error: {str(e)}, delete task directly."
                )
                if "task" in locals() and task is not None:
                    await self.data_store.delete_task(task)
                await asyncio.sleep(1)
