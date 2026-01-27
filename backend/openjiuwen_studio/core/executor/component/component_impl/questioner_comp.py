# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

from typing import AsyncIterator

from openjiuwen.core.component.questioner_comp import QuestionerComponent as BaseQuestionerComponent
from openjiuwen.core.component.questioner_comp import QuestionerExecutable as BaseQuestionerExecutable
from openjiuwen.core.component.questioner_comp import QuestionerState
from openjiuwen.core.graph.executable import Input, Output, Executable
from openjiuwen.core.runtime.runtime import Runtime
from openjiuwen.core.context_engine.base import Context


class QuestionerExecutable(BaseQuestionerExecutable):
    async def stream(self, inputs: Input, runtime: Runtime, context: Context) -> AsyncIterator[Output]:
        result = await self.invoke(inputs, runtime, context)
        yield result


class QuestionerComponent(BaseQuestionerComponent):
    def to_executable(self) -> Executable:
        return QuestionerExecutable(self._questioner_config).state(QuestionerState())
