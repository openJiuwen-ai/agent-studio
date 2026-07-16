# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
agent builder chain Template optimizer
"""

import copy
import os
import threading
from threading import Timer
from typing import Dict, Optional, Any, Callable, List, Set

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.common.status import TaskStatus
from agent_builder.prompt.mmapo.utils import MMAPO_MODE, JNT_MODE
from agent_builder.prompt.tune.base.constant import TuneConstant
from agent_builder.prompt.tune.base.context import JobInfo, Progress, SingleTaskInfo
from agent_builder.prompt.tune.base.context import TotalJobDetails, JobDetail
from agent_builder.prompt.tune.base.utils import (
    placeholder_to_dict,
    example_to_string_list,
    JointParams,
    calc_run_time,
)
from agent_builder.prompt.tune.storage.base import BaseContextStoreAccesser
from agent_builder.prompt.tune.storage.db_accesser import DbContextAccesser
from cacheout import Cache
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.adapter.singleton import Singleton


class ContextManager(metaclass=Singleton):
    """
    A singleton class for managing the context of tasks, including in-memory caching, checkpointing,
    and persistent storage access. It is used to store, retrieve, and manage the state of optimization tasks.
    """

    def __init__(self):
        self._cache: Cache = Cache(maxsize=65536)  # 内存态缓存
        self._check_points: Cache = Cache(maxsize=65536)  # 检查点
        self._store: Optional[BaseContextStoreAccesser] = None  # 持久化服务访问器
        self._lock = threading.Lock()  # 上下文管理器锁
        self._n_max_running_tasks: int = self._load_max_running_task_num()
        self._n_max_running_tasks_mmapo: int = self._load_max_running_task_num(
            mode=MMAPO_MODE
        )
        self._status_checker = None

    def __len__(self):
        """get length of cache"""
        with self._lock:
            return self._cache.size()

    @staticmethod
    def _load_max_running_task_num(mode: str = JNT_MODE) -> int:
        """load max running task num"""
        n_max_running_tasks = (
            os.getenv("PROMPT_MAX_OPTIMIZATION_TASK_NUM")
            if mode == JNT_MODE
            else os.getenv("MMAPO_MAX_OPTIMIZATION_TASK_NUM")
        )
        if not n_max_running_tasks:
            return TuneConstant.DEFAULT_MAX_RUNNING_TASK_NUM
        try:
            n_max_running_tasks = int(n_max_running_tasks)
        except ValueError:
            logger.warning(
                f"Load invalid max running task num, set default value "
                f"{TuneConstant.DEFAULT_MAX_RUNNING_TASK_NUM}"
            )
            return TuneConstant.DEFAULT_MAX_RUNNING_TASK_NUM
        if n_max_running_tasks <= 0:
            logger.warning(
                f"Max running task num should be larger than 0, set default value "
                f"{TuneConstant.DEFAULT_MAX_RUNNING_TASK_NUM}"
            )
            return TuneConstant.DEFAULT_MAX_RUNNING_TASK_NUM

        return int(n_max_running_tasks)

    @staticmethod
    def _generate_task_info_from_context(
        ctx_id: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """generate task info from cache"""
        if not context:
            return SingleTaskInfo().model_dump()

        job_info = JobInfo(
            id=ctx_id,
            name=context.get("name"),
            desc=context.get("desc"),
            num_iter=context["optimize_info"].num_iter,
            created_at=context.get("create_time"),
            optimized_model=context["model_info"].model,
            assistant_model=context["assistant_info"].model,
        )

        params = context.get("params", None)
        # params未初始化的异常场景，确保状态返回接口可用
        if not params:
            params = JointParams(
                base_instruction=context.get("raw_templates")[0],
                original_placeholder=context["optimize_info"].placeholder,
                filled_instruction=context.get("raw_templates")[0],
            )

        placeholders = context["optimize_info"].placeholder
        original_prompt = context.get("raw_templates")[0]
        if placeholders:
            for p in placeholders:
                name, content = p.get("name"), p.get("content")
                if name and content:
                    original_prompt = original_prompt.replace(
                        f"{{{{{name}}}}}", content
                    )
        progress = Progress(
            job_info=job_info,
            original_prompt=original_prompt,
            best_prompt=params.full_prompt,
            original_placeholder=placeholder_to_dict(placeholders, True),
            best_placeholder=placeholder_to_dict(params.placeholder),
            examples=example_to_string_list(params.examples + params.cot_examples),
            filled_prompt=params.filled_instruction,
            success_rate=context["scores"][0],
            error_msg=context["error_msg"],
            progress_rate=round(context["progress_rate"], 2),
            time_cost=context["run_time"],
            status=context["status"],
            evaluation_method=context["optimize_info"].eval_mode,
        )
        history = context["history"] if "history" in context else []
        return SingleTaskInfo(history=history, progress=progress).model_dump()

    def has_store(self):
        """check manager has persistence store ability"""
        return self._store is not None

    def init_store(self):
        """initialize store database tables"""
        if self._store and hasattr(self._store, 'init_db'):
            self._store.init_db()
        if self._store and hasattr(self._store, 'fix_stale_tasks'):
            self._store.fix_stale_tasks()

    def set_store(
        self, store_instance: BaseContextStoreAccesser = None, store_type: str = None
    ):
        """set store service for ContextManager.

        If called without arguments, auto-detects store type from db_config.
        If no database is configured, silently returns without error.
        """
        with self._lock:
            if self._store:
                logger.debug("store is already set.")
                return
            try:
                if store_instance:
                    self._store = store_instance
                elif store_type is None:
                    store_type = self._resolve_store_type()
                    if store_type is None:
                        logger.info("No database configured, prompt optimization persistence disabled.")
                        return
                    self._store = self._create_accesser(store_type)
                else:
                    self._store = self._create_accesser(store_type)

                if self._store:
                    self.init_store()
            except Exception as e:
                self._store = None
                raise

    @staticmethod
    def _resolve_store_type() -> str:
        """Auto-detect store type from settings.db_config."""
        from agent_builder.adapter.config_bridge import settings

        db = settings.db_config
        if not db.host:
            return None
        return db.db_type.upper()

    @staticmethod
    def _create_accesser(store_type: str) -> BaseContextStoreAccesser:
        """Create the appropriate store accesser based on store_type."""
        if store_type in (TuneConstant.MYSQL_STORAGE, TuneConstant.GAUSSDB_STORAGE):
            return DbContextAccesser()
        raise ValueError(f"Unknown store type: {store_type}")

    def load_context(
        self, ctx_id: str, convert_func: Callable = None, mode: str = JNT_MODE
    ) -> Dict[str, Any]:
        """load context from store"""
        if not self._store:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_STORAGE_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_STORAGE_ERROR.errmsg.format(
                    error_msg="Cannot load context: invalid storage service"
                ),
            )

        if ctx_id in self._cache:
            logger.info(f"task {ctx_id} already loaded in cache")
            return None

        context = self._store.load_context(ctx_id, load_all=True, mode=mode)

        # 当前添加缓存需要从回调函数中进行，故需要加锁
        with self._lock:
            if convert_func is not None:
                context = convert_func(context)
            if not context:
                logger.warning(f"load context failed, id = {ctx_id}.")
                return None
        return context

    def store_context(self, ctx_id: str, context: Dict[str, Any]):
        """store context in store"""
        if not self._store:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_STORAGE_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_STORAGE_ERROR.errmsg.format(
                    error_msg="Invalid storage service"
                ),
            )

        if ctx_id not in self._cache:
            raise JiuWenBaseException(
                error_code=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.code,
                message=StatusCode.PROMPT_OPTIMIZE_INVALID_PARAMS_ERROR.errmsg.format(
                    error_msg=f"Cannot store invalid context id {ctx_id}"
                ),
            )

        with self._lock:
            ctx_id_list = list(self._cache.keys())[:]
        self._store.store_context_ids(ctx_id_list)
        self._store.store_context(ctx_id, context)

    def get_context_attr(
        self,
        ctx_id: str,
        attr_name: str,
        attr_name_alias: str = None,
        from_store: bool = False,
        table_name: str = "progress",
    ) -> Any:
        """get context attribute"""
        context = self._cache.get(ctx_id)
        if context and not (self._store and from_store):
            return context.get(attr_name, None)
        try:
            if not self.has_store():
                return None
            return self._store.get_context_attr(
                ctx_id,
                attr_name if not attr_name_alias else attr_name_alias,
                table_name=table_name,
            )
        except JiuWenBaseException:
            return None

    def set_context_attr(
        self, ctx_id: str, attr_name: str, attr_value: Any, attr_name_alias: str = None
    ):
        """set context attribute"""
        try:
            if self.has_store():
                self._store.set_context_attr(
                    ctx_id,
                    attr_name if not attr_name_alias else attr_name_alias,
                    attr_value,
                )
        except JiuWenBaseException as e:
            raise e
        context = self._cache.get(ctx_id)
        if context:
            context[attr_name] = attr_value
        check_point = self._check_points.get(ctx_id)
        if check_point:
            check_point[attr_name] = attr_value

    def set(self, ctx_id: str, context: Dict[str, Any]):
        """set context to cache"""
        with self._lock:
            self._cache.set(ctx_id, context)

    def get(self, ctx_id: str) -> Optional[Dict[str, Any]]:
        """get context from cache"""
        with self._lock:
            return self._cache.get(ctx_id, None)

    def is_executable(self, mode: str = JNT_MODE) -> bool:
        """check if the number of running tasks is exceed threshold"""
        n_running_tasks = 0
        tasks_limit = (
            self._n_max_running_tasks
            if mode == JNT_MODE
            else self._n_max_running_tasks_mmapo
        )
        for task in self._cache.values():
            if not task.get("id", "").startswith(mode):
                continue
            status = task.get(TaskStatus.TASK_STATUS, TaskStatus.TASK_FAILED)
            if status in (TaskStatus.TASK_STOPPING, TaskStatus.TASK_RUNNING):
                n_running_tasks += 1
        return n_running_tasks < tasks_limit

    def set_checkpoint(self, ctx_id: str, context: Dict[str, Any]):
        """set checkpoint to cache"""
        with self._lock:
            event = context.get("cancel_event")
            context["cancel_event"] = None
            copy_context = copy.deepcopy(context)
            context["cancel_event"] = event
            self._check_points.set(ctx_id, copy_context)

    def get_checkpoint(self, ctx_id: str) -> Optional[Dict[str, Any]]:
        """get context from cache"""
        with self._lock:
            context = copy.deepcopy(self._check_points.get(ctx_id, None))
            if context:
                context["cancel_event"] = threading.Event()
            return context

    def delete(self, ctx_id: str, delete_store: bool = False):
        """delete context from cache"""
        with self._lock:
            self._cache.delete(ctx_id)
            self._check_points.delete(ctx_id)
            if self._store and delete_store:
                self._store.delete_context(ctx_id)

    def get_task_info(self, ctx_id: str, cur_status: str) -> Dict[str, Any]:
        """get context info from cache"""
        if ctx_id in self._cache:
            task_info = self._generate_task_info_from_context(
                ctx_id, self.get_checkpoint(ctx_id)
            )
            task_info["progress"]["status"] = cur_status
            return task_info
        return self._generate_task_info_from_store(ctx_id)

    def get_batch_task_info(self, ctx_id_list: List[str]) -> Dict[str, Any]:
        """get batch context info from cache"""
        infos = TotalJobDetails()
        for ctx_id in ctx_id_list:
            context = self._cache.get(ctx_id)
            if context:
                task_status = context[TaskStatus.TASK_STATUS]
                detail: JobDetail = self._generate_task_detail_from_check_point(ctx_id)
                detail.status = task_status
            else:
                detail: JobDetail = self._generate_task_detail_from_store(ctx_id)
                if detail is None:
                    continue
            infos.data.append(detail)
            if detail.status == TaskStatus.TASK_FINISHED:
                infos.finished_jobs += 1
            elif detail.status == TaskStatus.TASK_FAILED:
                infos.failed_jobs += 1
            elif detail.status == TaskStatus.TASK_STOPPED:
                infos.stopped_jobs += 1
            else:
                infos.running_jobs += 1
        infos.total_jobs = (
            infos.finished_jobs
            + infos.failed_jobs
            + infos.running_jobs
            + infos.stopped_jobs
        )
        return infos.model_dump()

    def clear(self):
        """clear context from cache"""
        with self._lock:
            self._cache.clear()

    def items(self):
        """get iterable (id, context) pairs"""
        with self._lock:
            return self._cache.items()

    def _generate_task_info_from_store(self, ctx_id: str) -> Dict[str, Any]:
        """generate task info from store"""
        if not self._store:
            raise JiuWenBaseException(
                StatusCode.PROMPT_OPTIMIZE_STORAGE_ERROR.code,
                StatusCode.PROMPT_OPTIMIZE_STORAGE_ERROR.errmsg.format(
                    error_msg="no storage service"
                ),
            )
        context = self._store.load_context(ctx_id)
        return self._generate_task_info_from_context(ctx_id, context)

    def _generate_task_detail_from_check_point(self, ctx_id: str) -> JobDetail:
        """generate task detail from checkpoint"""
        with self._lock:
            job_detail = JobDetail()
            context = self._check_points.get(ctx_id) or self._cache.get(ctx_id)
            job_info = JobInfo(
                id=ctx_id,
                name=context.get("name"),
                desc=context.get("desc"),
                num_iter=context["optimize_info"].num_iter,
                created_at=context.get("create_time"),
                optimized_model=context["model_info"].model,
                assistant_model=context["assistant_info"].model,
            )
            job_detail.job_info = job_info
            job_detail.status = context.get("status")
            job_detail.error_msg = context.get("error_msg")
            job_detail.progress_rate = context.get("progress_rate")
            job_detail.time_cost = context.get("run_time")
            return job_detail

    def _generate_task_detail_from_store(self, ctx_id: str) -> Optional[JobDetail]:
        """generate task detail from store"""
        if not self._store:
            return None
        job_detail = JobDetail()
        try:
            context = self._store.load_context(ctx_id)
            if not context:
                return None
        except JiuWenBaseException:
            return None
        # 检查是否存在伪运行状态
        self._stop_fake_running_task(ctx_id, context)
        job_info = JobInfo(
            id=ctx_id,
            name=context.get("name"),
            desc=context.get("desc"),
            num_iter=context["optimize_info"].num_iter,
            created_at=context.get("create_time"),
            optimized_model=context["model_info"].model,
            assistant_model=context["assistant_info"].model,
        )
        job_detail.job_info = job_info
        job_detail.status = context.get("status")
        job_detail.error_msg = context.get("error_msg")
        job_detail.progress_rate = context.get("progress_rate")
        job_detail.time_cost = context.get("run_time")
        return job_detail

    def _stop_fake_running_task(self, ctx_id: str, context: Dict[str, Any]):
        """stop fake running task"""
        if not context or context.get(TaskStatus.TASK_STATUS, "") not in (
            TaskStatus.TASK_RUNNING,
            TaskStatus.TASK_STOPPING,
        ):
            return

        create_time = context.get("create_time", None)
        run_time = context.get("run_time", None)
        if create_time is None or run_time is None:
            return

        actual_runtime = calc_run_time(create_time)
        if actual_runtime - run_time > TuneConstant.RUNNING_STATUS_TIMEOUT:
            self.set_context_attr(
                ctx_id, TaskStatus.TASK_STATUS, TaskStatus.TASK_FAILED
            )
            context[TaskStatus.TASK_STATUS] = TaskStatus.TASK_FAILED


class StatusChecker(Timer, metaclass=Singleton):
    """
    A singleton class serving as a task manager, used for managing and checking the running status of tasks.
    """

    def __init__(self):
        super().__init__(TuneConstant.STATUS_CHECK_INTERVAL, None)
        self._tasks: Set[str] = set()
        self._lock = threading.Lock()
        self._cur_period: int = 0
        self.start()

    def add_task(self, ctx_id: str):
        """add task"""
        with self._lock:
            if ctx_id not in self._tasks:
                self._tasks.add(ctx_id)

    def run(self) -> None:
        """run task status check timer"""
        while not self.finished.is_set():
            self._cur_period += 1
            tasks = copy.deepcopy(self._tasks)
            for ctx_id in tasks:
                try:
                    self._check_status(ctx_id)
                except Exception as e:
                    logger.warning(
                        f"Periodic check failed, ctx_id is {ctx_id}, reason: {str(e)}"
                    )
                    continue
            self.finished.wait(self.interval)

    def _check_status(self, ctx_id: str):
        """check status of task"""
        # 从数据库中读取，检查状态是否有变化
        status = ContextManager().get_context_attr(
            ctx_id, TaskStatus.TASK_STATUS, from_store=True
        )
        if not status:
            if ContextManager().get(ctx_id):
                status = ContextManager().get_context_attr(
                    ctx_id, TaskStatus.TASK_STATUS, from_store=False
                )
            if not status:
                logger.warning("Task status is undefined")
                self._remove_event(ctx_id)
                return
        if status == TaskStatus.TASK_STOPPING:
            self._stop_event(ctx_id)
        elif status in (TaskStatus.TASK_RUNNING, TaskStatus.TASK_STOPPING):
            self._running_event(ctx_id)
        else:
            self._remove_event(ctx_id)

    def _stop_event(self, ctx_id: str):
        """stop task"""
        context = ContextManager().get(ctx_id)
        if not context:
            return
        cancel_event = context.get("cancel_event")
        if cancel_event:
            if not cancel_event.is_set():
                context[TaskStatus.TASK_STATUS] = TaskStatus.TASK_STOPPING
            cancel_event.set()

    def _running_event(self, ctx_id: str):
        """running event"""
        if self._cur_period < TuneConstant.RUNNING_CHECK_PERIOD:
            return

        self._cur_period = 0
        start_time = ContextManager().get_context_attr(
            ctx_id, "create_time", attr_name_alias="created_at", table_name="job_info"
        )
        new_run_time = calc_run_time(start_time)
        ContextManager().set_context_attr(
            ctx_id, "run_time", new_run_time, attr_name_alias="time_cost"
        )

    def _remove_event(self, ctx_id: str):
        """remove task"""
        with self._lock:
            # 防止新增后删除的并发问题，故需要在锁中再次查询状态
            status = ContextManager().get_context_attr(ctx_id, TaskStatus.TASK_STATUS)
            if status != TaskStatus.TASK_RUNNING:
                self._tasks.remove(ctx_id)
