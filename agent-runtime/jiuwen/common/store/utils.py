#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import importlib
import os
from abc import ABC, abstractmethod
from functools import wraps
from typing import Callable

from jiuwen.common.log.base import logger


class StoreCallbacks(ABC):
    @abstractmethod
    def handle_failure(self, e: Exception):
        """abstract failure handler for exception callbacks"""


class StoreHandler(ABC):
    def __init__(self):
        self._callbacks: StoreCallbacks = DefaultStoreCallbacks()

    def set_callbacks(self, callbacks: StoreCallbacks = None, env_var: str = ""):
        """set exception callbacks"""
        if callbacks and isinstance(callbacks, StoreCallbacks):
            self._callbacks = callbacks
            return
        if not env_var:
            return

        self._load_callbacks_from_env(env_var)

    def handle(self, func) -> Callable:
        """store call wrapper"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                self._callbacks.handle_failure(e)
                raise e

        return wrapper

    def _load_callbacks_from_env(self, env_var):
        callback_instance_path: str = os.environ.get(env_var, "")
        if not callback_instance_path or not isinstance(callback_instance_path, str):
            return

        cbk_items = callback_instance_path.strip().split(":")
        if len(cbk_items) != 2:
            logger.warning("Redis callbacks instance path is invalid")
            return
        cbk_module_str, cbk_class_str = cbk_items[0], cbk_items[1]
        try:
            cbk_module = importlib.import_module(cbk_module_str)
            cbk_class = getattr(cbk_module, cbk_class_str)
            cbk_instance = cbk_class()
        except (ImportError, AttributeError) as e:
            logger.error(
                f"Failed to import callback module {cbk_module_str} and callback class {cbk_class_str}: {e}"
            )
            return

        self._callbacks = cbk_instance


class DefaultStoreCallbacks(StoreCallbacks):
    def handle_failure(self, e: Exception):
        """default exception callback"""
        pass
