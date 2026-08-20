import datetime
from typing import AsyncIterable, List

from jiuwen.common.llm_service.language_model.base import InputType, LanguageModelOutput
from jiuwen.common.llm_service.messages import (
    BaseMessage as OldBaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage as OldSystemMessage,
    FunctionMessage,
    ToolMessage as OldToolMessage,
    ToolCall as OldToolCall,
    UsageMetadata,
)
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import ModelError
from openjiuwen.core.common.logging import llm_logger
from openjiuwen.core.foundation.llm.schema.message import (
    BaseMessage,
    UserMessage,
    AssistantMessage,
    SystemMessage,
    ToolMessage,
)
from openjiuwen.core.foundation.llm.schema.tool_call import ToolCall
from openjiuwen.core.foundation.tool.schema import ToolInfo
from openjiuwen.core.runner import Runner
from openjiuwen.core.session.agent import create_agent_session

BJ_TZ = datetime.timezone(datetime.timedelta(hours=8), name="Asia/Beijing")


class ModelWrapper:
    """Model 接口适配层

    Model 接口适配层，实现了新旧版本模型接口的无缝适配。
    - 隔离 Controller 层对具体 LLM 实现的依赖
    - 将旧版本 BaseChatModel.ainvoke 接口规范适配到新版本 openJiuwen 模型接口
    - 通过 Runner.resource_mgr.get_model 获取模型实例后调用 model.invoke
    - 输入输出类型严格遵循 BaseChatModel 定义，确保不引入额外数据结构
    """

    @staticmethod
    def _convert_tool_call(tool_call: OldToolCall | dict) -> ToolCall:
        """将旧格式工具调用转换为新格式

        支持处理 OldToolCall 对象或字典格式的工具调用

        Args:
            tool_call: 旧格式工具调用对象或字典

        Returns:
            ToolCall: 转换后的新格式工具调用
        """
        import json

        if isinstance(tool_call, dict):
            # 处理字典格式的工具调用
            if "function" in tool_call:
                # OpenAI 格式: {id, type, function: {name, arguments}}
                convert_dict = {
                    "type": tool_call.get("type", "function"),
                    "name": tool_call["function"].get("name", ""),
                    "arguments": tool_call["function"].get("arguments", ""),
                }
                if tool_call.get("id") is not None:
                    convert_dict["id"] = tool_call.get("id")
                return ToolCall(**convert_dict)
            else:
                # 扁平格式: {id, type, name, arguments}
                convert_dict = {
                    "type": tool_call.get("type", "function"),
                    "name": tool_call.get("name", ""),
                    "arguments": tool_call.get("arguments", ""),
                }
                if tool_call.get("id") is not None:
                    convert_dict["id"] = tool_call.get("id")
                return ToolCall(**convert_dict)
        else:
            # 处理旧格式 ToolCall 对象
            args = tool_call.args
            if not isinstance(args, str):
                try:
                    args = json.dumps(args, ensure_ascii=False)
                except (TypeError, ValueError):
                    args = str(args)

            convert_dict = {
                "type": "function",
                "name": tool_call.name,
                "arguments": args,
            }
            if hasattr(tool_call, "id") and tool_call.id is not None:
                convert_dict["id"] = tool_call.id
            return ToolCall(**convert_dict)

    @staticmethod
    def _convert_to_old_tool_call(tool_call: ToolCall) -> OldToolCall:
        """将新格式ToolCall转换为旧格式OldToolCall

        Args:
            tool_call: 新格式ToolCall对象

        Returns:
            OldToolCall: 转换后的旧格式工具调用
        """
        import json

        # 解析arguments为字典
        args = {}
        if tool_call.arguments:
            try:
                args = json.loads(tool_call.arguments)
                if not isinstance(args, dict):
                    llm_logger.warning(
                        f"Tool call arguments is not a dictionary: {tool_call.arguments}"
                    )
                    args = {}
            except json.JSONDecodeError as e:
                llm_logger.warning(
                    f"Invalid JSON in tool call arguments: {tool_call.arguments}. Error: {e}"
                )
                args = {}

        convert_dict = {"name": tool_call.name, "args": args}
        if tool_call.id is not None:
            convert_dict["id"] = tool_call.id
        return OldToolCall(**convert_dict)

    @staticmethod
    def _convert_input_to_model_format(
        input_data: InputType,
    ) -> tuple[List[BaseMessage], List[ToolInfo]]:
        """将 InputType 转换为 model.invoke 可使用的消息格式。

        Args:
            input_data: 模型输入，与 BaseChatModel.ainvoke 的 inputs 参数一致

        Returns:
            tuple[List[BaseMessage], List[ToolInfo]]: 转换后的新格式消息列表和工具列表

        Raises:
            ValueError: 输入格式错误时抛出
        """
        if not input_data:
            raise ValueError("Get empty input from LLM invoke")

        def _convert_message(message) -> BaseMessage:
            """转换单个消息到新格式"""
            if isinstance(message, dict):
                # 字典格式消息直接转换
                role = message.get("role")
                content = message.get("content", "")

                if role == "system":
                    convert_dict = {"content": content}
                    if message.get("name") is not None:
                        convert_dict["name"] = message.get("name")
                    return SystemMessage(**convert_dict)
                elif role == "user":
                    convert_dict = {"content": content}
                    if message.get("name") is not None:
                        convert_dict["name"] = message.get("name")
                    return UserMessage(**convert_dict)
                elif role == "assistant":
                    # 处理助手消息和工具调用
                    tool_calls = message.get("tool_calls")
                    new_tool_calls = []

                    if tool_calls:
                        for tc in tool_calls:
                            new_tool_calls.append(ModelWrapper._convert_tool_call(tc))

                    convert_dict = {"content": content}
                    if message.get("name") is not None:
                        convert_dict["name"] = message.get("name")
                    if new_tool_calls:
                        convert_dict["tool_calls"] = new_tool_calls
                    return AssistantMessage(**convert_dict)
                elif role in ["function", "tool"]:
                    convert_dict = {"content": content}
                    if message.get("name") is not None:
                        convert_dict["name"] = message.get("name")
                    tool_call_id = message.get("tool_call_id")
                    if tool_call_id is not None and tool_call_id != "":
                        convert_dict["tool_call_id"] = tool_call_id
                    return ToolMessage(**convert_dict)
                else:
                    raise ValueError(f"Unknown message role: {role}")

            elif isinstance(message, OldBaseMessage):
                # 旧格式 BaseMessage 转换
                if isinstance(message, HumanMessage):
                    convert_dict = {"content": message.content, "name": message.name}
                    return UserMessage(**convert_dict)
                elif isinstance(message, AIMessage):
                    # 转换工具调用
                    new_tool_calls = []
                    if message.tool_calls:
                        if isinstance(message.tool_calls, list):
                            # 多个工具调用
                            for tc in message.tool_calls:
                                new_tool_calls.append(
                                    ModelWrapper._convert_tool_call(tc)
                                )
                        else:
                            # 单个工具调用
                            new_tool_calls.append(
                                ModelWrapper._convert_tool_call(message.tool_calls)
                            )

                    convert_dict = {"content": message.content}
                    if message.name is not None:
                        convert_dict["name"] = message.name
                    if new_tool_calls:
                        convert_dict["tool_calls"] = new_tool_calls
                    return AssistantMessage(**convert_dict)
                elif isinstance(message, OldSystemMessage):
                    convert_dict = {"content": message.content}
                    if message.name is not None:
                        convert_dict["name"] = message.name
                    return SystemMessage(**convert_dict)
                elif isinstance(message, (FunctionMessage, OldToolMessage)):
                    convert_dict = {"content": message.content}
                    if message.name is not None:
                        convert_dict["name"] = message.name
                    tool_call_id = getattr(message, "tool_call_id", None)
                    if tool_call_id is not None and tool_call_id != "":
                        convert_dict["tool_call_id"] = tool_call_id
                    return ToolMessage(**convert_dict)
                else:
                    raise ValueError(
                        f"Unknown old message type: {type(message).__name__}"
                    )

            else:
                raise TypeError(f"Unknown message type: {type(message).__name__}")

        if isinstance(input_data, str):
            # 字符串输入转换为 UserMessage
            convert_dict = {"content": input_data}
            return [UserMessage(**convert_dict)], []

        elif isinstance(input_data, list):
            # List[dict] 或 List[OldBaseMessage] 转换
            return [_convert_message(msg) for msg in input_data], []

        elif isinstance(input_data, dict):
            # LanguageModelInput 提取 messages 并转换
            messages = input_data.get("messages")
            tools = input_data.get("tools")
            if tools is None:
                tools = []
            if not messages:
                raise ValueError("LanguageModelInput must contain 'messages' field")
            new_tools = []
            for tool in tools:
                if isinstance(tool, dict):
                    new_tool = ToolInfo(
                        name=tool.get("name") or "",
                        description=tool.get("description") or "",
                        parameters=tool.get("parameters")
                        or {"type": "object", "properties": {}},
                    )
                else:
                    new_tool = ToolInfo(
                        name=tool.name or "",
                        description=tool.description or "",
                        parameters=tool.parameters
                        or {"type": "object", "properties": {}},
                    )
                new_tools.append(new_tool)

            return [_convert_message(msg) for msg in messages], new_tools

        else:
            raise TypeError(f"Get wrong type from input: {type(input_data).__name__}")

    @staticmethod
    def _post_stream_message(
        model_response: AssistantMessage,
    ) -> tuple[AIMessage, list[ToolCall] | None]:
        """将 model.invoke 的返回值转换为 AIMessage。

        Args:
            model_response: model.invoke 的返回值，包含 role、content、tool_calls 等属性

        Returns:
            AIMessage: 转换后的 AIMessage 对象
        """
        # 转换工具调用
        tool_calls = None
        if hasattr(model_response, "tool_calls") and model_response.tool_calls:
            if isinstance(model_response.tool_calls, list):
                tool_calls = model_response.tool_calls

        # 转换 usage_metadata 格式
        usage_metadata = model_response.usage_metadata
        if usage_metadata:
            data = usage_metadata.model_dump()
            data["errmsg"] = data.pop("err_msg", "")
            data["requests_start_time"] = data.pop("request_start_time", "")
            data.pop("cache_tokens", None)
            usage_metadata = UsageMetadata(**data)

        convert_dict = {"content": model_response.content}
        if usage_metadata is not None:
            convert_dict["usage_metadata"] = usage_metadata
        reasoning_content = getattr(model_response, "reasoning_content", None)
        if reasoning_content is not None:
            convert_dict["reasoning_content"] = reasoning_content
        raw_content = getattr(model_response, "parser_content", None)
        if raw_content is not None:
            convert_dict["raw_content"] = raw_content
        name = getattr(model_response, "name", None)
        if name is not None:
            convert_dict["name"] = name
        id_value = getattr(model_response, "id", None)
        if id_value is not None:
            convert_dict["id"] = id_value
        # 构建 AIMessage
        return AIMessage(**convert_dict), tool_calls

    async def ainvoke(
        self, inputs: InputType, model_id: str, session_id: str, **kwargs
    ) -> LanguageModelOutput:
        """同步（批）调用Model。

        Controller Mode 的意图识别场景使用此接口。

        Args:
            inputs:     模型输入，与 BaseChatModel.ainvoke 的 inputs 参数一致
            model_id:  模型唯一标识，用于查找已注册的 Model 实例
            session_id:  对话级 Session 对象的唯一标识
            **kwargs:  额外参数，如 temperature、top_p 等

        Returns:
            LanguageModelOutput: 模型响应（含content、usage_metadata 等）

        Raises:
            ModelError: 调用失败时抛出
        """
        temperature = kwargs.get("temperature", None)
        top_p = kwargs.get("top_p", None)
        max_tokens = kwargs.get("max_tokens", None)
        stop = kwargs.get("stop", None)
        model_name = kwargs.get("model", None)
        timeout = kwargs.get("timeout", None)

        if not model_id or not session_id:
            raise ValueError("model_id and session_id are required")

        messages, tools = self._convert_input_to_model_format(inputs)
        agent_session = create_agent_session(session_id=session_id)
        model = await Runner.resource_mgr.get_model(
            model_id=model_id, session=agent_session
        )
        if model is None:
            raise ModelError(
                StatusCode.MODEL_CALL_FAILED,
                msg=f"Model resource not found or failed to instantiate: model_id={model_id}",
            )
        try:
            model_response = await model.invoke(
                messages,
                tools=tools,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stop=stop,
                model=model_name,
                timeout=timeout,
            )
        except Exception as e:
            error_msg = f"Model invoke failed: {e}"
            raise ModelError(StatusCode.MODEL_CALL_FAILED, msg=error_msg)

        cur_ai_message, tool_calls = self._post_stream_message(model_response)
        tcs = []
        if tool_calls is not None:
            for tc in tool_calls:
                tcs.append(self._convert_to_old_tool_call(tc))
        cur_ai_message.tool_calls = tcs
        return cur_ai_message

    async def astream(
        self, inputs: InputType, model_id: str, session_id: str, **kwargs
    ) -> AsyncIterable[LanguageModelOutput]:
        """流式调用 Model。

        预留给 ReactMode 等流式场景，Controller Mode 当前不使用。

        Args:
            inputs:     模型输入，与 BaseChatModel.ainvoke 的 inputs 参数一致
            model_id:  模型唯一标识，用于查找已注册的 Model 实例
            session_id:  对话级 Session 对象的唯一标识
            **kwargs:  额外参数，如 temperature、top_p 等

        Yields:
            LanguageModelOutput: 流式输出块

        Raises:
            ModelError: 调用失败时抛出
        """
        temperature = kwargs.get("temperature", None)
        top_p = kwargs.get("top_p", None)
        max_tokens = kwargs.get("max_tokens", None)
        stop = kwargs.get("stop", None)
        model_name = kwargs.get("model", None)
        timeout = kwargs.get("timeout", None)

        if not model_id or not session_id:
            raise ValueError("model_id and session_id are required")

        messages, tools = self._convert_input_to_model_format(inputs)
        request_start_time = datetime.datetime.now(tz=BJ_TZ).isoformat()
        first_token_time = ""
        tc_id = ""
        agent_session = create_agent_session(session_id=session_id)
        model = await Runner.resource_mgr.get_model(
            model_id=model_id, session=agent_session
        )
        if model is None:
            raise ModelError(
                StatusCode.MODEL_CALL_FAILED,
                msg=f"Model resource not found or failed to instantiate: model_id={model_id}",
            )
        try:
            assemble_tool_calls = {}
            total_content = ""
            usage_metadata = UsageMetadata()
            async for chunk in model.stream(
                messages,
                tools=tools,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stop=stop,
                model=model_name,
                timeout=timeout,
            ):
                if not first_token_time:
                    first_token_time = datetime.datetime.now(tz=BJ_TZ).isoformat()
                cur_ai_message, tool_calls = self._post_stream_message(chunk)
                if cur_ai_message.content:
                    if not cur_ai_message.usage_metadata:
                        cur_ai_message.usage_metadata = UsageMetadata()
                    if cur_ai_message.usage_metadata:
                        cur_ai_message.usage_metadata.errmsg = "success"
                        cur_ai_message.usage_metadata.first_token_time = (
                            first_token_time
                        )
                        cur_ai_message.usage_metadata.requests_start_time = (
                            request_start_time
                        )
                        usage_metadata = cur_ai_message.usage_metadata
                    yield cur_ai_message
                    total_content += cur_ai_message.content
                elif tool_calls:
                    for tc in tool_calls:
                        if tc.id != "" and tc.id != tc_id:
                            tc_id = tc.id
                        if tc_id not in assemble_tool_calls:
                            assemble_tool_calls[tc_id] = tc
                        else:
                            assemble_tool_calls[tc_id].arguments += tc.arguments
                elif cur_ai_message.usage_metadata:
                    usage_metadata = cur_ai_message.usage_metadata
                    usage_metadata.errmsg = "success"
                    usage_metadata.first_token_time = first_token_time
                    usage_metadata.requests_start_time = request_start_time
            return_tool_calls = [
                self._convert_to_old_tool_call(tc)
                for tc in assemble_tool_calls.values()
            ]
            if return_tool_calls:
                usage_metadata.finish_reason = "function_call"
                yield AIMessage(
                    content=total_content,
                    tool_calls=return_tool_calls,
                    usage_metadata=usage_metadata,
                )
            elif not total_content:
                raise ModelError(
                    StatusCode.MODEL_CALL_FAILED,
                    msg="Model stream returned empty content",
                )
            else:
                usage_metadata.finish_reason = "stop"
                yield AIMessage(content=total_content, usage_metadata=usage_metadata)
        except Exception as e:
            error_msg = f"Model stream failed: {e}"
            llm_logger.error(error_msg)
            raise ModelError(StatusCode.MODEL_CALL_FAILED, msg=error_msg)
