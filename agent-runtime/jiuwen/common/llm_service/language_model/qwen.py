#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
"""
QwenMax service
"""

import datetime
import json
from typing import List, Optional, Any, Dict, Tuple, Iterator

import requests
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.llm_service.language_model.base import (
    BaseChatModel,
    LanguageModelOutput,
)
from jiuwen.common.llm_service.messages import (
    BaseMessage,
    AIMessage,
    Tool,
    UsageMetadata,
    ToolCall,
)
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.security.cryptor import Crypt
from jiuwen.prompt import TemplateManager
from pydantic import Field, BaseModel

MESSAGES_STR = "messages"
UTF_STR = "utf-8"
# 定义北京时间的消息格式
BJ_TZ = datetime.timezone(datetime.timedelta(hours=8), name="Asia/Beijing")


class DataField:
    """DataField class."""

    data_str = "data:"
    choices_str = "choices"


class Qwen(BaseModel, BaseChatModel):
    """agentBuilder LLM chat models API."""

    @property
    def _default_params(self) -> Dict[str, Any]:
        """Get the default parameters for calling agent-builderAPI."""
        params = {
            "model": self.model_name,
            "stream": self.streaming,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }
        if self.thinking is not None:
            params["enable_thinking"] = self.thinking["type"] == "enabled"
        return params

    """Base auth for API requests"""
    api_key: Optional[str] = Field(default="", alias="api_key")
    """Base URL path for API requests"""
    api_base: Optional[str] = Field(default="", alias="api_base")
    """Model name for API requests"""
    model_name: Optional[str] = Field(default="", alias="model")
    temperature: float = Field(default=0.95)
    top_p: float = Field(default=0.1)
    """Whether to stream the results or not."""
    streaming: bool = Field(default=False, alias="stream")
    thinking: Optional[object] = Field(default=None, alias="thinking")

    if model_name == "" or api_key == "":
        raise JiuWenBaseException(
            StatusCode.LLM_CONFIG_MISS_ERROR.code,
            StatusCode.LLM_CONFIG_MISS_ERROR.errmsg.format(
                error_msg="please check qwen-max api_base, model_name value."
            ),
        )

    class Config:
        """Configuration for this pydantic object."""

        populate_by_name = True

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "qwen"

    def _create_message_dicts(
        self, messages: List[BaseMessage]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Convert BaseMessage to a message_dict."""
        message_dicts = [self._convert_message_to_dict(m) for m in messages]
        params = self._default_params
        return message_dicts, params

    def _request_params(
        self, messages: List[BaseMessage], tools: [Dict[str, Any]] = None
    ):
        """agentBuilder Construct the information required for the request."""
        headers = {
            "x-apig-appcode": Crypt().decrypt(self.api_key),
            "Content-Type": "application/json",
        }
        system_message = TemplateManager().get(
            name=ModelUtil.system_message_prompt, filters={"tag": self.model_name}
        )
        message_dicts, params = self._create_message_dicts(messages)
        system_message.content.extend(message_dicts)
        top_p, temperature = ModelUtil.truncate_params(params)
        payload = {
            **params,
            MESSAGES_STR: system_message.content,
        }
        new_tools = tools
        if tools:
            new_tools = []
            for tool in tools:
                new_tools.append({"type": "function", "function": tool})
        if not new_tools:
            new_tools = None
        request_data = {
            "model": payload.get("model"),
            "top_p": top_p,
            "temperature": temperature,
            "messages": system_message.content,
        }
        if payload.get("enable_thinking") is not None:
            request_data.update({"enable_thinking": payload.get("enable_thinking")})
        if new_tools is not None:
            request_data.update({"tools": new_tools})
        return request_data, headers

    def _chat(
        self,
        messages: List[BaseMessage],
        tools: List[Tool] = None,
        **kwargs: Any,
    ) -> LanguageModelOutput:
        """agentBuilder chat function"""
        resquest_data, headers = self._request_params(messages, tools)
        resquest_data.update({"stream": False})
        res = requests.post(
            url=self.api_base,
            json=resquest_data,
            headers=headers,
            verify=ModelUtil.parse_ssl_verify(),
            stream=False,
            timeout=60,
        )
        if res.status_code == 200:
            res_json = res.json()
            tools_flag = res_json.get("choices", [])[0].get("finish_reason", "stop")
            usage_metadata = UsageMetadata(
                code=0,
                errmsg="成功",
                task_id=res_json.get("id", self.model_name),
                model_name=res_json.get("model", self.model_name),
                finish_reason="stop",
            )
            (
                usage_metadata.input_tokens,
                usage_metadata.output_tokens,
                usage_metadata.total_tokens,
            ) = self._extract_tokens_from_response(res_json)
            res_content = res_json.get("choices")[0].get("message").get("content")
            reasoning_content = (
                res_json.get("choices")[0].get("message").get("reasoning_content", "")
                or ""
            )
            if tools_flag == "tool_calls":
                name = (
                    res_json.get("choices")[0]
                    .get("message")
                    .get("tool_calls")
                    .get("function")
                    .get("name")
                )
                check_and_trans_result = ModelUtil.check_and_trans2json(
                    res_json.get("choices")[0]
                    .get("message")
                    .get("tool_calls")
                    .get("function")
                    .get("arguments")
                )
                if name and check_and_trans_result[0]:
                    tools_call = ToolCall(name=name, args=check_and_trans_result[1])
                    usage_metadata.finish_reason = "function_call"
                else:
                    res_content = (
                        res_json.get("choices")[0]
                        .get("message")
                        .get("tool_calls")
                        .get("function")
                    )
                    tools_call = {}

                return AIMessage(
                    content=res_content,
                    usage_metadata=usage_metadata,
                    reasoning_content=reasoning_content,
                    tool_calls=tools_call,
                )
            return AIMessage(
                content=res_content,
                usage_metadata=usage_metadata,
                reasoning_content=reasoning_content,
                tool_calls={},
            )

        raise JiuWenBaseException(
            StatusCode.LLM_REQUEST_ERROR.code,
            StatusCode.LLM_REQUEST_ERROR.errmsg.format(
                error_msg=res.json().get("message", "please check model service.")
            ),
        )

    def _stream(
        self, messages: List[BaseMessage], tools: List[Tool] = None, **kwargs: Any
    ) -> Iterator[LanguageModelOutput]:
        """agentBuilder stream function."""
        resquest_data, headers = self._request_params(messages, tools)
        resquest_data.update({"stream": True})
        resquest_data.update({"stream_options": {"include_usage": True}})
        usage_metadata = UsageMetadata(
            prompt="null",
            requests_start_time=datetime.datetime.now(tz=BJ_TZ).isoformat(),
        )
        res = requests.post(
            url=self.api_base,
            json=resquest_data,
            headers=headers,
            verify=ModelUtil.parse_ssl_verify(),
            stream=True,
            timeout=120,
        )
        total_message = ""
        total_reason_message = ""
        # tool_calls 累积变量（流式响应中 tool_calls 分多个 chunk 返回）
        # 按 index 分组累积，支持并行 function calling
        tool_calls_acc = {}  # {index: {"id": str, "name": str, "arguments": str}}
        finish_reason = "stop"
        if res.status_code == 200:
            for i in res.iter_lines():
                if not usage_metadata.first_token_time:
                    usage_metadata.first_token_time = datetime.datetime.now(
                        tz=BJ_TZ
                    ).isoformat()
                if (
                    str(i.decode(UTF_STR)).startswith(DataField.data_str)
                    and len(i.decode(UTF_STR)) > 20
                ):
                    try:
                        res_content_json_content = json.loads(
                            i.decode(UTF_STR).removeprefix(DataField.data_str)
                        )
                    except json.decoder.JSONDecodeError as error:
                        raise JiuWenBaseException(
                            error_code=StatusCode.LLM_RESPONSE_SCHEMA_ERROR.code,
                            message=StatusCode.LLM_RESPONSE_SCHEMA_ERROR.errmsg.format(
                                error_msg="qwen model stream result invalid json formatting."
                            ),
                        ) from error
                    if (
                        DataField.choices_str in res_content_json_content
                        and res_content_json_content.get(DataField.choices_str)
                    ):
                        choice = res_content_json_content.get(DataField.choices_str)[0]
                        delta = choice.get("delta", {})

                        # 累积文本内容
                        total_message += delta.get("content", "") or ""
                        total_reason_message += delta.get("reasoning_content", "") or ""

                        # 累积 tool_calls（与 _chat() 对齐，按 index 分组）
                        delta_tool_calls = choice.get("delta", {}).get("tool_calls")
                        if delta_tool_calls:
                            if isinstance(delta_tool_calls, list):
                                for tc in delta_tool_calls:
                                    idx = tc.get("index", 0)
                                    if idx not in tool_calls_acc:
                                        tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                                    func = tc.get("function", {})
                                    if tc.get("id"):
                                        tool_calls_acc[idx]["id"] = tc["id"]
                                    func = tc.get("function", {})
                                    if func.get("name"):
                                        tool_calls_acc[idx]["name"] = func["name"]
                                    if func.get("arguments"):
                                        tool_calls_acc[idx]["arguments"] += func["arguments"]
                            elif isinstance(delta_tool_calls, dict):
                                idx = delta_tool_calls.get("index", 0)
                                if idx not in tool_calls_acc:
                                    tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                                func = delta_tool_calls.get("function", {})
                                if delta_tool_calls.get("id"):
                                    tool_calls_acc[idx]["id"] = delta_tool_calls["id"]
                                func = delta_tool_calls.get("function", {})
                                if func.get("name"):
                                    tool_calls_acc[idx]["name"] = func["name"]
                                if func.get("arguments"):
                                    tool_calls_acc[idx]["arguments"] += func["arguments"]

                        # 读取 finish_reason
                        chunk_finish = choice.get("finish_reason")
                        if chunk_finish:
                            finish_reason = chunk_finish

                    usage_metadata.code = 0
                    usage_metadata.errmsg = "成功"
                    usage_metadata.task_id = res_content_json_content.get("id")
                    usage_metadata.model_name = self.model_name
                    usage_metadata.finish_reason = "null"
                    usage_metadata.total_latency = 0
                    # 处理token消耗，流式输出一般在最后一个消息的时候返回消耗信息，或者不断叠加返回
                    if res_content_json_content.get("usage"):
                        (
                            usage_metadata.input_tokens,
                            usage_metadata.output_tokens,
                            usage_metadata.total_tokens,
                        ) = self._extract_tokens_from_response(res_content_json_content)
                    if (
                        DataField.choices_str in res_content_json_content
                        and res_content_json_content.get(DataField.choices_str)
                    ):
                        content = (
                            res_content_json_content.get(DataField.choices_str)[0]
                            .get("delta", {})
                            .get("content", "")
                            or ""
                        )
                        reasoning_content = (
                            res_content_json_content.get(DataField.choices_str)[0]
                            .get("delta", {})
                            .get("reasoning_content", "")
                            or ""
                        )
                        yield AIMessage(
                            reasoning_content=reasoning_content,
                            content=content,
                            usage_metadata=usage_metadata,
                            tool_calls={},
                        )
                    else:
                        yield AIMessage(
                            content="", usage_metadata=usage_metadata, tool_calls={}
                        )

            # 流结束后：如果有 tool_calls，构造 ToolCall 对象（与 _chat() 逻辑一致）
            if finish_reason == "tool_calls" and tool_calls_acc:
                tools_call_list = []
                for idx in sorted(tool_calls_acc.keys()):
                    acc = tool_calls_acc[idx]
                    if not acc["name"]:
                        continue
                    check_and_trans_result = ModelUtil.check_and_trans2json(
                        acc["arguments"]
                    )
                    if check_and_trans_result[0]:
                        tc = ToolCall(
                            name=acc["name"], args=check_and_trans_result[1]
                        )
                        if acc["id"]:
                            tc.id = acc["id"]
                        tools_call_list.append(tc)

                if tools_call_list:
                    usage_metadata.finish_reason = "function_call"
                    # 单个 tool_call 直接返回对象，多个返回列表（下游已支持）
                    tool_calls_result = tools_call_list[0] if len(tools_call_list) == 1 else tools_call_list
                    yield AIMessage(
                        content=total_message,
                        usage_metadata=usage_metadata,
                        tool_calls=tool_calls_result,
                    )
                else:
                    usage_metadata.finish_reason = "stop"
                    yield AIMessage(
                        content=total_message,
                        usage_metadata=usage_metadata,
                        tool_calls={},
                    )
            else:
                usage_metadata.finish_reason = "stop"
                yield AIMessage(
                    content=total_message,
                    usage_metadata=usage_metadata,
                    tool_calls={},
                )

        else:
            raise JiuWenBaseException(
                StatusCode.LLM_REQUEST_ERROR.code,
                StatusCode.LLM_REQUEST_ERROR.errmsg.format(
                    error_msg=res.json().get("message", "please check model service.")
                ),
            )
