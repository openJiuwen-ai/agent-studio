# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""日志格式常量。

单独成模块是为了让日志装配能发生在最早的导入阶段：这里只依赖标准库，导入它不会
连带拉起 agent-core / jiuwen 的业务模块（那些模块在导入期就会打日志，会先在
agent-core 默认配置下落到 ./logs/ 里的多余文件）。
"""

COMMON_LOG_FORMAT = (
    "%(asctime)s,%(msecs)03d|%(log_type)s|%(filename)s:%(lineno)d|%(funcName)s|"
    "%(trace_id)s|%(execution_id)s|%(request_id)s|%(levelname)s|%(message)s"
)
PERFORMANCE_LOG_FORMAT = (
    "%(asctime)s,%(msecs)03d|%(log_type)s|%(trace_id)s|%(execution_id)s|%(request_id)s|"
    "%(levelname)s|%(message)s"
)
DEFAULT_LOG_FORMAT = "%(asctime)s,%(msecs)03d|%(log_type)s|%(trace_id)s|%(levelname)s|%(message)s"
