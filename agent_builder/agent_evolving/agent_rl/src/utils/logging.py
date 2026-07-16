# -*- coding:utf-8 -*-
#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import logging
import sys

ROOT_LOGGER_NAME = "JiuwenAgentRL"


def _configure_root_logger(level=logging.INFO, name=ROOT_LOGGER_NAME):
    """Configure the root logger with a stream handler, formatter, and log level.
    If the logger is already configured, it is returned directly.
    """
    _logger = logging.getLogger(name)
    if _logger.handlers:
        return _logger
    _logger.setLevel(level)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] (Process-%(process)d %(name)s)   %(message)s"
    )
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    _logger.propagate = False
    return _logger


def get_logger(name=None):
    """Retrieve the root logger or a namespaced child logger if a name is provided.
    Ensures that the root logger is configured before creating child loggers.
    """
    root_logger = _configure_root_logger()
    if not name:
        return root_logger
    return root_logger.getChild(name)


logger = get_logger()
