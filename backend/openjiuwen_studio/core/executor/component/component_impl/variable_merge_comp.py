#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from typing import Any, Dict
from openjiuwen.core.workflow import WorkflowComponent, Input, Output
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.workflow.components import Session

from openjiuwen_studio.core.common.dsl import VariMergeConfig


class VariableMergeComponent(WorkflowComponent):
    def __init__(self, conf: VariMergeConfig) -> None:
        super().__init__()
        self.conf = conf
        self.groups = self.conf.groups

    def _is_empty(self, value: Any) -> bool:
        """检查组件输出值是否为空"""
        return value in [None, "", [], {}, ()] or (hasattr(value, '__len__') and len(value) == 0)

    async def invoke(self, inputs: Input, session: Session, context: ModelContext) -> Output:
        result: Dict[str, Any] = {}
        for group in self.groups:
            for item in group.items:
                if item in inputs and not self._is_empty(inputs[item]):
                    result[group.name] = inputs[item]
                    break
        return result
