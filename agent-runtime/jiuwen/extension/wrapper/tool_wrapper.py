# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
ToolWrapper -- 统一工具包装器

通过 tool_type 参数决定实例化 RestfulApiWrapper 还是 McpToolWrapper。
使用 __getattr__ 魔术方法 + hasattr() 动态判断属性是否存在。
"""

from enum import Enum
from typing import Any, AsyncIterator, Iterator, Union

from jiuwen.common.log.base import logger
from jiuwen.orchestration.utils import Input, Output


class ToolType(str, Enum):
    RESTFUL = "restful"
    MCP = "mcp"
    SYSTEM_OPERATION = "SystemOperation"


class ToolWrapper:
    """
    统一工具包装器

    通过 tool_type 参数决定实例化 RestfulApiWrapper 还是 McpToolWrapper。
    使用 __getattr__ 魔术方法 + hasattr() 动态判断属性是否存在。

    Args:
        tool_id: 工具 ID
        agent_id: 代理 ID
        session_id: 会话 ID
        tool_type: 工具类型，"restful" 或 "mcp"，默认为 "restful"
    """

    def __init__(
        self,
        tool_id: str,
        agent_id: str,
        session_id: str,
        tool_type: Union[str, ToolType] = ToolType.RESTFUL,
    ):
        """
        初始化包装器

        Args:
            tool_id: 已注册到 ResourceMgr 的工具 ID
            agent_id: Agent ID
            session_id: Session ID
            tool_type: 工具类型，ToolType 枚举或字符串（"restful"/"mcp"），默认为 ToolType.RESTFUL
        """
        self._tool_id = tool_id
        self._agent_id = agent_id
        self._session_id = session_id
        self._tool_type = (
            ToolType(tool_type) if isinstance(tool_type, str) else tool_type
        )
        self._wrapper = None

    def _get_wrapper(self) -> Union[Any, None]:
        """
        延迟获取对应的 wrapper 实例

        Returns:
            RestfulApiWrapper 或 McpToolWrapper 实例
        """
        if self._wrapper is None:
            if self._tool_type == ToolType.RESTFUL:
                from jiuwen.extension.wrapper.restful_api_wrapper import (
                    RestfulApiWrapper,
                )

                self._wrapper = RestfulApiWrapper(
                    self._tool_id, self._agent_id, self._session_id
                )
            elif self._tool_type == ToolType.MCP:
                from jiuwen.extension.wrapper.mcp_tool_wrapper import McpToolWrapper

                self._wrapper = McpToolWrapper(
                    self._tool_id, self._agent_id, self._session_id
                )
            else:
                raise ValueError(
                    f"Invalid tool_type: {self._tool_type}, "
                    f"expected '{ToolType.RESTFUL.value}' or '{ToolType.MCP.value}'"
                )
        return self._wrapper

    def __getattr__(self, attr_name: str) -> Any:
        """
        统一属性访问方法

        当访问不存在的属性时，Python 会调用此方法。
        使用 hasattr() 动态判断属性是否存在。

        Args:
            attr_name: 被访问的属性名称

        Returns:
            属性值或 None
        """
        try:
            wrapper = self._get_wrapper()

            if hasattr(wrapper, attr_name):
                return getattr(wrapper, attr_name)
            else:
                logger.error(
                    f"Attribute '{attr_name}' is not available for tool_type '{self._tool_type.value}'. "
                    f"Returning None"
                )
                return None

        except AttributeError as as_e:
            logger.error(f"Failed to get attribute '{attr_name}' from wrapper: {as_e}")
            return None

    @property
    def is_restful(self) -> bool:
        """是否为 restful 类型"""
        return self._tool_type == ToolType.RESTFUL

    @property
    def is_mcp(self) -> bool:
        """是否为 mcp 类型"""
        return self._tool_type == ToolType.MCP

    @property
    def tool_type(self) -> ToolType:
        """工具类型"""
        return self._tool_type

    def __getstate__(self):
        """序列化时排除 _wrapper（懒加载，可重建）"""
        return {
            "_tool_id": self._tool_id,
            "_agent_id": self._agent_id,
            "_session_id": self._session_id,
            "_tool_type": self._tool_type,
            "_wrapper": None,
        }

    def __setstate__(self, state):
        """反序列化时恢复状态"""
        self.__dict__.update(state)

    def invoke(self, inputs: Input, **kwargs) -> Output:
        """
        同步调用

        Args:
            inputs: 输入参数
            **kwargs: 额外参数

        Returns:
            输出结果
        """
        return self._get_wrapper().invoke(inputs, **kwargs)

    async def ainvoke(self, inputs: Input, **kwargs) -> Output:
        """
        异步调用

        Args:
            inputs: 输入参数
            **kwargs: 额外参数

        Returns:
            输出结果
        """
        return await self._get_wrapper().ainvoke(inputs, **kwargs)

    def stream(self, inputs: Input, **kwargs) -> Iterator[Output]:
        """
        流式输出（仅 restful 支持）

        Args:
            inputs: 输入参数
            **kwargs: 额外参数

        Returns:
            输出迭代器
        """
        if self._tool_type != ToolType.RESTFUL:
            logger.error(
                f"stream() is not available for tool_type '{self._tool_type.value}'. "
                f"Only '{ToolType.RESTFUL.value}' is supported."
            )
            return iter([])
        return self._get_wrapper().stream(inputs, **kwargs)

    async def astream(self, inputs: Input, **kwargs) -> AsyncIterator[Output]:
        """
        异步流式输出（仅 restful 支持）

        Args:
            inputs: 输入参数
            **kwargs: 额外参数

        Yields:
            输出块
        """
        if self._tool_type != ToolType.RESTFUL:
            logger.error(
                f"astream() is not available for tool_type '{self._tool_type.value}'. "
                f"Only '{ToolType.RESTFUL.value}' is supported."
            )
            return
        async for chunk in self._get_wrapper().astream(inputs, **kwargs):
            yield chunk
