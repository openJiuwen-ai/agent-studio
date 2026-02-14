#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from typing import AsyncIterator

from openjiuwen.core.workflow import QuestionerConfig, QuestionerComponent
from openjiuwen.core.workflow.components.llm.questioner_comp import QuestionerExecutable, QuestionerState
from openjiuwen.core.graph.executable import Executable, Input, Output
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.workflow.components import Session
from openjiuwen.core.common.logging import logger


class QuestionerExecutableWrapper(QuestionerExecutable):
    """
    Wrapper for QuestionerExecutable that adds stream() method support.
    
    The original QuestionerExecutable only implements invoke() method,
    but when End node has stream_output=true, the system tries to call
    stream() method on upstream components. This wrapper delegates
    stream() calls to invoke() method.
    """
    
    async def stream(self, inputs: Input, session: Session, context: ModelContext) -> AsyncIterator[Output]:
        """
        Stream method that delegates to invoke.
        
        Since Questioner doesn't actually produce streaming output,
        we just invoke it and yield the result as a single chunk.
        """
        logger.debug(f"QuestionerExecutableWrapper stream method called, delegating to invoke")
        result = await self.invoke(inputs, session, context)
        yield result


class QuestionerComponentWrapper(QuestionerComponent):
    """
    Wrapper for QuestionerComponent that creates QuestionerExecutableWrapper
    instead of the original QuestionerExecutable.
    """
    
    def __init__(self, questioner_comp_config: QuestionerConfig = None):
        super().__init__(questioner_comp_config)
        self._questioner_config = questioner_comp_config
    
    def to_executable(self) -> Executable:
        """Return wrapped executable with stream support"""
        return QuestionerExecutableWrapper(self._questioner_config).state(QuestionerState())
