#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
"""
BaseChatModel
"""

import json
from abc import ABC
from typing import List, Any, Iterator, AsyncIterator, Dict, Union, Tuple
from typing_extensions import TypedDict

from jiuwen.common.llm_service.messages import (
    BaseMessage,
    Tool,
    HumanMessage,
    AIMessage,
    SystemMessage,
    FunctionMessage,
    ChatMessage,
    ToolMessage,
)
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.llm_service.utils import Runnable
from jiuwen.memory.conversation import ConversationMemory
from jiuwen.orchestration import Invokable
from pydantic import ConfigDict

LanguageModelOutput = BaseMessage


class LanguageModelInput(TypedDict):
    """LanguageModelInput class"""

    messages: List[BaseMessage]
    tools: List[Tool]


InputType = Union[str, LanguageModelInput, List[BaseMessage], List[dict]]


class BaseChatModel(Invokable, Runnable[LanguageModelInput, LanguageModelOutput], ABC):
    """BaseChatModel class
    +---------------------------+------------------------------------------------------+--------------------------+
    |Method                     | Input                                                | Output                   |
    +===========================+======================================================+==========================+
    |`invoke`                   | str | List[dict | BaseMessage] | LanguageModelInput  | BaseMessage              |
    +---------------------------+------------------------------------------------------+--------------------------+

    """

    memory: ConversationMemory = None
    model_config = ConfigDict()
    model_config["arbitrary_types_allowed"] = True

    @staticmethod
    def _convert_message_to_dict(message: BaseMessage) -> Dict[str, Any]:
        """Convert a message to a dictionary.

        Args:
            message: The message.

        Returns:
            The dictionary.
        """
        role_str = "role"
        content_str = "content"
        function_str = "tool"
        if isinstance(message, HumanMessage):
            message_dict = {role_str: "user", content_str: message.content}
        elif isinstance(message, AIMessage):
            message_dict = {
                role_str: "assistant",
                content_str: message.content if message.content else "null",
            }
            if isinstance(message.tool_calls, list) and len(message.tool_calls) > 0:
                function_dict = []
                for tool in message.tool_calls:
                    function_dict.append(
                        dict(
                            function=dict(
                                name=tool.name,
                                arguments=json.dumps(tool.args, ensure_ascii=False),
                            ),
                            id=tool.id,
                            type="function",
                        )
                    )
                message_dict.update(dict(tool_calls=function_dict))
        elif isinstance(message, SystemMessage):
            message_dict = {role_str: "system", content_str: message.content}
        elif isinstance(message, FunctionMessage):
            message_dict = {
                role_str: function_str,
                content_str: message.content,
                "name": message.name,
            }
        elif isinstance(message, ChatMessage):
            message_dict = {role_str: function_str, content_str: message.content}
        elif isinstance(message, ToolMessage):
            message_dict = {
                role_str: function_str,
                content_str: message.content,
                "name": message.name,
                "tool_call_id": message.tool_call_id,
            }
        else:
            raise ValueError("Got unknown type Message.")
        return message_dict

    @staticmethod
    def __convert_input_to_message(inputs: InputType) -> List[BaseMessage]:
        """__convert_input_to_message"""
        if not inputs:
            raise ValueError("Get empty input from LLM invoke")
        if isinstance(inputs, str):
            messages = [HumanMessage(content=inputs)]
        elif isinstance(inputs, list):
            if isinstance(inputs[0], dict):
                messages = ModelUtil.switch_message(messages=inputs)
            elif isinstance(inputs[0], BaseMessage):
                messages = inputs
            else:
                raise TypeError("Get wrong type list from input")
        else:
            raise TypeError("Get wrong type from input")
        return messages

    @staticmethod
    def _extract_tokens_from_response(
        response_data: Dict[str, Any],
    ) -> Tuple[int, int, int]:
        """
        Extract token information from LLM response data.

        Args:
            response_data: Raw response from LLM.

        Returns:
            A tuple containing input_tokens, output_tokens, and total_tokens.
        """
        # Initialize with zeros
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        if "usage" in response_data:
            usage_data = response_data["usage"]
            if isinstance(usage_data, dict):
                input_tokens = usage_data.get(
                    "prompt_tokens", usage_data.get("input_tokens", 0)
                )
                output_tokens = usage_data.get(
                    "completion_tokens", usage_data.get("output_tokens", 0)
                )
                total_tokens = usage_data.get("total_tokens", 0)
            elif hasattr(usage_data, "prompt_tokens"):
                input_tokens = getattr(usage_data, "prompt_tokens", 0)
                output_tokens = getattr(usage_data, "completion_tokens", 0)
                total_tokens = getattr(usage_data, "total_tokens", 0)
            elif hasattr(usage_data, "input_tokens"):
                input_tokens = getattr(usage_data, "input_tokens", 0)
                output_tokens = getattr(usage_data, "output_tokens", 0)
                total_tokens = getattr(usage_data, "total_tokens", 0)

        return input_tokens, output_tokens, total_tokens

    def invoke(self, inputs: InputType, **kwargs) -> LanguageModelOutput:
        """invoke"""
        if isinstance(inputs, dict):
            return self._chat(inputs.get("messages"), inputs.get("tools"))
        return self._chat(self.__convert_input_to_message(inputs=inputs))

    async def ainvoke(self, inputs: InputType, **kwargs) -> LanguageModelOutput:
        if isinstance(inputs, dict):
            return await self._achat(inputs.get("messages"), inputs.get("tools"))
        return await self._achat(self.__convert_input_to_message(inputs=inputs))

    def stream(self, inputs: InputType, **kwargs) -> Iterator[LanguageModelOutput]:
        if isinstance(inputs, dict):
            return self._stream(inputs.get("messages"), inputs.get("tools"), **kwargs)
        return self._stream(self.__convert_input_to_message(inputs=inputs))

    async def astream(
        self, inputs: InputType, **kwargs
    ) -> AsyncIterator[LanguageModelOutput]:
        if isinstance(inputs, dict):
            for item in self._stream(
                inputs.get("messages"), inputs.get("tools"), **kwargs
            ):
                yield item
        else:
            for item in self._stream(self.__convert_input_to_message(inputs=inputs)):
                yield item

    def _chat(
        self,
        messages: List[BaseMessage],
        tools: List[Tool] = None,
        **kwargs: Any,
    ) -> LanguageModelOutput:
        pass

    async def _achat(
        self,
        messages: List[BaseMessage],
        tools: List[Tool] = None,
        **kwargs: Any,
    ) -> LanguageModelOutput:
        return self._chat(messages, tools, **kwargs)

    def _stream(
        self,
        messages: List[BaseMessage],
        tools: List[Tool] = None,
        **kwargs: Any,
    ) -> Iterator[LanguageModelOutput]:
        pass

    async def _astream(
        self,
        messages: List[BaseMessage],
        tools: List[Tool] = None,
        **kwargs: Any,
    ) -> AsyncIterator[LanguageModelOutput]:
        return self._stream(messages, tools, **kwargs)
