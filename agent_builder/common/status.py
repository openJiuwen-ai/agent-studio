#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

"""
status code
"""

from typing import Final


class TaskStatus:
    """
    TaskStatus definition.
    """

    TASK_STATUS: Final[str] = "status"
    TASK_RUNNING: Final[str] = "running"
    TASK_FINISHED: Final[str] = "finished"
    TASK_FAILED: Final[str] = "failed"
    TASK_DELETED: Final[str] = "deleted"
    TASK_STOPPED: Final[str] = "stopped"
    TASK_STOPPING: Final[str] = "stopping"
    TASK_QUEUED: Final[str] = "queued"
