#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""Function class"""

import inspect
from abc import ABC
from typing import List, Callable

from jiuwen.insight.manager import TraceManager
from jiuwen.insight.utils import (
    extract_tool_trace_info,
    get_instance_info,
)
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.utils import Input, Output
from jiuwen.plugin.models.param import Param


class Function(Invokable, ABC):
    """Function class"""

    def __init__(
        self,
        name: str = "",
        description: str = "",
        params: List[Param] = None,
        func: Callable = None,
        plugin_name: str = "",
        plugin_desc: str = "",
        label: str = "",
        **kwargs,
    ):
        self.name: str = name
        self.description: str = description
        self.params: List[Param] = params
        self.callable_function: Callable = func
        self.plugin_name = plugin_name
        self.plugin_desc = plugin_desc
        self.label = label
        self.related_info: dict = kwargs.get("related_info")
        self.status: int = kwargs.get("status")
        self.principle: str = kwargs.get("principle")
        self.user_id: str = kwargs.get("user_id", "")

    async def ainvoke(self, inputs: Input, **kwargs) -> Output:
        if not isinstance(inputs, dict):
            raise TypeError(
                "Plugin.ainvoke() excepted 'dict', but got {}".format(
                    type(inputs).__name__
                )
            )
        inputs = self._format_input_with_default_when_required(inputs)
        instance_info = get_instance_info(self)
        # planner tool_call 标识入扁平键（core handler 盖 gen_ai.tool.*）
        instance_info.update(extract_tool_trace_info(kwargs))
        trace_manager = TraceManager.generate_manager(
            kwargs.pop("trace_handlers", None), instance_info
        )
        await trace_manager.on_plugin_start(inputs)
        try:
            res = self.callable_function(**inputs)
            if inspect.isawaitable(res):
                res = await res
            await trace_manager.on_plugin_end(res)
            return res
        except Exception as error:
            await trace_manager.on_plugin_error(error)
            raise error

    def invoke(self, inputs: Input, **kwargs) -> Output:
        """Synchronous invoke, delegates to ainvoke."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.ainvoke(inputs, **kwargs))

    def _format_input_with_default_when_required(self, inputs: dict):
        params_default_dict = {}
        for param in self.params:
            if param.required and (param.default_value or param.default_value is False):
                params_default_dict[param.name] = param.default_value
        for field, value in params_default_dict.items():
            if not inputs.get(field) and inputs.get(field) is not False:
                inputs[field] = value
        return inputs
