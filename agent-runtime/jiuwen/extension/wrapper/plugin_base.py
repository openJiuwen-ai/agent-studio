# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
PluginBase -- 自定义插件基类。

客户开发的插件需继承此基类，实现 ``invoke`` 方法（非流式）和可选的
``stream`` 方法（流式）。框架通过 ``CustomPluginTool`` 将插件实例包装为
``Tool``，注册到 ``Runner.resource_mgr``，供智能体和工作流调用。

使用示例::

    from jiuwen.extension.wrapper.plugin_base import PluginBase

    class WeatherPlugin(PluginBase):
        async def invoke(self, inputs, **kwargs):
            city = inputs.get("city")
            return {"temperature": 25, "city": city}

        async def stream(self, inputs, **kwargs):
            city = inputs.get("city")
            yield f"正在查询 {city} 天气..."
            yield '{"temperature": 25}'
"""

import json
from abc import ABC, abstractmethod
from typing import AsyncIterator, List

from jiuwen.plugin.models.param import Param


class PluginBase(ABC):
    """自定义插件基类。

    客户开发的插件继承此类，实现 ``invoke`` 方法即可被框架调用。
    ``stream`` 方法有默认实现（降级为 ``invoke``），如需流式输出则覆写。

    Args:
        params: 框架传入的参数定义列表（由 IR ``arguments`` 反序列化而来）。
            插件可通过 ``self.params`` 访问参数名、类型、描述等信息。
        **config: 来自 IR 配置的额外字段，按需取用。
    """

    def __init__(self, params: List[Param] = None, **config):
        self._params: List[Param] = params or []
        self._config: dict = config

    @property
    def params(self) -> List[Param]:
        """参数定义列表"""
        return self._params

    @property
    def config(self) -> dict:
        """原始 IR 配置（不含 params）"""
        return self._config

    @abstractmethod
    async def invoke(self, inputs: dict, **kwargs) -> dict:
        """非流式执行。

        Args:
            inputs: 输入参数字典，键为参数名，值为用户提供值。
            **kwargs: 框架保留参数（如 ``runtime_auth``）。

        Returns:
            dict: 执行结果。若包含 ``errCode`` 键则原样透传，
                  否则框架包装为 ``{"data": result, "errCode": 0, "errMessage": ""}``。
        """
        ...

    async def stream(self, inputs: dict, **kwargs) -> AsyncIterator[str]:
        """流式执行。

        默认实现：调用 ``invoke`` 并将结果作为单条 JSON 字符串 yield。
        子类可覆写以实现逐条流式输出。

        Args:
            inputs: 输入参数字典。
            **kwargs: 框架保留参数。

        Yields:
            str: 流式数据片段。
        """
        result = await self.invoke(inputs, **kwargs)
        yield json.dumps(result, ensure_ascii=False)
