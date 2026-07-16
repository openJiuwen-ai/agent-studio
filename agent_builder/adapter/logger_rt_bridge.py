# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
Logger bridge: full replica of agent_runtime.common.logger.

Provides an identical logging.Logger instance configured with the same
format and default level as the original.
"""

import logging


def _logging_initialized() -> bool:
    """检查根 logger 是否已配置 handler。"""
    root = logging.getLogger()
    return any(isinstance(h, logging.StreamHandler) for h in root.handlers)


_logger = logging.getLogger("agent_runtime")
if not _logger.handlers and not _logging_initialized():
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)


logger = _logger
