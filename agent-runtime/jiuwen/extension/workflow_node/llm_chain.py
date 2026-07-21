# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.

"""
LLMChain 组件 - 完整迁移自商用版本
适配到 openjiuwen 开源框架

功能特性:
- 完整的配置验证（包括思考模式验证）
- 对话历史管理
- 模板占位符安全验证
- 思考模式支持（reasoning_content）- 完整的流式处理
- 响应格式化（JSON/Markdown/Text）
- 流式输出处理
- 输出配置处理
- Token 使用统计
"""

import asyncio
import base64
import html
import ast
import json
import re
import time
from typing import Any, List, Optional, AsyncGenerator

from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error, ExecutionError
from jiuwen.common.exception.status_code import StatusCode as JiuWenStatusCode
from jiuwen.common.exception.base import JiuWenBaseException
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.foundation.llm import Model
from openjiuwen.core.foundation.prompt import PromptTemplate
from jiuwen.prompt import Prompt, Template
from openjiuwen.core.session.stream.base import CustomSchema
from openjiuwen.core.workflow import WorkflowComponent
from pydantic import BaseModel, StrictStr, Field, ValidationError

USER_FIELDS = "userFields"
PARTIAL_CONTENT = "partial_content"
JIUWEN_LLM_TYPE = "jiuwen.LLMComponent"
MEMORY_MESSAGE = "memory_message"

CHAT_HISTORY_MAX_TURN_DEFAULT = 3
_ROLE = "role"
_CONTENT = "content"
ROLE_MAP = {"user": "用户", "assistant": "助手", "system": "系统"}
MESSAGE_TYPE_TO_ROLE = {"human": "user", "ai": "assistant", "system": "system"}
_TYPE = "type"


class LLMChainModelConfig(BaseModel):
    model_name: StrictStr = Field(alias="modelName")
    model_type: StrictStr = Field(alias="modelType")
    hyper_parameters: dict = Field(alias="hyperParameters", default={})
    extension: dict = Field(default={})


class LLMChainConfig(BaseModel):
    model: LLMChainModelConfig
    deploy_mode: StrictStr = Field(alias="deployMode")
    template_content: list = Field(alias="templateContent")
    response_format: dict = Field(alias="responseFormat")
    enable_history: bool = Field(alias="enableHistory", default=True)
    user_fields: dict = Field(alias="userFields")


class LLMChainState:
    """LLMChain 状态管理"""

    def __init__(self):
        self.initialized = False
        self.llm = None


class ValidationUtils:
    """验证工具类"""

    @staticmethod
    def raise_invalid_params_error(error_msg: str = "") -> None:
        raise build_error(StatusCode.COMPONENT_LLM_CONFIG_INVALID, error_msg=error_msg)


class LLMChain(WorkflowComponent):
    """
    LLMChain 类 - 用于生成对话回复
    完全基于商用版本 jiuwen 中的 LLMChain 实现，适配到 openjiuwen 开源框架
    """

    def __init__(self, conf: dict = None):
        super().__init__()
        self._conf = conf or {}
        self._runtime_context = None
        self._llm = None
        self._metadata = None
        self._state = LLMChainState()
        self._session = None
        self._context = None
        self._initialized = False
        self._stream_final_output: dict | None = None
        self.mem_conf = None

    def init(self, conf: dict, **kwargs):
        """初始化组件配置"""
        self._conf = conf
        self._runtime_context = kwargs.get("runtime_context")
        self._metadata = kwargs.get("metadata")
        self.mem_conf = conf.get("memory", {})
        self._validate_config()

    async def _initialize_if_needed(self):
        """按需初始化模型"""
        if not self._initialized:
            try:
                self._llm = await self._create_llm_instance()
                self._initialized = True
            except Exception as e:
                raise build_error(
                    StatusCode.COMPONENT_LLM_INIT_FAILED,
                    error_msg="Failed to initialize LLM",
                ) from e

    async def _create_llm_instance(self):
        """创建 LLM 模型实例"""
        try:
            from agent_runtime.common.model_adapters import adapt_llm_chain_config
            from jiuwen.serve.controllers.execution.ir_converter import _get_model_config_provider

            provider = _get_model_config_provider()
            adapted_conf = adapt_llm_chain_config(self._conf)
            llm_comp_config = await provider.get_llm_config(adapted_conf)

            model = Model(
                model_client_config=llm_comp_config.model_client_config,
                model_config=llm_comp_config.model_config,
            )
            return model

        except ValidationError as e:
            raise build_error(
                StatusCode.COMPONENT_LLM_CONFIG_INVALID,
                error_msg=f"LLM config validation failed: {str(e)}",
            ) from e

    @staticmethod
    def _get_prompt_instance_by_template(template) -> PromptTemplate:
        """获取提示模板实例"""
        return PromptTemplate(template=template)

    async def invoke(self, inputs: dict[str, Any], session, context):
        """LLM 组件非流式调用接口"""
        await self._initialize_if_needed()
        self._session = session
        self._context = context

        inputs_data = inputs.get(USER_FIELDS, {})
        self._process_inputs(inputs_data)
        await self._resolve_vision_urls(inputs_data)

        language_model_inputs = self._get_model_input(inputs=inputs_data)

        try:
            llm_output = await self._llm.invoke(messages=language_model_inputs)

            formatted_res = self._format_response(
                llm_output.content,
                self._get_response_format().get("type"),
                (
                    llm_output.reasoning_content
                    if hasattr(llm_output, "reasoning_content")
                    else None
                ),
            )

            final_output = {USER_FIELDS: formatted_res}
            self._append_usage_metadata(llm_output, final_output)
            return final_output

        except Exception as e:
            raise build_error(
                StatusCode.COMPONENT_LLM_INVOKE_CALL_FAILED,
                error_msg=f"LLM invoke failed: {str(e)}",
            ) from e

    def get_stream_output(self) -> dict | None:
        """Return final batch output after stream completes for downstream ${node_llm...} refs."""
        return self._stream_final_output

    async def stream(self, inputs: dict[str, Any], session, context):
        """LLM 组件流式调用接口 - 支持思考模式

        思考开关三态：
          enabled  → _is_thinking_enabled()=True → reasoning 真流式 + content 假流式（预消费）
          None     → _is_thinking_enabled()=False 且 type 未设置 → content 真流式 + reasoning 真流式
          disabled → _is_thinking_enabled()=False 且 type=disabled → content 真流式，丢弃 reasoning
        """
        await self._initialize_if_needed()
        self._session = session
        node_id = session.get_component_id()
        self._context = context
        self._stream_final_output = None

        inputs_data = inputs.get(USER_FIELDS, {})
        self._process_inputs(inputs_data)

        # 三态判断：enabled / None / disabled
        thinking_config = (
            self._conf.get("model", {}).get("hyperParameters", {}).get("thinking", {})
        )
        thinking_type = thinking_config.get("type")
        is_enabled = self._is_thinking_enabled()
        # type 未设置（None/空值）时为 None 状态，其余非 enabled 都是 disabled
        is_none = not thinking_type
        output_reasoning = is_enabled or is_none

        if self._get_response_format().get("type") == "json":
            # JSON 模式：非流式调用后一次性输出
            result = await self.invoke(inputs, session, context)
            custom_data = {
                "node_id": node_id,
                "node_name": self._conf.get("name") or node_id,
                "node_type": JIUWEN_LLM_TYPE,
                "componentType": "LLM",
                "should_interrupt": False,
                "userFields": result.get(USER_FIELDS, {}),
                "model_stats": result.get("metadata", {}),
                "status": "finish",
            }
            if output_reasoning:
                custom_data["think"] = result.get(USER_FIELDS, {}).get("reasoning_content")
            await session.write_custom_stream(
                CustomSchema(type=PARTIAL_CONTENT, index=0, data=custom_data))
            self._stream_final_output = result
            yield result
        else:
            await self._resolve_vision_urls(inputs_data)
            language_model_inputs = self._get_model_input(inputs=inputs_data)

            # Multi-agent path: the sub-workflow LLM node's own ``memory.enable``
            # is False, and the jiuwen ``Workflow._update_runtime_context``
            # retrieval hook is bypassed (sub-workflows run via the agent-core
            # engine). Retrieve memory here when the multi-agent-level switch
            # ``enable_memory_retrieve`` is on, so the LLM can use long-term
            # memory in controller mode just like in direct-workflow mode.
            await self._inject_retrieved_memory(language_model_inputs, inputs_data)

            try:
                outputs_list = self._get_outputs_list_from_conf()
                output_id = "raw_output"
                if outputs_list and len(outputs_list) > 0:
                    output_id = outputs_list[0].get("id", "raw_output")

                if is_enabled:
                    # ── enabled: reasoning 真流式, content 假流式 ──
                    async for item in self._stream_thinking_enabled(
                        language_model_inputs, output_id, node_id, session
                    ):
                        yield item
                else:
                    # ── disabled / None: content 真流式 ──
                    # disabled → output_reasoning=False → 丢弃 reasoning
                    # None     → output_reasoning=True  → 输出 reasoning
                    async for item in self._stream_real_time(
                        language_model_inputs, output_id, node_id, session,
                        output_reasoning=output_reasoning,
                    ):
                        yield item

            except Exception as e:
                raise build_error(
                    StatusCode.COMPONENT_LLM_INVOKE_CALL_FAILED,
                    error_msg=f"LLM stream failed: {str(e)}",
                ) from e

    async def _process_thinking_stream(
        self, model_result, llm_inputs: dict
    ) -> tuple[AsyncGenerator, str, dict]:
        """
        预消费模型流，分离 content 和 reasoning_content

        工作流程：
        1. 完整遍历模型返回流
        2. 收集所有 content chunks 到列表
        3. 累积所有 reasoning_content 到字符串
        4. 收集 usage_metadata 和性能指标到 state
        5. 基于缓存的 content_chunks 构造异步迭代器

        Returns:
            tuple: (rawOutput generator, reasoning_content 完整字符串, state dict)
                   state 含 usage_metadata / first_token_ms / total_token_ms
        """
        content_chunks: list[str] = []
        reasoning_content: str = ""

        state = {
            "start_time": time.perf_counter(),
            "is_first_token": True,
            "usage_metadata": None,
            "first_token_ms": None,
            "total_token_ms": None,
        }

        try:
            if asyncio.iscoroutine(model_result):
                result_iter = await model_result
            else:
                result_iter = model_result

            reasoning_content = await self._consume_llm_stream(
                content_chunks, reasoning_content, result_iter, state
            )

        except Exception as e:
            raise build_error(
                StatusCode.COMPONENT_LLM_INVOKE_CALL_FAILED,
                error_msg=f"LLM stream failed: {str(e)}",
            ) from e

        # 流消费完成，记录 total_token 性能指标
        state["total_token_ms"] = round(
            (time.perf_counter() - state["start_time"]) * 1000)
        workflow_logger.info(f"total_token<llm>|{state['total_token_ms']}")

        accumulated_content = "".join(content_chunks)
        formatted_res = self._format_response(
            accumulated_content,
            self._get_response_format().get("type"),
            reasoning_content,
        )
        self._stream_final_output = {USER_FIELDS: formatted_res}

        async def raw_output_generator():
            """基于缓存的 content_chunks 重放生成流式数据"""
            accumulated_content = ""
            # 获取用户配置的输出字段名，默认使用 "raw_output"
            outputs_list = self._get_outputs_list_from_conf()
            output_id = "raw_output"
            if outputs_list and len(outputs_list) > 0:
                output_id = outputs_list[0].get("id", "raw_output")

            for chunk in content_chunks:
                if getattr(chunk, "finish_reason", "null") == "null":
                    accumulated_content += chunk
                yield {output_id: chunk}

            formatted_res = self._format_response(
                accumulated_content,
                self._get_response_format().get("type"),
                reasoning_content,
            )
            # 确保 output 中有 reasoning_content 字段
            if isinstance(formatted_res, dict):
                if (
                    "reasoning_content" not in formatted_res
                    or not formatted_res["reasoning_content"]
                ):
                    formatted_res["reasoning_content"] = reasoning_content

            yield {"final_output": formatted_res}

        return raw_output_generator(), reasoning_content, state

    async def _consume_llm_stream(
        self, content_chunks, reasoning_content, result_iter, state
    ):
        """消费 LLM 流，分离 content 和 reasoning_content，并收集 usage_metadata"""
        node_id = self._session.get_component_id() if self._session else ""
        node_name = self._conf.get("name") or node_id
        index = 0

        async for item in result_iter:
            if state["is_first_token"]:
                state["first_token_ms"] = round(
                    (time.perf_counter() - state["start_time"]) * 1000)
                workflow_logger.info(f"first_token<llm>|{state['first_token_ms']}")
                state["is_first_token"] = False

            # 收集 usage_metadata（取最后一个非空的）
            if hasattr(item, "usage_metadata") and item.usage_metadata:
                state["usage_metadata"] = item.usage_metadata

            if hasattr(item, "reasoning_content") and item.reasoning_content:
                reasoning_content += item.reasoning_content
                if self._session:
                    await self._session.write_custom_stream(
                        CustomSchema(
                            type=PARTIAL_CONTENT,
                            index=index,
                            data={
                                "answer": "",
                                "think": item.reasoning_content,
                                "node_id": node_id,
                                "node_name": node_name,
                                "node_type": JIUWEN_LLM_TYPE,
                                "should_interrupt": False,
                            },
                        )
                    )
                    index += 1

            if item.content:
                content_chunks.append(item.content)

        return reasoning_content

    async def _stream_thinking_enabled(
        self, language_model_inputs, output_id, node_id, session
    ):
        """思考开关 enabled: reasoning 真流式 + content 假流式（预消费）"""
        (
            raw_output_gen,
            reasoning_content,
            thinking_state,
        ) = await self._process_thinking_stream(
            self._llm.stream(messages=language_model_inputs),
            language_model_inputs,
        )
        async for chunk_data in raw_output_gen:
            raw_output = chunk_data.get(output_id) or chunk_data.get(
                "final_output", ""
            )
            if chunk_data.get("final_output"):
                usage_metadata = thinking_state.get("usage_metadata")
                model_stats = (
                    getattr(usage_metadata, 'model_stats', {}) or {}
                    if usage_metadata else {}
                )
                custom_data = {
                    "rawOutput": raw_output.get("rawOutput") if
                        isinstance(raw_output, dict) else raw_output,
                    "node_id": node_id,
                    "node_name": self._conf.get("name") or node_id,
                    "node_type": JIUWEN_LLM_TYPE,
                    "componentType": "LLM",
                    "userFields": raw_output,
                    "model_stats": model_stats,
                }
                if isinstance(raw_output, dict) and raw_output.get("reasoning_content"):
                    custom_data["think"] = raw_output.get("reasoning_content")
                # llm_info trace
                await session.trace(data={"llm_info": {
                    "llm_inputs": language_model_inputs,
                    "llm_outputs": chunk_data.get("llm_outputs") or chunk_data.get("final_output"),
                    "reasoning_content": reasoning_content
                }})
                # 性能 trace（批量）
                await session.trace(data={"performance_metric": {
                    "first_token<llm>": thinking_state.get("first_token_ms"),
                    "total_token<llm>": thinking_state.get("total_token_ms"),
                }})
                self._stream_final_output = custom_data
                # 调试信息走 yield（最后一帧，含 reasoning_content + usage）
                usage_dict = usage_metadata.model_dump() if usage_metadata else {}
                yield {
                    USER_FIELDS: {"reasoning_content": reasoning_content},
                    **usage_dict,
                }
            else:
                yield {USER_FIELDS: {output_id: raw_output}}

    async def _stream_real_time(
        self, language_model_inputs, output_id, node_id, session,
        output_reasoning=True,
    ):
        """真流式路径 — thinking 非 enabled 时走此路径

        Args:
            output_reasoning: 是否输出 reasoning_content
                True  → None 状态，思考模型返回的 reasoning 透传输出
                False → disabled 状态，即使模型返回了 reasoning 也丢弃不输出

        对齐商用 jiuwen _process_streaming_data_generator：
        - content 真流式输出（逐 chunk yield）
        - reasoning_content 根据 output_reasoning 决定是否输出
        """
        node_name = self._conf.get("name") or node_id
        accumulated_content = ""
        reasoning_content = ""
        model_stats = {}
        stream_state = {
            "start_time": time.perf_counter(),
            "is_first_token": True,
            "first_token_ms": None,
            "usage_metadata": None,
        }
        think_index = 0

        async for chunk in self._llm.stream(
            messages=language_model_inputs, tools=[]):
            # 收集 usage / metadata
            if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                stream_state["usage_metadata"] = chunk.usage_metadata
                model_stats = getattr(chunk.usage_metadata, 'model_stats', {}) or {}
            if hasattr(chunk, 'metadata') and chunk.metadata:
                model_stats.update(chunk.metadata)

            # first_token 性能统计
            if stream_state["is_first_token"]:
                stream_state["first_token_ms"] = round(
                    (time.perf_counter() - stream_state["start_time"]) * 1000)
                workflow_logger.info(f"first_token<llm>|{stream_state['first_token_ms']}")
                stream_state["is_first_token"] = False

            # reasoning_content: disabled 时丢弃，None 时真流式输出
            if output_reasoning and hasattr(chunk, "reasoning_content") and chunk.reasoning_content:
                reasoning_content += chunk.reasoning_content
                await session.write_custom_stream(
                    CustomSchema(
                        type=PARTIAL_CONTENT,
                        index=think_index,
                        data={
                            "answer": "",
                            "think": chunk.reasoning_content,
                            "node_id": node_id,
                            "node_name": node_name,
                            "node_type": JIUWEN_LLM_TYPE,
                            "componentType": "LLM",
                            "should_interrupt": False,
                        },
                    )
                )
                think_index += 1

            # content 真流式输出
            if chunk.content and chunk.content != "":
                if getattr(chunk, "finish_reason", "null") == "null":
                    accumulated_content += chunk.content
                yield {USER_FIELDS: {output_id: chunk.content}}

        # 流结束：性能统计 + trace + 最终帧
        total_token_ms = round(
            (time.perf_counter() - stream_state["start_time"]) * 1000)
        workflow_logger.info(f"total_token<llm>|{total_token_ms}")

        reasoning_for_format = reasoning_content if output_reasoning else None
        formatted_res = self._format_response(
            accumulated_content,
            self._get_response_format().get("type"),
            reasoning_for_format,
        )
        custom_data = {
            "rawOutput": accumulated_content,
            "node_id": node_id,
            "node_name": node_name,
            "node_type": JIUWEN_LLM_TYPE,
            "componentType": "LLM",
            "should_interrupt": False,
            "userFields": formatted_res,
            "model_stats": model_stats,
            "status": "finish",
        }
        # llm_info trace
        await session.trace(data={"llm_info": {
            "llm_inputs": language_model_inputs,
            "llm_outputs": accumulated_content,
            "reasoning_content": reasoning_for_format,
        }})
        # 性能 trace（批量）
        await session.trace(data={"performance_metric": {
            "first_token<llm>": stream_state["first_token_ms"],
            "total_token<llm>": total_token_ms,
        }})
        self._stream_final_output = custom_data
        # 最后一帧
        usage_dict = (
            stream_state["usage_metadata"].model_dump()
            if stream_state["usage_metadata"] else {}
        )
        final_frame = {USER_FIELDS: {"final_output": formatted_res}, **usage_dict}
        if output_reasoning and reasoning_content:
            final_frame[USER_FIELDS]["reasoning_content"] = reasoning_content
        yield final_frame

    def _format_response(
        self, content: str, response_type: str, reasoning_content: str = None
    ) -> dict:
        """格式化响应 - 支持 JSON/Markdown/Text 格式"""
        outputs_list = self._get_outputs_list_from_conf()
        result = {}

        if response_type == "json":
            parsed = self._extract_json(content)
            for output in outputs_list:
                output_id = output.get("id")
                if not output_id:
                    continue
                if output_id == "reasoning_content" and reasoning_content is not None:
                    result[output_id] = reasoning_content
                elif parsed and output_id in parsed:
                    result[output_id] = parsed[output_id]
                else:
                    result[output_id] = content
        else:
            for output in outputs_list:
                output_id = output.get("id")
                if not output_id:
                    continue
                if output_id == "reasoning_content" and reasoning_content is not None:
                    result[output_id] = reasoning_content
                else:
                    result[output_id] = content

        if not result:
            result = {"raw_output": content}

        return result

    @staticmethod
    def _extract_json(text: str) -> Optional[dict]:
        """从 LLM 输出中提取 JSON 对象"""
        if not text:
            return None
        text = text.strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1).strip())
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
        return None

    def _apply_format_instructions(self, messages: List[dict]) -> List[dict]:
        """注入格式控制指令到 prompt，从输入端约束模型的输出格式"""
        response_format = self._get_response_format()
        res_type = response_format.get("type", "text")

        if res_type == "text":
            return messages

        last_user_idx = None
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                last_user_idx = i
                break

        if last_user_idx is None:
            return messages

        user_content = messages[last_user_idx]["content"]

        if res_type == "markdown":
            default_instruction = (
                "Please return the answer in markdown format.\n"
                "- For headings, use number signs (#).\n"
                "- For list items, start with dashes (-).\n"
                "- To emphasize text, wrap it with asterisks (*).\n"
                "- For code or commands, surround them with backticks (`).\n"
                "- For quoted text, use greater than signs (>).\n"
                "- For links, wrap the text in square brackets [], "
                "followed by the URL in parentheses ().\n"
                "- For images, use square brackets [] for the alt text, "
                "followed by the image URL in parentheses ().\n"
                "The question is: ${query}."
            )
            instruction = response_format.get("markdownInstruction") or default_instruction
            if not instruction.strip():
                instruction = default_instruction
        elif res_type == "json":
            default_instruction = (
                "Carefully consider the user's question to ensure your answer "
                "is logical and makes sense.\n"
                "- Make sure your explanation is concise and easy to understand, "
                "not verbose.\n"
                "- Strictly return the answer in a valid json format only, and "
                '"DO NOT ADD ANY COMMENTS BEFORE OR AFTER IT".\n'
                "The question is: ${query}."
            )
            instruction = response_format.get("jsonInstruction") or default_instruction
            if not instruction.strip():
                instruction = default_instruction
        else:
            return messages

        messages[last_user_idx]["content"] = instruction.replace(
            "${query}", html.escape(user_content)
        )
        return messages

    def _get_chat_history(self) -> list[dict]:
        """从 context 获取对话历史"""
        if not self._context:
            return []
        try:
            messages = self._context.get_messages(with_history=True)
            return [self._message_to_dict(msg) for msg in messages]
        except Exception:
            return []

    @staticmethod
    def _message_to_dict(msg) -> dict:
        """将 BaseMessage 转换为 {role, content} 字典"""
        if isinstance(msg, dict):
            return msg
        role = getattr(msg, "type", "") or getattr(msg, "role", "")
        content = getattr(msg, "content", "")
        role = MESSAGE_TYPE_TO_ROLE.get(role, role)
        return {"role": role, "content": content}

    def _get_history(
        self, user_prompt: str, system_prompt: Optional[str] = None
    ) -> list[dict]:
        """构建包含对话历史的消息列表"""
        chat_history = self._get_chat_history()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if chat_history:
            for history in self._truncate_history_by_turn(chat_history, self._get_history_size()):
                role = history.get("role", "user")
                content = history.get("content", "")
                if role in ("user", "assistant", "system") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_prompt})
        return messages

    def _append_usage_metadata(self, llm_output, final_output: dict):
        """添加使用信息

        以 NEW openjiuwen 原生字段集为准，全字段铺平到 final_output 顶层。
        不做字段名映射、不补缺失字段、不删 NEW 多出的 cost 字段。
        """
        if (
            llm_output
            and hasattr(llm_output, "usage_metadata")
            and llm_output.usage_metadata
        ):
            final_output.update(llm_output.usage_metadata.model_dump())

    def _get_model_input(self, inputs: dict) -> List[dict]:
        """获取模型输入，包含系统提示和对话历史"""
        prompt_template = self._get_template_content()
        try:
            self._validate_prompt_template(prompt_template)
            user_prompt = self._render_prompt(prompt_template, inputs)
        except JiuWenBaseException:
            raise
        except ExecutionError:
            raise
        except Exception as e:
            raise build_error(
                StatusCode.COMPONENT_LLM_CONFIG_INVALID,
                error_msg="Failed to assemble llm template",
            ) from e

        system_template = self._get_system_template_content()
        system_prompt = None
        if system_template:
            try:
                self._validate_prompt_template(system_template)
                system_prompt = self._render_prompt(system_template, inputs)
            except JiuWenBaseException:
                raise
            except ExecutionError:
                raise
            except Exception as e:
                raise build_error(
                    StatusCode.COMPONENT_LLM_CONFIG_INVALID,
                    error_msg="Failed to assemble llm template",
                ) from e

        if self._get_enable_history():
            messages = self._get_history(user_prompt, system_prompt)
        else:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

        self._insert_memory_message(messages, inputs)
        messages = self._apply_format_instructions(messages)

        # 多模态视觉输入注入
        messages = self._get_vision(messages, inputs)

        return messages

    async def _resolve_vision_urls(self, inputs: dict) -> None:
        """提前将图片 URL 下载并转为 base64 data URI，就地替换 inputs 中的值

        在 invoke/stream 入口调用，将网络 I/O 与消息组装解耦。
        """
        model_conf = self._conf.get("model", {})
        extension = model_conf.get("extension", {})
        if not extension.get("vl_enable"):
            return
        for key in list(inputs.keys()):
            if "image_vision" not in key.lower():
                continue
            urls = inputs[key]
            if isinstance(urls, str):
                urls = [urls]
            resolved = []
            for url in urls:
                if isinstance(url, str) and url:
                    resolved.append(await self._resolve_image_url(url))
                else:
                    resolved.append(url)
            inputs[key] = resolved

    def _get_vision(self, messages: list[dict], inputs: dict) -> list[dict]:
        """多模态理解大模型视觉输入填充，考虑到历史会话将视觉输入放在最后一条 user 消息"""
        model_conf = self._conf.get("model", {})
        extension = model_conf.get("extension", {})
        vl_enable = extension.get("vl_enable")
        if not vl_enable:
            return messages

        # 收集视觉 URL
        vision_items = []
        for key, value in inputs.items():
            if "image_vision" in key.lower():
                urls = value if isinstance(value, list) else [value]
                for url in urls:
                    if isinstance(url, str) and url:
                        vision_items.append({"type": "image_url", "image_url": {"url": url}})
            if "video_vision" in key.lower():
                urls = value if isinstance(value, list) else [value]
                for url in urls:
                    if isinstance(url, str) and url:
                        vision_items.append({"type": "video_url", "video_url": {"url": url}})

        # 没有实际视觉内容时不转换消息格式，保持纯文本 content
        if not vision_items:
            return messages

        # 找到最后一条 user 消息并注入视觉内容
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                content = [{"type": "text", "text": messages[i]["content"]}]
                content.extend(vision_items)
                messages[i]["content"] = content
                break
        return messages

    @staticmethod
    async def _resolve_image_url(url: str) -> str:
        """将图片 URL 转为 base64 data URI，确保模型服务端可直接使用

        如果 URL 已经是 data URI 则直接返回；否则尝试下载并转为 base64。
        下载失败时返回原始 URL 作为兜底。
        """
        if url.startswith("data:"):
            return url
        try:
            import httpx
            async with httpx.AsyncClient(verify=False, timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "image/jpeg")
                if ";" in content_type:
                    content_type = content_type.split(";")[0].strip()
                b64 = base64.b64encode(resp.content).decode("utf-8")
                return f"data:{content_type};base64,{b64}"
        except Exception as e:
            workflow_logger.warning(f"Failed to resolve image URL to base64, using original URL: {url}, error: {e}")
            return url

    def _insert_memory_message(self, messages: list[dict], inputs: dict) -> None:
        """Inject retrieved long-term memory before the current user prompt."""
        memory_conf = self.mem_conf or self._conf.get("memory", {})
        if not (memory_conf and memory_conf.get("enable")):
            return

        memory_msg = inputs.get(MEMORY_MESSAGE) if isinstance(inputs, dict) else None
        if memory_msg is None and self._session:
            memory_msg = self._session.get_global_state(MEMORY_MESSAGE)
        if memory_msg is None and self._session:
            try:
                state = self._session.dump_state()
                memory_msg = (state or {}).get(MEMORY_MESSAGE)
                if memory_msg is None:
                    memory_msg = ((state or {}).get("global_state") or {}).get(
                        MEMORY_MESSAGE
                    )
            except Exception:
                memory_msg = None

        memory_content = self._extract_memory_content(memory_msg)
        if not memory_content:
            return

        insert_index = len(messages)
        for idx in range(len(messages) - 1, -1, -1):
            if messages[idx].get("role") == "user":
                insert_index = idx
                break
        messages.insert(insert_index, {"role": "user", "content": memory_content})

    @staticmethod
    def _extract_memory_content(memory_msg: Any) -> str:
        if memory_msg is None:
            return ""
        if isinstance(memory_msg, dict):
            return str(memory_msg.get("content") or "")

        content = getattr(memory_msg, "content", None)
        if content:
            return str(content)

        if not isinstance(memory_msg, str):
            return ""
        if not memory_msg.startswith("type="):
            return memory_msg

        match = re.search(
            r"content=('(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\")",
            memory_msg,
            re.DOTALL,
        )
        if not match:
            return memory_msg
        try:
            return str(ast.literal_eval(match.group(1)))
        except Exception:
            return match.group(1).strip("'\"")

    async def _inject_retrieved_memory(
        self, messages: list[dict], inputs: dict
    ) -> None:
        """Retrieve long-term memory for the multi-agent (controller) path.

        In controller mode the sub-workflow LLM node runs with
        ``memory.enable=False`` and the jiuwen retrieval hook is bypassed,
        so ``_insert_memory_message`` does nothing. This helper re-enables
        retrieval driven by the multi-agent-level ``enable_memory_retrieve``
        switch: it reads ``memory_repo_id`` / ``userId`` from the session
        global_state (populated from workflow_req_params), retrieves matching
        memories, and inserts them before the current user message.

        No-op when retrieval is disabled, params are missing, or no memory
        is found — so direct-workflow mode (which pre-injects via
        ``_insert_memory_message``) is unaffected.
        """
        try:
            if not (self._session and hasattr(self._session, "get_global_state")):
                return
            emr = self._session.get_global_state("enable_memory_retrieve")
            if not emr:
                return
            scope_id = self._session.get_global_state("memory_repo_id")
            if not scope_id:
                return
            gv = self._session.get_global_state("global_variables") or {}
            user_id = ""
            if isinstance(gv, dict):
                user_id = gv.get("userId", "") or ""
                # Fallback: in multi-agent mode the top-level userId is often
                # empty even though sys.userId carries the real user id.
                if not user_id:
                    sys_args = gv.get("sys") or {}
                    if isinstance(sys_args, dict):
                        user_id = sys_args.get("userId", "") or ""
            if not user_id:
                return
            query = ""
            if isinstance(inputs, dict):
                query = str(inputs.get("query", "") or "")
            if not query:
                return

            from agent_runtime.memory.memory_retrieval import retrieve_memory_prompt

            memory_prompt = await retrieve_memory_prompt(
                user_id=user_id, scope_id=scope_id, query=query
            )
            if not memory_prompt:
                return
            # Insert memory as a user message right before the last user message,
            # mirroring _insert_memory_message placement.
            insert_index = len(messages)
            for idx in range(len(messages) - 1, -1, -1):
                if messages[idx].get("role") == "user":
                    insert_index = idx
                    break
            messages.insert(insert_index, {"role": "user", "content": memory_prompt})
        except Exception as e:
            workflow_logger.warning(
                "Failed to inject retrieved memory in controller mode: %s",
                e,
                exc_info=True,
            )

    def _validate_prompt_template(self, template: str) -> None:
        """
        在 invoke 之前校验模板源，拦截危险占位符（如 query.__class__、表达式等）。
        只依赖模板字符串，不依赖运行时 inputs。
        """
        if not template:
            return

        texts: list[str] = [template]

        placeholder_find_pattern = re.compile(r"\{\{([^{}]*)\}\}")
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

    @staticmethod
    def _normalize_template_placeholders(template: str) -> str:
        """归一化模板中的占位符，去除 {{ }} 内部的前后空白

        与旧版 TextableVariable 的处理对齐：将 {{ query   }} 归一化为 {{query}}，
        确保后续精确字符串替换和残留校验能正确工作。
        """
        return re.sub(
            r"\{\{([^{}]*)\}\}",
            lambda m: "{{" + m.group(1).strip() + "}}",
            template,
        )

    def _render_prompt(self, template: str, inputs: dict) -> str:
        """渲染提示模板，校验未定义变量"""
        result = self._normalize_template_placeholders(template)
        for key, value in inputs.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        # 校验：如果还有未替换的 {{...}}，说明引用了不存在的变量
        remaining = re.findall(r'\{\{([^{}]*)\}\}', result)
        if remaining:
            raise ExecutionError(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                msg=JiuWenStatusCode.PROMPT_ASSEMBLER_INPUT_KEY_ERROR.errmsg
                    + f", root cause=Error parsing the placeholder `{remaining[0]}`.",
            )
        return result

    def _get_template_content(self) -> str:
        """获取用户模板内容"""
        template_content_list = self._conf.get("templateContent", [])
        user_prompts = [
            element for element in template_content_list if element.get(_ROLE) == "user"
        ]

        if not user_prompts or not isinstance(user_prompts[0], dict):
            raise build_error(
                StatusCode.COMPONENT_LLM_CONFIG_INVALID,
                error_msg="Failed to retrieve llm template content",
            )

        return str(user_prompts[0].get("content", ""))

    def _get_system_template_content(self) -> Optional[str]:
        """获取系统模板内容"""
        template_content_list = self._conf.get("templateContent", [])
        system_prompts = [
            element
            for element in template_content_list
            if element.get(_ROLE) == "system"
        ]
        if not system_prompts:
            return None
        return str(system_prompts[0].get("content", ""))

    def _get_outputs_list_from_conf(self) -> List[dict]:
        """获取输出列表"""
        return self._conf.get(USER_FIELDS, {}).get("outputs", [])

    def _get_outputs_conf(self) -> dict:
        """
        获取特定格式的conf中定义的组件输出
        example:
            {"xxx": {"type": "xx", "description": "xx"}}
        """
        outputs_config_list = self._get_outputs_list_from_conf()
        return {config.get("id"): config for config in outputs_config_list}

    def _get_response_format(self):
        """获取响应格式"""
        return self._conf.get("responseFormat", {"type": "text"})

    def _validate_config(self):
        """验证配置"""
        try:
            LLMChainConfig.model_validate(self._conf)
            self._validate_thinking_mode()

            response_config = self._get_response_format()
            # 非 enabled 时 reasoning 不可用，markdown/text 只允许一个输出
            if not self._is_thinking_enabled() and response_config.get(_TYPE) in [
                "markdown",
                "text",
            ]:
                if len(self._get_outputs_list_from_conf()) != 1:
                    raise build_error(
                        StatusCode.COMPONENT_LLM_CONFIG_INVALID,
                        error_msg="When type in responseFormat is markdown or text, there is only one user-defined output",
                    )
            else:
                # enabled / None 时 reasoning_content 可作为输出字段，至少需要1个输出
                if len(self._get_outputs_list_from_conf()) < 1:
                    raise build_error(
                        StatusCode.COMPONENT_LLM_CONFIG_INVALID,
                        error_msg="When type in responseFormat is set to JSON, at least one user-defined output is required",
                    )

        except ValidationError as e:
            raise build_error(
                StatusCode.COMPONENT_LLM_CONFIG_INVALID,
                error_msg=f"Invalid LLM config: {str(e)}",
            )

    def _validate_thinking_mode(self):
        """验证思考模式配置"""
        thinking_config = (
            self._conf.get("model", {}).get("hyperParameters", {}).get("thinking")
        )
        if thinking_config and thinking_config.get("type") not in [
            "enabled",
            "disabled",
        ]:
            raise build_error(
                StatusCode.COMPONENT_LLM_CONFIG_INVALID,
                error_msg="model thinking type is not valid",
            )

    def _is_thinking_enabled(self) -> bool:
        """检查是否开启了思考模式"""
        thinking_config = (
            self._conf.get("model", {}).get("hyperParameters", {}).get("thinking", {})
        )
        return thinking_config.get("type") == "enabled"

    def _get_enable_history(self) -> bool:
        """获取是否启用历史记录"""
        return self._conf.get("enableHistory", False)

    def _get_history_size(self) -> int:
        """获取对话历史截断轮数，优先读取 IR 配置中的 historySize，否则使用默认值"""
        return self._conf.get("historySize", CHAT_HISTORY_MAX_TURN_DEFAULT)

    @staticmethod
    def _truncate_history_by_turn(chat_history: list[dict], num_turns: int) -> list[dict]:
        """按轮数截取对话历史。

        1 轮 = 1 条 user 消息 + 其对应的所有回复 (assistant/function/tool 等)。
        从后往前按 user 消息计数，确保截断起点一定是 user 消息，
        避免残留孤立的 assistant/tool 消息导致模型上下文不完整。

        Args:
            chat_history: 对话历史列表，每项为 {role, content} 字典
            num_turns: 对话轮数

        Returns:
            最近 num_turns 轮的消息
        """
        if not chat_history or num_turns <= 0:
            return []

        start_index = 0
        user_count = 0
        for i in range(len(chat_history) - 1, -1, -1):
            if chat_history[i].get("role") == "user":
                user_count += 1
                if user_count == num_turns:
                    start_index = i
                    break

        if user_count < num_turns:
            return chat_history

        return chat_history[start_index:]

    def _process_inputs(self, inputs: dict):
        """处理输入数据 - 预埋 CHAT_HISTORY 变量"""
        if not self._get_enable_history():
            inputs.update({"CHAT_HISTORY": ""})
            return

        chat_history = self._get_chat_history()
        full_input = ""
        for history in self._truncate_history_by_turn(chat_history, self._get_history_size()):
            full_input += "{}：{}\n".format(
                ROLE_MAP.get(history.get("role", "user"), "用户"),
                history.get("content"),
            )
        inputs.update({"CHAT_HISTORY": full_input})
