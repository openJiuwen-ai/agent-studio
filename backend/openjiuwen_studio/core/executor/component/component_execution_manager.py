#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

import asyncio
import threading
from dataclasses import dataclass
from typing import Dict, Optional
from openjiuwen.core.common.logging import logger
from openjiuwen.core.workflow.components import Session


@dataclass
class ComponentExecutionRegistration:
    execution_id: str
    session: Optional[Session] = None
    task: Optional[asyncio.Task] = None


@dataclass
class ComponentExecutionInfo(ComponentExecutionRegistration):
    thread_id: Optional[int] = None


class ComponentExecutionManager:
    def __init__(self):
        self._executions: Dict[str, ComponentExecutionInfo] = {}
        self._cancelled_flags: Dict[str, bool] = {}
        self._lock = threading.Lock()

    def register_execution(self, reg: ComponentExecutionRegistration):
        with self._lock:
            key = reg.execution_id
            self._executions[key] = ComponentExecutionInfo(
                execution_id=key, session=reg.session, task=reg.task, thread_id=threading.get_ident()
            )
            self._cancelled_flags[key] = False
            logger.info(f"Registered component execution: {key}")

    def unregister_execution(self, execution_id: str):
        with self._lock:
            if execution_id in self._executions:
                self._executions.pop(execution_id)
                self._cancelled_flags.pop(execution_id, None)
                logger.info(f"Unregistered component execution: {execution_id}")

    def is_cancelled(self, execution_id: str) -> bool:
        with self._lock:
            return self._cancelled_flags.get(execution_id, False)

    def get_execution(self, execution_id: str) -> Optional[ComponentExecutionInfo]:
        with self._lock:
            return self._executions.get(execution_id)

    async def cancel_execution(self, execution_id: str) -> bool:
        info = self.get_execution(execution_id)
        if not info:
            logger.warning(f"Component execution not found: {execution_id}")
            return False
        try:
            with self._lock:
                self._cancelled_flags[execution_id] = True
            logger.info(f"Set cancelled flag for {execution_id}")

            if info.task and not info.task.done():
                info.task.cancel()
                logger.info(f"Component run task cancelled by user: {execution_id}")
                try:
                    await info.task
                except asyncio.CancelledError:
                    logger.info(f"Task cancelled: {execution_id}")
                except Exception as e:
                    logger.error(f"Cancel task error: {e}", exc_info=True)

            self.unregister_execution(execution_id)
            return True
        except Exception as e:
            logger.error(f"Cancel component execution error: {e}", exc_info=True)
            return False


component_execution_manager = ComponentExecutionManager()
