#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

"""
This module is used to generate replies for the dialog system.
"""

import asyncio
import os
import re
import time
from typing import Any, Generator, List, AsyncGenerator

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import LanguageModelInput
from jiuwen.common.llm_service.messages import BaseMessage
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.log.base import performance_logger
from jiuwen.context.history import ConversationHistory
from jiuwen.context.memory_engine.config.memory_ir_config import (
    USER_PROFILE_KEY,
    ENABLE_KEY,
)
from model_service.env_resolver import friendly_message
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.callbacks.span import Span
from jiuwen.orchestration.flow.components.util import (
    get_data_of_streaming_with_metadata,
    process_on_invoke_info,
    get_callback_data,
    filter_enable_history,
    format_pydantic_validation_error_message,
)
from jiuwen.orchestration.flow.constant import (
    WORKFLOW_CHAT_HISTORY,
    USER_FIELDS,
    MEMORY_MESSAGE,
)
from jiuwen.orchestration.flow.enum import (
    StreamDataMsg,
    ChatHistoryRole,
    WorkflowLLMResponseType,
)
from jiuwen.orchestration.flow.model.workflow_data_class import WorkflowStreamingData
from jiuwen.orchestration.flow.stream.base import StreamData, StreamCode
from jiuwen.prompt import Prompt, Template, TemplateManager
from jiuwen.prompt.agent.common.utils import format_prompt, format_response
from pydantic import BaseModel, StrictStr, Field, ValidationError

CHAT_HISTORY_MAX_TURN = 3
_ROLE = "role"
_CONTENT = "content"
ROLE_MAP = {"user": "用户", "assistant": "助手", "system": "系统"}
_SPAN = "span"
_WORKFLOW_DATA = "workflow_data"
_ID = "id"
_TYPE = "type"
_INSTRUCTION_NAME = "instruction_name"
_TEMPLATE_NAME = "template_name"

LOG_VERBOSE_MODE = os.getenv("LOG_VERBOSE", "false").lower() == "true"


class LLMChainModelConfig(BaseModel):
    model_name: StrictStr = Field(alias="modelName")
    model_type: StrictStr = Field(alias="modelType")
    hyper_parameters: dict = Field(alias="hyperParameters", default={})
    extension: dict = Field(default={})


class LLMChainConfig(BaseModel):
    """
    大模型组件 配置校验
    """

    model: LLMChainModelConfig
    deploy_mode: StrictStr = Field(alias="deployMode")
    template_content: list = Field(alias="templateContent")
    response_format: dict = Field(alias="responseFormat")
    enable_history: bool = Field(alias="enableHistory", default=True)
    user_fields: dict = Field(alias="userFields")


response_format_to_prompt_map = {
    WorkflowLLMResponseType.JSON.value: {
        _INSTRUCTION_NAME: "jsonInstruction",
        _TEMPLATE_NAME: "llm_json_formatting",
    },
    WorkflowLLMResponseType.MARKDOWN.value: {
        _INSTRUCTION_NAME: "markdownInstruction",
        _TEMPLATE_NAME: "llm_markdown_formatting",
    },
}


class LLMChain(Invokable):
    """
    LLMChain class is used to generate conversation replies.
    It is useful in scenarios where natural language generation is required.
    """

    def __init__(self):
        super().__init__()
        self._conf = None
        self._runtime_context = None
        self.llm = None
        self.metadata = None
        self.mem_conf = None

    @staticmethod
    def _get_prompt_instance_by_template(template) -> Prompt:
        return Prompt(template=Template(name="default", content=template))

    def init(self, conf: dict, **kwargs):
        runtime_context = kwargs.get("runtime_context")
        metadata = kwargs.get("metadata")
        self._conf = conf
        self._runtime_context = runtime_context
        self.llm = self._get_llm_instance()
        self._validate_config()
        self.metadata = metadata
        self.mem_conf = conf.get("memory", {})

    def invoke(self, inputs: dict[str, Any], **kwargs):
        ...

    async def ainvoke(self, inputs: dict[str, Any], **kwargs):
        """LLM组件非流式调用接口"""
        inputs = inputs.get(USER_FIELDS)
        self._process_inputs(inputs)
        language_model_inputs = await self._get_model_input(inputs=inputs)
        llm_output = self.llm.invoke(language_model_inputs)
        formatted_res = format_response(
            llm_output.content,
            self._get_response_format().get("type"),
            outputs_config=self._get_outputs_conf(),
            outputs_config_list=self._get_outputs_list_from_conf(),
        )
        final_output = {USER_FIELDS: formatted_res}
        # 增加token消耗信息，非流式场景不需要firstTokenTime
        self.__append_usage_metadata(llm_output, final_output)
        return final_output

    async def stream(self, inputs: dict[str, Any], **kwargs):
        """LLM组件流式蹦字调用接口"""
        if self._get_response_format().get("type") == "json":
            inputs = inputs.get(USER_FIELDS)
            self._process_inputs(inputs)
            language_model_inputs = await self._get_model_input(inputs=inputs)
            llm_output = self.llm.invoke(language_model_inputs)
            final_res = format_response(
                llm_output.content,
                self._get_response_format().get("type"),
                outputs_config=self._get_outputs_conf(),
                outputs_config_list=self._get_outputs_list_from_conf(),
            )
            final_output = {USER_FIELDS: final_res}
            # 增加token消耗信息，非流式场景不需要firstTokenTime
            self.__append_usage_metadata(llm_output, final_output)
        else:
            inputs = inputs.get(USER_FIELDS)
            self._process_inputs(inputs)
            language_model_inputs = await self._get_model_input(inputs=inputs)
            result = self.llm.stream(language_model_inputs)
            llm_inputs = dict(language_model_inputs)
            generator_res = self._get_streaming_generator(
                result, kwargs.get(_SPAN), llm_inputs
            )
            output_definition_list = self._get_outputs_list_from_conf()
            final_res = {
                output.get("id"): generator_res for output in output_definition_list
            }
            final_output = {USER_FIELDS: final_res}
        return final_output

    async def astream(self, inputs: dict[str, Any], **kwargs):
        """LLM async stream - 返回包含异步迭代器的结果"""
        final_output = None

        if self._get_response_format().get("type") == "json":
            inputs = inputs.get(USER_FIELDS)
            self._process_inputs(inputs)
            language_model_inputs = await self._get_model_input(inputs=inputs)
            user_profile = self.mem_conf.get(USER_PROFILE_KEY)
            if isinstance(user_profile, dict) and user_profile.get(ENABLE_KEY, False):
                memory_msg = self._runtime_context.get(MEMORY_MESSAGE)
                if isinstance(memory_msg, BaseMessage):
                    language_model_inputs["messages"].append(memory_msg)
            performance_logger.info(
                f"LLM CHAIN inputs: {inputs}", simple_log="LLM CHAIN inputs: inputs"
            )
            llm_output = await self.llm.ainvoke(language_model_inputs)

            final_output = await self._get_json_type_output(
                final_output, llm_output, **kwargs
            )

            # 增加token消耗信息，非流式场景不需要firstTokenTime
            self.__append_usage_metadata(llm_output, final_output)
        else:
            inputs = inputs.get(USER_FIELDS)
            self._process_inputs(inputs)
            language_model_inputs = await self._get_model_input(inputs=inputs)
            user_profile = self.mem_conf.get(USER_PROFILE_KEY)
            if isinstance(user_profile, dict) and user_profile.get(ENABLE_KEY, False):
                memory_msg = self._runtime_context.get(MEMORY_MESSAGE)
                if isinstance(memory_msg, BaseMessage):
                    language_model_inputs["messages"].append(memory_msg)
            performance_logger.info(
                f"LLM CHAIN inputs: {inputs}.", simple_log="LLM CHAIN inputs: inputs."
            )
            result = self.llm.astream(language_model_inputs)
            llm_inputs = dict(language_model_inputs)
            final_output = await self._get_markdown_text_output(
                final_output, kwargs, llm_inputs, result
            )
        return final_output

    async def _get_markdown_text_output(self, final_output, kwargs, llm_inputs, result):
        # 检查是否开启了思考模式
        if self._is_thinking_enabled():
            # 预消费流：获取完整 reasoning_content + rawOutput generator
            raw_output_gen, reasoning_content = await self._process_thinking_stream(
                result, llm_inputs, **kwargs
            )
            output_definition_list = self._get_outputs_list_from_conf()
            final_res = {}
            if output_definition_list:
                for output in output_definition_list:
                    if output.get("id") == "reasoning_content":
                        final_res[output.get("id")] = reasoning_content
                    else:
                        final_res[output.get("id")] = raw_output_gen
            final_output = {USER_FIELDS: final_res}
        else:
            # 原有逻辑：单 generator 输出
            output_definition_list = self._get_outputs_list_from_conf()

            # final_stream_data 现在是异步生成器
            final_stream_data = self._process_streaming_data_generator(
                result, kwargs.get(_SPAN), llm_inputs
            )

            # 根据输出配置包装数据
            if output_definition_list:
                for output in output_definition_list:
                    final_res = {output.get("id"): final_stream_data}
                    final_output = {USER_FIELDS: final_res}
            else:
                final_output = {USER_FIELDS: final_stream_data}
        return final_output

    async def _get_json_type_output(self, final_output, llm_output, **kwargs):
        stream_callback = kwargs.get("stream_callback")
        span: Span = kwargs.get("span")
        stream_related_info = WorkflowStreamingData(
            stream_callback=stream_callback, execution_id=span.trace_id
        )

        if self._is_thinking_enabled():
            await self._output_reasoning_content(
                reasoning_content=llm_output.reasoning_content,
                stream_related_info=stream_related_info,
                execution_id=span.trace_id,
            )
            content = format_response(
                llm_output.content,
                self._get_response_format().get("type"),
                outputs_config=self._get_outputs_conf(),
                outputs_config_list=self._get_outputs_list_from_conf(),
            )
            output_definition_list = self._get_outputs_list_from_conf()
            final_res = {}

            if output_definition_list:
                for output in output_definition_list:
                    if output.get("id") == "reasoning_content":
                        final_res["reasoning_content"] = llm_output.reasoning_content
                    else:
                        final_res[output.get("id")] = content
            final_output = {USER_FIELDS: final_res}
        else:
            final_res = format_response(
                llm_output.content,
                self._get_response_format().get("type"),
                outputs_config=self._get_outputs_conf(),
                outputs_config_list=self._get_outputs_list_from_conf(),
            )
            final_output = {USER_FIELDS: final_res}
        return final_output

    async def _process_thinking_stream(
        self, model_result, llm_inputs: dict, **kwargs
    ) -> tuple[AsyncGenerator, str]:
        """
        预消费模型流，分离 content 和 reasoning_content

        工作流程：
        1. 完整遍历模型返回流
        2. 收集所有 content chunks 到列表
        3. 累积所有 reasoning_content 到字符串
        4. 基于缓存的 content_chunks 构造异步迭代器

        Returns:
            tuple: (rawOutput generator, reasoning_content 完整字符串)
        """

        span: Span = kwargs.get("span")
        execution_id = span.trace_id if span else ""

        # 缓存数据
        content_chunks: list[str] = []
        reasoning_content: str = ""

        # 状态统计
        state = {
            "first_token_time": "",
            "requests_start_time": "",
            "llm_tokens_statistics": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
            "start_time": time.perf_counter(),
            "is_first_token": True,
            "error": None,
        }

        # ========== 阶段1: 完整消费原始流 ==========
        try:
            if asyncio.iscoroutine(model_result):
                result_iter = await model_result
            else:
                result_iter = model_result

            reasoning_content = await self._consume_llm_stream(
                content_chunks, reasoning_content, result_iter, state, **kwargs
            )
            performance_logger.info(
                f"total_token<llm>|{round((time.perf_counter() - state['start_time']) * 1000)}"
            )
            # 处理回调信息
            final_content = "".join(content_chunks)
            await process_on_invoke_info(
                component_metadata=get_callback_data(invokable_metadata=self.metadata),
                runtime_context=self._runtime_context,
                data={
                    "llm_info": {
                        "llm_inputs": llm_inputs,
                        "llm_outputs": final_content,
                        "reasoning_content": reasoning_content,
                    }
                },
                span=span,
            )

        except Exception as e:
            state["error"] = e

        # ========== 阶段2: 基于缓存构造 rawOutput generator ==========
        async def raw_output_generator():
            """基于缓存的 content_chunks 重放生成流式数据"""
            index = 0
            accumulated_content = ""

            # 如果有错误，直接输出错误
            if state["error"]:
                yield StreamData(
                    code=StreamCode.ERROR.value,
                    msg=StreamDataMsg.FAIL.value,
                    data=get_data_of_streaming_with_metadata(
                        answer=friendly_message(state["error"]), metadata=self.metadata
                    ),
                    execution_id=execution_id,
                )
                return

            # 重放缓存的 content chunks
            for chunk in content_chunks:
                accumulated_content += chunk
                yield StreamData(
                    code=StreamCode.PARTIAL_CONTENT.value,
                    msg=StreamDataMsg.SUCCESS.value,
                    data=get_data_of_streaming_with_metadata(
                        answer=chunk, metadata=self.metadata
                    ),
                    execution_id=execution_id,
                    index=index,
                )
                index += 1

            # FINISH 事件
            formatted_res = format_response(
                accumulated_content,
                self._get_response_format().get("type"),
                outputs_config=self._get_outputs_conf(),
                outputs_config_list=self._get_outputs_list_from_conf(),
            )
            yield StreamData(
                code=StreamCode.FINISH.value,
                msg=StreamDataMsg.FINISH.value,
                data=get_data_of_streaming_with_metadata(
                    answer={
                        USER_FIELDS: formatted_res,
                        "firstTokenTime": state["first_token_time"],
                        "requestStartTime": state["requests_start_time"],
                        "input_tokens": state["llm_tokens_statistics"]["input_tokens"],
                        "output_tokens": state["llm_tokens_statistics"][
                            "output_tokens"
                        ],
                        "total_tokens": state["llm_tokens_statistics"]["total_tokens"],
                    },
                    metadata=self.metadata,
                ),
                execution_id=execution_id,
            )

        return raw_output_generator(), reasoning_content

    async def _consume_llm_stream(
        self, content_chunks, reasoning_content, result_iter, state, **kwargs
    ):
        span: Span = kwargs.get("span")
        execution_id = span.trace_id if span else ""
        stream_callback = kwargs.get("stream_callback")
        stream_related_info = WorkflowStreamingData(
            stream_callback=stream_callback, execution_id=execution_id
        )
        async for item in result_iter:
            # 更新统计信息
            state["first_token_time"] = item.usage_metadata.first_token_time
            state["requests_start_time"] = item.usage_metadata.requests_start_time
            state["llm_tokens_statistics"]["input_tokens"] = (
                item.usage_metadata.input_tokens
            )
            state["llm_tokens_statistics"]["output_tokens"] = (
                item.usage_metadata.output_tokens
            )
            state["llm_tokens_statistics"]["total_tokens"] = (
                item.usage_metadata.total_tokens
            )

            if state["is_first_token"]:
                performance_logger.info(
                    f"first_token<llm>|{round((time.perf_counter() - state['start_time']) * 1000)}"
                )
                state["is_first_token"] = False

            # 错误处理
            if item.usage_metadata.code != 0:
                state["error"] = JiuWenBaseException(message=item.usage_metadata.errmsg)
                break

            # 收集 reasoning_content（累积为完整字符串）
            if hasattr(item, "reasoning_content") and item.reasoning_content:
                reasoning_content += item.reasoning_content
                reason_item = StreamData(
                    code=StreamCode.PARTIAL_CONTENT.value,
                    msg=StreamDataMsg.SUCCESS.value,
                    data=get_data_of_streaming_with_metadata(
                        answer="", metadata=self.metadata, think=item.reasoning_content
                    ),
                    execution_id=execution_id,
                )
                await stream_related_info.stream_callback.on_recv(reason_item)

            # 收集 content（缓存到列表）
            if item.content and item.usage_metadata.finish_reason == "null":
                content_chunks.append(item.content)

            if (
                item.content
                and item.usage_metadata.finish_reason == "stop"
                and not content_chunks
            ):
                content_chunks.append(item.content)
        return reasoning_content

    async def _output_reasoning_content(
        self, reasoning_content, stream_related_info, execution_id: str = ""
    ):
        reason = StreamData(
            code=StreamCode.PARTIAL_CONTENT.value,
            msg=StreamDataMsg.SUCCESS.value,
            data=get_data_of_streaming_with_metadata(
                answer="", metadata=self.metadata, think=reasoning_content
            ),
            execution_id=execution_id,
        )
        await stream_related_info.stream_callback.on_recv(reason)

    def _is_thinking_enabled(self) -> bool:
        """检查是否开启了思考模式"""
        thinking_config = (
            self._conf.get("model", {}).get("hyperParameters", {}).get("thinking", {})
        )
        return thinking_config.get("type") == "enabled"

    def __append_usage_metadata(self, llm_output, final_output: dict):
        """根据llm返回，增加额外usage信息，对于非流式响应主要是token消耗"""
        if (
            llm_output
            and hasattr(llm_output, "usage_metadata")
            and llm_output.usage_metadata
        ):
            final_output.update(llm_output.usage_metadata)

    async def __format_result(
        self,
        final_output,
        llm_inputs,
        span,
        first_token_time,
        requests_start_time,
        input_tokens,
        output_tokens,
        total_tokens,
        model_stats,
        execution_id,
    ):
        # 格式化最终结果
        formatted_res = format_response(
            final_output,
            self._get_response_format().get("type"),
            outputs_config=self._get_outputs_conf(),
            outputs_config_list=self._get_outputs_list_from_conf(),
        )

        # 处理回调信息
        await process_on_invoke_info(
            component_metadata=get_callback_data(invokable_metadata=self.metadata),
            runtime_context=self._runtime_context,
            data={"llm_info": {"llm_inputs": llm_inputs, "llm_outputs": final_output}},
            span=span,
        )

        # 构造并返回最终结果
        final_stream_data = StreamData(
            code=StreamCode.FINISH.value,
            msg=StreamDataMsg.FINISH.value,
            data=get_data_of_streaming_with_metadata(
                answer={
                    USER_FIELDS: formatted_res,
                    "firstTokenTime": first_token_time,
                    "requestStartTime": requests_start_time,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "model_stats": model_stats,
                },
                metadata=self.metadata,
            ),
            execution_id=execution_id,
        )
        return final_stream_data

    def _generate_error_stream_data(self, item, execution_id):
        return StreamData(
            code=StreamCode.ERROR.value,
            msg=StreamDataMsg.FAIL.value,
            data=get_data_of_streaming_with_metadata(
                answer=item.usage_metadata.errmsg, metadata=self.metadata
            ),
            execution_id=execution_id,
        )

    def _generate_partial_stream_data(
        self, item, execution_id, partial_content_index=0
    ):
        if hasattr(item, "reasoning_content") and item.reasoning_content:
            return StreamData(
                code=StreamCode.PARTIAL_CONTENT.value,
                msg=StreamDataMsg.SUCCESS.value,
                data=get_data_of_streaming_with_metadata(
                    answer=item.content,
                    metadata=self.metadata,
                    think=item.reasoning_content,
                ),
                execution_id=execution_id,
                index=partial_content_index,
            )

        return StreamData(
            code=StreamCode.PARTIAL_CONTENT.value,
            msg=StreamDataMsg.SUCCESS.value,
            data=get_data_of_streaming_with_metadata(
                answer=item.content, metadata=self.metadata
            ),
            execution_id=execution_id,
            index=partial_content_index,
        )

    async def _process_streaming_data_generator(self, result, span: Span, llm_inputs):
        """处理流式数据 - 返回异步生成器"""
        final_output = ""
        execution_id = span.trace_id if span else ""
        partial_content_index = 0

        # 状态统计
        state = {
            "first_token_time": "",
            "requests_start_time": "",
            "llm_tokens_statistics": {},
            "model_stats": {},
            "start_time": time.perf_counter(),
            "is_first_token": True,
        }

        try:
            if asyncio.iscoroutine(result):
                result = await result
                for item in result:
                    state["first_token_time"] = item.usage_metadata.first_token_time
                    state["requests_start_time"] = (
                        item.usage_metadata.requests_start_time
                    )
                    # 设置token消耗信息
                    state["llm_tokens_statistics"]["input_tokens"] = (
                        item.usage_metadata.input_tokens
                    )
                    state["llm_tokens_statistics"]["output_tokens"] = (
                        item.usage_metadata.output_tokens
                    )
                    state["llm_tokens_statistics"]["total_tokens"] = (
                        item.usage_metadata.total_tokens
                    )

                    if state["is_first_token"]:
                        performance_logger.info(
                            f"first_token<llm>|{round((time.perf_counter() - state['start_time']) * 1000)}"
                        )
                        state["is_first_token"] = False

                    if item.usage_metadata.code != 0:
                        yield self._generate_error_stream_data(item, execution_id)
                        continue

                    if item.usage_metadata.finish_reason == "null":
                        partial_stream_data = self._generate_partial_stream_data(
                            item, execution_id, partial_content_index
                        )
                        partial_content_index += 1
                        final_output = final_output + str(item.content)
                        yield partial_stream_data

                    if item.usage_metadata.finish_reason == "stop" and not final_output:
                        stop_stream_data = self._generate_partial_stream_data(
                            item, execution_id
                        )
                        final_output = str(item.content)
                        yield stop_stream_data
            else:
                # 异步迭代器，使用 async for
                async for item in result:
                    state["first_token_time"] = item.usage_metadata.first_token_time
                    state["requests_start_time"] = (
                        item.usage_metadata.requests_start_time
                    )
                    # 设置token消耗信息
                    state["llm_tokens_statistics"]["input_tokens"] = (
                        item.usage_metadata.input_tokens
                    )
                    state["llm_tokens_statistics"]["output_tokens"] = (
                        item.usage_metadata.output_tokens
                    )
                    state["llm_tokens_statistics"]["total_tokens"] = (
                        item.usage_metadata.total_tokens
                    )
                    state["model_stats"] = item.usage_metadata.model_stats

                    if state["is_first_token"]:
                        performance_logger.info(
                            f"first_token<llm>|{round((time.perf_counter() - state['start_time']) * 1000)}"
                        )
                        state["is_first_token"] = False

                    if item.usage_metadata.code != 0:
                        yield self._generate_error_stream_data(item, execution_id)
                        continue

                    if item.usage_metadata.finish_reason == "null":
                        partial_stream_data = self._generate_partial_stream_data(
                            item, execution_id, partial_content_index
                        )
                        partial_content_index += 1
                        final_output = final_output + str(item.content)
                        yield partial_stream_data

                    if item.usage_metadata.finish_reason == "stop" and not final_output:
                        stop_stream_data = self._generate_partial_stream_data(
                            item, execution_id
                        )
                        final_output = str(item.content)
                        yield stop_stream_data

            performance_logger.info(
                f"total_token<llm>|{round((time.perf_counter() - state['start_time']) * 1000)}"
            )

        except JiuWenBaseException as e:
            yield StreamData(
                code=StreamCode.ERROR.value,
                msg=StreamDataMsg.FAIL.value,
                data=get_data_of_streaming_with_metadata(
                    answer=e.message, metadata=self.metadata
                ),
                execution_id=execution_id,
            )
            return

        yield await self.__format_result(
            final_output,
            llm_inputs,
            span,
            state["first_token_time"],
            state["requests_start_time"],
            state["llm_tokens_statistics"]["input_tokens"],
            state["llm_tokens_statistics"]["output_tokens"],
            state["llm_tokens_statistics"]["total_tokens"],
            state["model_stats"],
            execution_id,
        )

    def _get_streaming_generator_for_json(self, output, execution_id: str):
        yield StreamData(
            code=StreamCode.PARTIAL_CONTENT.value,
            msg=StreamDataMsg.SUCCESS.value,
            execution_id=execution_id,
            data=get_data_of_streaming_with_metadata(
                answer=output, metadata=self.metadata
            ),
        )
        yield StreamData(
            code=StreamCode.FINISH.value,
            msg=StreamDataMsg.FINISH.value,
            execution_id=execution_id,
            data=get_data_of_streaming_with_metadata(
                answer=output, metadata=self.metadata
            ),
        )

    def _get_streaming_generator(self, result: Generator, span: Span, llm_inputs):
        final_output = ""
        execution_id = span.trace_id if span else ""
        partial_content_index = 0
        first_token_time = ""
        requests_start_time = ""
        llm_tokens_statistics = {}
        start_time = time.perf_counter()
        is_first_token = True
        try:
            for item in result:
                if is_first_token:
                    first_token_time = item.usage_metadata.first_token_time
                    requests_start_time = item.usage_metadata.requests_start_time
                    performance_logger.info(
                        f"first_token<llm>|{round((time.perf_counter() - start_time) * 1000)}"
                    )
                    is_first_token = False
                # 设置token消耗信息
                llm_tokens_statistics["input_tokens"] = item.usage_metadata.input_tokens
                llm_tokens_statistics["output_tokens"] = (
                    item.usage_metadata.output_tokens
                )
                llm_tokens_statistics["total_tokens"] = item.usage_metadata.total_tokens
                if item.usage_metadata.code != 0:
                    yield StreamData(
                        code=StreamCode.ERROR.value,
                        msg=StreamDataMsg.FAIL.value,
                        data=get_data_of_streaming_with_metadata(
                            answer=item.usage_metadata.errmsg, metadata=self.metadata
                        ),
                        execution_id=execution_id,
                    )
                if item.usage_metadata.finish_reason == "null":
                    yield StreamData(
                        code=StreamCode.PARTIAL_CONTENT.value,
                        msg=StreamDataMsg.SUCCESS.value,
                        data=get_data_of_streaming_with_metadata(
                            answer=item.content, metadata=self.metadata
                        ),
                        execution_id=execution_id,
                        index=partial_content_index,
                    )
                    partial_content_index += 1
                    final_output = final_output + str(item.content)
                if item.usage_metadata.finish_reason == "stop" and not final_output:
                    yield StreamData(
                        code=StreamCode.PARTIAL_CONTENT.value,
                        msg=StreamDataMsg.SUCCESS.value,
                        data=get_data_of_streaming_with_metadata(
                            answer=item.content, metadata=self.metadata
                        ),
                        execution_id=execution_id,
                    )
                    final_output = str(item.content)
            performance_logger.info(
                f"total_token<llm>|{round((time.perf_counter() - start_time) * 1000)}"
            )
        except JiuWenBaseException as e:
            raise JiuWenBaseException(
                error_code=e.error_code,
                message=str(type(e).__name__),
                node_id=self.metadata.node_id,
                node_name=self.metadata.node_name,
                node_type=self.metadata.node_type,
            ) from e
        formatted_res = format_response(
            final_output,
            self._get_response_format().get("type"),
            outputs_config=self._get_outputs_conf(),
            outputs_config_list=self._get_outputs_list_from_conf(),
        )
        process_on_invoke_info(
            component_metadata=get_callback_data(invokable_metadata=self.metadata),
            runtime_context=self._runtime_context,
            data={"llm_info": {"llm_inputs": llm_inputs, "llm_outputs": final_output}},
            span=span,
        )
        yield StreamData(
            code=StreamCode.FINISH.value,
            msg=StreamDataMsg.FINISH.value,
            data=get_data_of_streaming_with_metadata(
                answer={
                    USER_FIELDS: formatted_res,
                    "firstTokenTime": first_token_time,
                    "requestStartTime": requests_start_time,
                    "input_tokens": llm_tokens_statistics["input_tokens"],
                    "output_tokens": llm_tokens_statistics["output_tokens"],
                    "total_tokens": llm_tokens_statistics["total_tokens"],
                },
                metadata=self.metadata,
            ),
            execution_id=execution_id,
        )

    async def _get_model_input(self, inputs: dict) -> LanguageModelInput:
        """
        获取模型输入
        """
        # 将模型IR配置中的templateContent占位符替换为真实输入
        prompt_instance = self._get_prompt_instance_by_template(
            self._get_template_content()
        )
        try:
            self._validate_prompt_instance(prompt_instance)
            user_prompt = await prompt_instance.ainvoke(inputs)
        except JiuWenBaseException:
            raise
        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_LLM_TEMPLATE_ASSEMBLE_ERROR.code,
                message=StatusCode.WORKFLOW_LLM_TEMPLATE_ASSEMBLE_ERROR.errmsg,
            ) from e

        # 根据IR中定义的模型输出格式获取对话历史列表
        final_prompt = self._get_history(user_prompt)
        return LanguageModelInput(
            messages=ModelUtil.switch_message(final_prompt),
            tools=inputs.get("tools", []),
        )

    def _validate_prompt_instance(self, prompt_instance: Prompt) -> None:
        """
        在 invoke 之前校验模板源，拦截危险占位符（如 query.__class__、表达式等）。
        只依赖模板字符串，不依赖运行时 inputs。
        """
        template = getattr(prompt_instance, "template", None)
        if template is None:
            return
        content = getattr(template, "content", None)
        texts: list[str] = []
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and isinstance(item.get(_CONTENT), str):
                    texts.append(item[_CONTENT])
                elif isinstance(item, str):
                    texts.append(item)
        # 查找 {{...}} 中的内容
        placeholder_find_pattern = re.compile(r"\{\{([^{}]*)\}\}")
        # 校验：仅允许「标识符.标识符...」，禁止 __、空格、括号等
        placeholder_safe_pattern = re.compile(
            r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$"
        )

        for text in texts:
            for match in placeholder_find_pattern.finditer(text):
                placeholder = match.group(1).strip()

                if (
                    not placeholder
                    or "__" in placeholder
                    or not placeholder_safe_pattern.fullmatch(placeholder)
                ):
                    raise ValueError(
                        f"Invalid or dangerous placeholder: '{placeholder}'"
                    )

    def _get_history(self, user_prompt: str):
        workflow_chat_history: ConversationHistory = self._runtime_context.get(
            WORKFLOW_CHAT_HISTORY, None
        )
        if workflow_chat_history:
            chat_history = workflow_chat_history.get_conversation_history()
        else:
            chat_history = []
        # 对话历史一定会包含最新用户问题，所以不会为空
        chat_history = filter_enable_history(chat_history)
        origin_history = [chat_history[-1]]
        if self._get_enable_history():
            origin_history = chat_history
        origin_history[-1].update({_CONTENT: user_prompt})
        return format_prompt(
            history=origin_history,
            response_format=self._get_response_format(),
            outputs_config_list=self._get_outputs_list_from_conf(),
        )

    def _get_template_content(self) -> str:
        template_content_list = self._conf.get("templateContent") or []
        user_prompt = [
            element
            for element in template_content_list
            if element.get(_ROLE) == ChatHistoryRole.USER.value
        ]
        if not user_prompt or not isinstance(user_prompt[0], dict):
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_LLM_INIT_ERROR.code,
                message=StatusCode.WORKFLOW_LLM_INIT_ERROR.errmsg.format(
                    msg="Failed to retrieve llm template content"
                ),
            )
        return str(user_prompt[0].get("content"))

    def _get_llm_instance(self):
        try:
            llm_chain_configs_model = LLMChainConfig.model_validate(self._conf)
            return ModelFactory().get_model(
                model_type=llm_chain_configs_model.model.model_type,
                model_name=llm_chain_configs_model.model.model_name,
                runtime_context=self._runtime_context,
                **llm_chain_configs_model.model.hyper_parameters,
                **llm_chain_configs_model.model.extension,
            )
        except ValidationError as e:
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_LLM_INIT_ERROR.code,
                message=StatusCode.WORKFLOW_LLM_INIT_ERROR.errmsg.format(
                    msg=format_pydantic_validation_error_message(e)
                    if LOG_VERBOSE_MODE
                    else str(type(e).__name__)
                ),
            ) from e

    def _get_outputs_list_from_conf(self) -> List[dict]:
        """获取conf中定义的组件输出列表"""
        return self._conf.get(USER_FIELDS, {}).get("outputs") or []

    def _get_response_format(self):
        """获取格式化输出相关定义"""
        response_format = self._conf.get("responseFormat")
        if response_format.get(_TYPE) in response_format_to_prompt_map:
            instruction_name = response_format_to_prompt_map.get(
                response_format.get(_TYPE)
            ).get(_INSTRUCTION_NAME)
            if not response_format.get(instruction_name):
                template_name = response_format_to_prompt_map.get(
                    response_format.get(_TYPE)
                ).get(_TEMPLATE_NAME)
                intent_detection_template = TemplateManager().get(
                    name=template_name,
                    filters={"tag": self._conf.get("model", {}).get("modelName")},
                )
                response_format.update(
                    {instruction_name: intent_detection_template.content}
                )
        return response_format

    def _get_outputs_conf(self) -> dict:
        """
        获取特定格式的conf中定义的组件输出
        example:
            {"xxx": {"type": "xx", "description": "xx"}}
        """
        outputs_config_list = self._get_outputs_list_from_conf()
        return {config.get("id"): config for config in outputs_config_list}

    def _validate_config(self):
        response_config = self._get_response_format()
        self._validate_thinking_mode()
        # 当responseFormat中的type为markdown或者text的时候，用户定义的输出有且只有一个
        # 当responseFormat中的type为json的时候，用户定义的输出最少一个
        if not self._is_thinking_enabled() and response_config.get(_TYPE) in [
            WorkflowLLMResponseType.MARKDOWN.value,
            WorkflowLLMResponseType.TEXT.value,
        ]:
            if len(self._get_outputs_list_from_conf()) != 1:
                raise JiuWenBaseException(
                    error_code=StatusCode.WORKFLOW_LLM_INIT_ERROR.code,
                    message=StatusCode.WORKFLOW_LLM_INIT_ERROR.errmsg.format(
                        msg="When type in responseFormat is markdown or text, there is only one user-defined output"
                    ),
                )
        else:
            if len(self._get_outputs_list_from_conf()) < 1:
                raise JiuWenBaseException(
                    error_code=StatusCode.WORKFLOW_LLM_INIT_ERROR.code,
                    message=StatusCode.WORKFLOW_LLM_INIT_ERROR.errmsg.format(
                        msg="When type in responseFormat is set to JSON, at least one user-defined output is required"
                    ),
                )

    def _get_enable_history(self) -> bool:
        return self._conf.get("enableHistory")

    def _process_inputs(self, inputs: dict):
        # 在inputs中预埋CHAT_HISTORY变量
        workflow_chat_history: ConversationHistory = self._runtime_context.get(
            WORKFLOW_CHAT_HISTORY, None
        )
        if workflow_chat_history:
            chat_history = workflow_chat_history.get_conversation_history()
        else:
            chat_history = []
        chat_history = chat_history[:-1]
        full_input = ""
        chat_history = filter_enable_history(chat_history)
        for history in chat_history[-CHAT_HISTORY_MAX_TURN:]:
            full_input += "{}：{}\n".format(
                ROLE_MAP.get(history.get("role", "user"), "用户"),
                history.get("content"),
            )
        inputs.update({"CHAT_HISTORY": full_input})

    def _validate_thinking_mode(self):
        thinking_config = (
            self._conf.get("model", {}).get("hyperParameters", {}).get("thinking")
        )
        if thinking_config and thinking_config.get("type") not in [
            "enabled",
            "disabled",
        ]:
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_LLM_INIT_ERROR.code,
                message=StatusCode.WORKFLOW_LLM_INIT_ERROR.errmsg.format(
                    msg="model thinking type is not valid"
                ),
            )
