#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.

"""
Constants
"""

# 任务元数据
from enum import Enum

# 任务元信息
JOB_METADATA_KEY = "jiuwen:job:{job_id}"

# worker元信息
WORKER_METADATA_KEY = "jiuwen:worker:{worker_id}"
# worker心跳
WORKER_HEARTBEAT_KEY = "jiuwen:worker:{worker_id}:heartbeat"
# worker可用列表
ACTIVE_WORKERS_KEY = "jiuwen:active_workers"

# worker任务队列
WORKER_QUEUED_JOBS_KEY = "jiuwen:worker:{worker_id}:queued"
WORKER_RUNNING_JOBS_KEY = "jiuwen:worker:{worker_id}:running_job"


class WorkerStatus(str, Enum):
    """
    The enum class of worker status
    """

    BUSY = "busy"  # 可用中
    STOP = "stop"  # 主动停止
    ABORT = "abort"  # 异常终止


class JobStatus(str, Enum):
    """
    The enum class of job status
    """

    QUEUED = "queued"  # 排队中
    RUNNING = "running"  # 运行中
    FINISHED = "finished"  # 已完成
    HEARTBEAT_TIMEOUT = "heartbeat_timeout"  # worker因心跳超时终止


def worker_metadata_key(worker_id):
    """
    Returns the redis key of worker metadata.
    """
    return WORKER_METADATA_KEY.format(worker_id=worker_id)


def worker_heartbeat_key(worker_id: str):
    """
    Returns the redis key of worker heartbeat.
    """
    return WORKER_HEARTBEAT_KEY.format(worker_id=worker_id)


def job_metadata_key(job_id):
    """
    Returns the redis key of job metadata.
    """
    return JOB_METADATA_KEY.format(job_id=job_id)


def worker_queued_jobs_key(worker_id):
    """
    Returns the redis key of worker queued jobs key.
    """
    return WORKER_QUEUED_JOBS_KEY.format(worker_id=worker_id)


def worker_running_jobs_key(worker_id):
    """
    Returns the redis key of worker running jobs.
    """
    return WORKER_RUNNING_JOBS_KEY.format(worker_id=worker_id)
