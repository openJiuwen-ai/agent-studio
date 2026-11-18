#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
"""buffered logger for common and interface."""

import logging
import os
import threading
from typing import Dict, Any, List

from jiuwen.common.configs.base import config
from jiuwen.common.configs.env_constants import JIUWEN_LOG_LEVEL_KEY
from jiuwen.common.log.base import performance_logger, get_thread_session

TOTAL_LOG_TAG = "total"
DETAIL_LOG_TAG = "detail"


class PerformanceLogBuffer:
    class Records:
        def __init__(self, extra: List[str]):
            self.extra: List[str] = extra
            self._record_map: Dict[str, Any] = dict()
            self._rw_lock = threading.Lock()

        def push(self, stage: str, cost: int):
            """push perf buffer content to queue"""
            with self._rw_lock:
                self._record_map[stage] = cost

        def get_record_map(self) -> Dict[str, int]:
            """get record buffer"""
            return self._record_map

    def __init__(self):
        self._perf_records: Dict[str, PerformanceLogBuffer.Records] = dict()
        self._lock = threading.Lock()
        log_config = config.get("logging", {})
        perf_log_level = logging.getLevelName(
            os.environ.get(JIUWEN_LOG_LEVEL_KEY, log_config.get("level", "INFO"))
        )
        if not isinstance(perf_log_level, int):
            perf_log_level = logging.INFO
        self._log_level: int = perf_log_level

    def init(self, uid: str, extra: List[str] = None):
        """create perf record queue"""
        with self._lock:
            try:
                records = self._perf_records.get(uid)
                if records is None:
                    records = PerformanceLogBuffer.Records(extra)
                    self._perf_records[uid] = records
                records.extra = extra
            except Exception as e:
                performance_logger.error(
                    f"Init buffer failed for uid {uid}: {e}",
                    simple_log="Init buffer failed",
                )
                return

    def debug(
        self, stage: str, timecost: int, uid: str = None, is_record: bool = False
    ):
        """perf record debug buffer"""
        self.buffer(logging.DEBUG, stage, timecost, uid, is_record)

    def info(self, stage: str, timecost: int, uid: str = None, is_record: bool = False):
        """perf record info buffer"""
        self.buffer(logging.INFO, stage, timecost, uid, is_record)

    def warning(
        self, stage: str, timecost: int, uid: str = None, is_record: bool = False
    ):
        """perf record warning buffer"""
        self.buffer(logging.WARNING, stage, timecost, uid, is_record)

    def error(
        self, stage: str, timecost: int, uid: str = None, is_record: bool = False
    ):
        """perf record error buffer"""
        self.buffer(logging.ERROR, stage, timecost, uid, is_record)

    def critical(
        self, stage: str, timecost: int, uid: str = None, is_record: bool = False
    ):
        """perf record critical buffer"""
        self.buffer(logging.CRITICAL, stage, timecost, uid, is_record)

    def buffer(
        self,
        level: int,
        stage: str,
        timecost: int,
        uid: str = None,
        is_record: bool = False,
    ):
        """save a perf log buffer"""
        if is_record:
            performance_logger.log(level, f"{DETAIL_LOG_TAG}|{stage}|{timecost}")
            return

        uid = uid or get_thread_session()
        if not uid or level < self._log_level:
            return

        with self._lock:
            records = self._perf_records.get(uid)
            if records is None:
                return
            records.push(stage, timecost)

    def record(self, uid: str = None):
        """record perf logs to console/logfile"""
        pass
