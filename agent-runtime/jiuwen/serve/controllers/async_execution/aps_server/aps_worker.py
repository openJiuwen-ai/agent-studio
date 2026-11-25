#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.

"""
ApsWorker
"""

import os
import secrets
import socket
import threading
import time

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from jiuwen.common.configs.env_constants import (
    DATASOURCE_REDIS_TTL_KEY,
    ASYNC_WORKER_ID_KEY,
)
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.store.redis import get_redis_instance, DEFAULT_REDIS_TTL
from jiuwen.common.utils.singleton import Singleton
from jiuwen.common.utils.utils import safe_json_loads
from jiuwen.serve.common.exception.exception_handler import hide_security
from jiuwen.serve.controllers.async_execution.add_job import (
    async_execute_workflow_apscheduler,
    async_cancel_execution_apscheduler,
)
from jiuwen.serve.controllers.async_execution.aps_server.constants import (
    worker_queued_jobs_key,
    worker_metadata_key,
    ACTIVE_WORKERS_KEY,
    WorkerStatus,
    worker_heartbeat_key,
    worker_running_jobs_key,
    JobStatus,
    job_metadata_key,
)
from jiuwen.serve.controllers.execution.enum import AsyncExecutionStatus
from jiuwen.serve.controllers.execution.manager import (
    ApsRedisManager,
    AsyncExecStateManager,
)
from jiuwen.serve.controllers.execution.utils import get_current_time_ms
from jiuwen.serve.schemas.orchestration_mgr import ExecutionRequest
from redis import RedisError


class ApsWorker(metaclass=Singleton):
    def __init__(
        self,
        hostname=None,
        worker_id=None,
        redis_conn=None,
        heartbeat_interval=30,
        heartbeat_threshold=3,
        max_pool_size=10,
    ):
        self.hostname = hostname if hostname else self._get_local_host_name()
        self.worker_id = f"{self.hostname}_{secrets.token_hex(24)}"
        self.worker_id = worker_id or self.worker_id
        os.environ[ASYNC_WORKER_ID_KEY] = self.worker_id

        self.redis = redis_conn or get_redis_instance()
        self.heartbeat_interval = heartbeat_interval  # 心跳间隔(秒)
        self.scan_interval = self.heartbeat_interval  # 扫描死worker间隔(秒)
        self.heartbeat_threshold = heartbeat_threshold
        self.max_pool_size = max_pool_size

        self.stop_event = threading.Event()

        # 配置 APScheduler
        self.scheduler = BackgroundScheduler(
            jobstores={"default": MemoryJobStore()},
            executors={"default": ThreadPoolExecutor(20)},  # 根据任务并发量调整
            job_defaults={"coalesce": True, "max_instances": 3},
        )
        self.listener_thread = None

    @staticmethod
    def _get_local_host_name():
        """
        获取本地主机标识，优先使用主机名，其次使用非回环 IP，否则返回默认值。

        返回:
            str: 主机名、非回环 IP 地址或默认值 "None"
        """
        try:
            # 尝试获取主机名
            hostname = socket.gethostname()
            if hostname:
                return hostname
        except Exception as e:
            hidden_err = hide_security(e)
            logger.error(f"Failed to get local host name, reason = {hidden_err}")
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_ASYNC_GET_LOCAL_HOST_NAME_ERROR.code,
                message=StatusCode.WORKFLOW_ASYNC_GET_LOCAL_HOST_NAME_ERROR.errmsg.format(
                    reason=hidden_err
                ),
            ) from e

        try:
            # 尝试获取非回环 IP 地址
            ip_list = socket.getaddrinfo(socket.gethostname(), None)
            non_loopback_ips = [
                addr[4][0]
                for addr in ip_list
                if addr[4][0] and not addr[4][0].startswith("127.")
            ]
            if non_loopback_ips:
                return non_loopback_ips[0]
        except Exception as e:
            hidden_err = hide_security(e)
            logger.error(f"Failed to get non loopback ips, reason = {hidden_err}")
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_ASYNC_GET_LOCAL_HOST_NAME_ERROR.code,
                message=StatusCode.WORKFLOW_ASYNC_GET_LOCAL_HOST_NAME_ERROR.errmsg.format(
                    reason=hidden_err
                ),
            ) from e

        # 默认值
        return "None"

    def start_listener(self):
        """
        Start listener thread
        """
        self.listener_thread = threading.Thread(
            target=self._redis_listener, daemon=True
        )
        self.listener_thread.start()

    def start(self):
        """启动调度系统"""
        # 1. 注册本机worker
        self._register_worker()

        # 2.1 添加心跳任务
        self.scheduler.add_job(
            self._send_heartbeat,
            "interval",
            seconds=self.heartbeat_interval,
            id="heartbeat",
        )

        # 2.2 添加扫描死亡worker任务
        self.scheduler.add_job(
            func=self._handle_dead_workers,
            trigger="interval",
            seconds=self.scan_interval,
            id="scan_dead_workers",
        )

        # 2.3 启动调度系统
        self.scheduler.start()

        # 3. 启动监听进程
        self.start_listener()

        try:
            while not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        """安全关闭"""
        self.stop_event.set()
        self.scheduler.shutdown(wait=False)
        if self.listener_thread:
            self.listener_thread.join(timeout=5)

        # 心跳停止后，清除本worker的状态，并将所有running_queue中的任务置为失败
        self._handle_jobs_in_dead_worker(self.worker_id)
        logger.info(f"Worker {self.worker_id} shutdown completed")

    def _register_worker(self):
        """注册worker到Redis"""
        try:
            with self.redis.get_redis_client().pipeline() as pipe:
                # 添加worker到活动worker集合
                pipe.sadd(ACTIVE_WORKERS_KEY, self.worker_id)
                # 设置worker元数据
                pipe.hset(
                    worker_metadata_key(self.worker_id),
                    mapping={
                        "birth_date": get_current_time_ms(),
                        "hostname": self.hostname,
                        "state": WorkerStatus.BUSY,
                        "last_heartbeat": get_current_time_ms(),
                    },
                )
                pipe.expire(
                    worker_metadata_key(self.worker_id),
                    int(os.getenv(DATASOURCE_REDIS_TTL_KEY, DEFAULT_REDIS_TTL)),
                )

                # 设置worker心跳信息
                pipe.hset(
                    worker_heartbeat_key(self.worker_id),
                    mapping={
                        "state": WorkerStatus.BUSY,
                        "last_heartbeat": get_current_time_ms(),
                    },
                )

                pipe.expire(
                    worker_heartbeat_key(self.worker_id),
                    self.heartbeat_interval * self.heartbeat_threshold,
                )
                # 执行原子操作
                pipe.execute()
            logger.info(f"Worker {self.worker_id} registered successfully")
        except Exception as e:
            hidden_err = hide_security(e)
            logger.error(
                f"Failed to register worker {self.worker_id}, reason = {hidden_err}"
            )
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_ASYNC_APS_WORKER_REGISTER_ERROR.code,
                message=StatusCode.WORKFLOW_ASYNC_APS_WORKER_REGISTER_ERROR.errmsg.format(
                    reason=hidden_err
                ),
            ) from e

    def _redis_listener(self):
        """独立监听线程：阻塞获取任务"""
        while not self.stop_event.is_set():
            # 阻塞式获取任务（超时时长需要小于redis配置的）
            result = self.redis.get_redis_client().blpop(
                worker_queued_jobs_key(self.worker_id), timeout=3
            )
            if result:
                list_name, value = result
                task = safe_json_loads(value)
                task_id = task.get("exec_id")
                cancel_flag = task.get("cancel", False)

                if cancel_flag:
                    logger.info(
                        f"Received cancel task request {task_id} from list {list_name.decode('utf-8')}"
                    )
                    # 添加任务到调度器
                    self._add_cancel_job_to_scheduler(task)
                else:
                    logger.info(
                        f"Received task {task_id} from list {list_name.decode('utf-8')}"
                    )
                    # 将任务添加到running_job队列
                    ApsRedisManager().add_job_to_running_jobs(self.worker_id, task_id)
                    # 动态添加任务到调度器
                    self._add_execute_job_to_scheduler(task)

    def _add_execute_job_to_scheduler(self, task):
        """动态添加workflow执行任务到调度器"""
        job_id = task.get("exec_id", "")

        # 避免重复添加
        if not self.scheduler.get_job(job_id):
            self.scheduler.add_job(
                async_execute_workflow_apscheduler, id=job_id, args=[task]
            )

    def _add_cancel_job_to_scheduler(self, task):
        """动态添加workflow取消任务到调度器"""
        job_id = task.get("exec_id", "")

        # 避免重复添加
        if not self.scheduler.get_job(job_id):
            self.scheduler.add_job(
                async_cancel_execution_apscheduler, id=job_id, args=[task]
            )

    def _send_heartbeat(self):
        """发送心跳信息并更新worker元数据"""
        try:
            # 使用Redis Pipeline执行批量操作
            with self.redis.get_redis_client().pipeline() as pipe:
                # ① 如果元数据不存在则插入，存在则更新元数据的last_heartbeat
                worker_key = worker_metadata_key(self.worker_id)
                pipe.hsetnx(
                    worker_key, "birth_date", get_current_time_ms()
                )  # 仅在不存在时设置
                pipe.hsetnx(worker_key, "hostname", self.hostname)
                pipe.hsetnx(worker_key, "state", WorkerStatus.BUSY)
                pipe.hset(worker_key, "last_heartbeat", get_current_time_ms())
                pipe.expire(
                    worker_key,
                    int(os.getenv(DATASOURCE_REDIS_TTL_KEY, DEFAULT_REDIS_TTL)),
                )

                # 构建心跳字符串命令
                heartbeat_key = worker_heartbeat_key(self.worker_id)

                # ② 插入心跳数据
                pipe.hset(heartbeat_key, "last_heartbeat", get_current_time_ms())
                pipe.expire(
                    heartbeat_key, self.heartbeat_interval * self.heartbeat_threshold
                )

                # ③ 如果在存活worker中不包括worker信息，则插入
                pipe.sadd(ACTIVE_WORKERS_KEY, self.worker_id)

                # 执行批量操作
                pipe.execute()
            logger.info(f"Worker {self.worker_id} 发送心跳")
        except RedisError as e:
            logger.error(f"{self.worker_id} 发送心跳失败: {e}")

    def _handle_dead_workers(self):
        """扫描并处理死亡的workers"""
        try:
            workers = self.redis.get_redis_client().smembers(ACTIVE_WORKERS_KEY)
            for worker_id_byte in workers:
                # redis中存在该worker的心跳
                worker_id = worker_id_byte.decode("utf-8")
                if self.redis.get_redis_client().exists(
                    worker_heartbeat_key(worker_id)
                ):
                    logger.info(f"发现存活worker: {worker_id}")
                    continue
                logger.warning(f"发现死亡Worker: {worker_id}")
                self._handle_jobs_in_dead_worker(worker_id)
        except RedisError as e:
            logger.error(f"扫描死亡Worker失败: {e}")

    def _handle_jobs_in_dead_worker(self, worker_id):
        """处理死亡worker的任务"""
        logger.info(
            f"Active workers before shutting down: {self.redis.get_redis_client().smembers(ACTIVE_WORKERS_KEY)}",
            simple_log="Active workers before shutting down.",
        )
        self._handle_running_jobs_in_dead_worker(worker_id)
        self._handle_queueing_jobs_in_dead_worker(worker_id)

        pipe = self.redis.get_redis_client().pipeline()
        pipe.hsetnx(worker_metadata_key(worker_id), "state", WorkerStatus.ABORT)
        pipe.srem(ACTIVE_WORKERS_KEY, worker_id)
        pipe.execute()
        # 记录执行后的活跃worker
        logger.info(
            f"Active workers after shutting down: {self.redis.get_redis_client().smembers(ACTIVE_WORKERS_KEY)}",
            simple_log="Active workers before shutting down.",
        )

    def _handle_running_jobs_in_dead_worker(self, worker_id):
        """处理running job"""
        try:
            _running_job_key = worker_running_jobs_key(worker_id)
            logger.info(
                f"_handle_jobs_in_dead_worker, running_job_key: {_running_job_key}",
                simple_log="_handle_jobs_in_dead_worker",
            )
            job_conv_list = []
            jobs = self.redis.list_get(_running_job_key)
            for job_data in jobs:
                job_id = job_data.decode("utf-8")
                conv_id = self.redis.get_redis_client().hget(
                    job_metadata_key(job_id), "conversation_id"
                )
                conv_id = conv_id.decode("utf-8") if conv_id else ""
                job_conv_list.append((job_id, conv_id))
            logger.info(
                f"_handle_running_jobs_in_dead_worker, exec_id and conv_id to be closed: {job_conv_list}",
                simple_log="_handle_running_jobs_in_dead_worker",
            )

            # 使用 pipeline 批量操作
            pipe = self.redis.get_redis_client().pipeline()
            for job_id, conv_id in job_conv_list:
                if job_id:
                    pipe.hset(
                        job_metadata_key(job_id), "status", JobStatus.HEARTBEAT_TIMEOUT
                    )
                if conv_id:
                    pipe.hset(
                        name=AsyncExecStateManager.get_state_key(conv_id),
                        key="status",
                        value=AsyncExecutionStatus.FAILED.value,
                    )
            pipe.delete(_running_job_key)
            pipe.execute()
            logger.info(
                f"Worker {worker_id}: running jobs marked as failed and cleaned up.",
                simple_log="Worker: running jobs marked as failed and cleaned up.",
            )

        except Exception as e:
            logger.error(
                f"_handle_running_jobs_in_dead_worker err,worker id: {worker_id} failed, reason = {e}",
                simple_log="_handle_running_jobs_in_dead_worker err",
            )

    def _handle_queueing_jobs_in_dead_worker(self, worker_id):
        """处理queueing job"""

        _queueing_job_key = worker_queued_jobs_key(worker_id)
        logger.info(
            f"_handle_jobs_in_dead_worker, queueing_job_key: {_queueing_job_key}",
            simple_log="_handle_jobs_in_dead_worker",
        )
        jobs = self.redis.list_get(_queueing_job_key)
        job_conv_list = []

        for job_data in jobs:
            task = safe_json_loads(job_data)
            cancel_flag = task.get("cancel", False)
            if not cancel_flag:
                job_id = task.get("exec_id", "")
                try:
                    req = ExecutionRequest.model_validate(
                        safe_json_loads(task.get("req_str", ""))
                    )
                except Exception as e:
                    logger.warning(
                        f"_handle_queueing_jobs_in_dead_worker model_validate err, task: {task} failed, reason = {e}",
                        simple_log="_handle_queueing_jobs_in_dead_worker model_validate err, task failed,",
                    )
                    continue
                conv_id = req.conversation_id
                job_conv_list.append((job_id, conv_id))
        logger.info(
            f"_handle_queued_jobs_in_dead_worker, exec_id and conv_id to be closed: {job_conv_list}",
            simple_log="_handle_queued_jobs_in_dead_worker, exec_id and conv_id to be closed",
        )
        pipe = self.redis.get_redis_client().pipeline()
        for job_id, conv_id in job_conv_list:
            if job_id:
                pipe.hset(
                    job_metadata_key(job_id), "status", JobStatus.HEARTBEAT_TIMEOUT
                )
            if conv_id:
                pipe.hset(
                    name=AsyncExecStateManager.get_state_key(conv_id),
                    key="status",
                    value=AsyncExecutionStatus.FAILED.value,
                )
        pipe.delete(_queueing_job_key)
        pipe.execute()
        logger.info(
            f"Worker {worker_id}: queueing jobs marked as failed and cleaned up.",
            simple_log="Worker: queueing jobs marked as failed and cleaned up.",
        )
