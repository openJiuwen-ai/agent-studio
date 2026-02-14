#!/usr/bin/python3.10
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, AsyncGenerator, List
import asyncio

from jinja2 import Environment, BaseLoader, TemplateError, UndefinedError
from jinja2.sandbox import SandboxedEnvironment, SecurityError
from openai import OpenAIError

from openjiuwen.core.common.logging import logger

try:
    from ops_client.decorator import observe
    from ops_client.tracer import set_baggage, get_baggage, calculate_input_tokens, set_attribute, start_span, end_span
    from ops_client.entities import SpanType, PlatformType
    from ops_client import trace, inject
except ImportError:
    from openjiuwen_studio.ops.modules.prompt.application.trace_sdk_interface import observe, set_baggage, \
        get_baggage, calculate_input_tokens, set_attribute, start_span, end_span, SpanType, PlatformType, \
        trace, inject

from openjiuwen_studio.ops.modules.llm.llm_manager import build_call_kwargs, ModelCallParams, get_llm_client_by_protocol
from openjiuwen_studio.ops.modules.prompt.domain.debug_entity import (
    SaveDebugContextRequest,
    ListDebugHistoryResponse,
    DebugContext,
    DebugStreamingRequest,
    DebugStreamingResponse,
)
from openjiuwen_studio.ops.modules.prompt.domain.debug_repository import DebugContextRepository, DebugLogRepository
from openjiuwen_studio.core.utils.compatible_field import mask_sensitive_fields


headers = {}


class VarType(str, Enum):
    """ prompt 变量类型 """
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    PLACEHOLDER = "placeholder"


@dataclass
class TemplateRenderConfig:
    template_msgs: List[Dict[str, Any]]
    variables: List[Dict[str, Any]]
    var_defs: Optional[List[Dict[str, Any]]] = None
    template_type: str = "normal"


class TemplateRenderError(RuntimeError):
    """模板渲染失败专用异常"""
    pass


@dataclass
class SaveDebugLogParam:
    """保存调试日志的参数"""
    prompt: Dict[str, Any]
    start_time: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None
    single_step_debug: bool = False
    debug_logs: List[Dict[str, Any]] = None


class PromptDebugService:
    """
    调试相关用例的应用服务层
    所有数据库操作通过Repository接口完成，不直接依赖 SQLAlchemy
    """

    def __init__(
            self,
            debug_ctx_repo: DebugContextRepository,
            debug_log_repo: DebugLogRepository,
    ):
        self.debug_ctx_repo = debug_ctx_repo
        self.debug_log_repo = debug_log_repo
        self.jinja_env = SandboxedEnvironment(
            autoescape=False,
            loader=BaseLoader(),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # 用于生成唯一的整数ID
        self._debug_id_counter = int(time.time() * 1000) % 1000000

    @staticmethod
    def _expand_placeholders(
            template_msgs: List[Dict[str, Any]],
            variables: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        把 template_msgs 中的 role == "placeholder" 元素，
        用 variables 里同 key 的 placeholder_messages 平铺展开。
        返回新的 message list。
        """
        var_map = {}
        for v in (variables or []):
            # 这里可以检查变量类型，确保只处理 PLACEHOLDER 类型
            if v.get("type") == "placeholder" or "placeholder_messages" in v:
                var_map[v["key"]] = v

        expanded = []
        for msg in template_msgs:
            if msg.get("role") == "placeholder":
                key = msg.get("content")
                if not key:
                    # 如果没有指定 key，可以记录警告或跳过
                    continue

                cfg = var_map.get(key, {})
                placeholder_msgs = cfg.get("placeholder_messages") or []

                if not placeholder_msgs:
                    # 如果没有找到对应的 placeholder 消息，可以记录警告
                    # 或者保留原始 placeholder 消息作为 fallback
                    expanded.append({
                        "role": "system",  # 或者保持为 "placeholder"
                        "content": f"⚠️ Placeholder '{key}' not found in variables"
                    })
                    continue

                # 展开历史对话
                for hist in placeholder_msgs:
                    # 确保每条消息都有必要的字段
                    expanded.append({
                        "role": hist.get("role", "user"),
                        "content": str(hist.get("content", "")),
                        # 保留其他可能的字段
                        **{k: v for k, v in hist.items() if k not in ["role", "content"]}
                    })
            else:
                # 非 placeholder 消息直接添加
                expanded.append(msg)

        return expanded

    @staticmethod
    def _build_tools(raw_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def _array_to_schema(params: List[dict]) -> dict:
            """UI 数组 -> OpenAI JSON Schema"""
            properties = {}
            required = []
            for p in params:
                name = p["name"]
                properties[name] = {
                    "type": p.get("type", "string"),
                    "description": p.get("description", "")
                }
                if p.get("required"):
                    required.append(name)
            return {"type": "object", "properties": properties, "required": required}

        functions = []
        for t in raw_tools or []:
            func_def = t.get("function", {})
            parameters = func_def.get("parameters") or {}
            if isinstance(parameters, str):
                parameters = json.loads(parameters)

            # 关键：如果是数组就转 Schema
            if isinstance(parameters, list):
                parameters = _array_to_schema(parameters)

            functions.append(
                {
                    "type": "function",
                    "function": {
                        "name": func_def.get("name"),
                        "description": func_def.get("description") or "",
                        "parameters": parameters,
                    },
                }
            )
        return functions

    @staticmethod
    def _parse_variable(
            value: str,
            var_type: VarType,
    ) -> Any:
        """
        根据声明的类型解析/校验变量值
        """
        # 对于 PLACEHOLDER 类型，直接返回原始值或特殊处理
        if var_type == VarType.PLACEHOLDER:
            # placeholder 变量通常包含消息列表，直接返回不解析
            return value

        value = value.strip() if isinstance(value, str) else str(value)

        try:
            if var_type == VarType.OBJECT:
                return json.loads(value)  # 必须是合法 JSON
            if var_type == VarType.INTEGER:
                return int(value)
            if var_type == VarType.FLOAT:
                return float(value)
            if var_type == VarType.BOOLEAN:
                # 支持 true/True/1/false/False/0
                return value.lower() in {"true", "1"}

            return value
        except ValueError:
            # 解析失败时直接按字符串返回（或自行抛出异常）
            return value

    @staticmethod
    def _get_mock_response(mock_tools: List[Dict[str, Any]], tool_name: str) -> Any:
        """ mock_tools 里找对应 tool_name 的 mock_response """
        for t in mock_tools or []:
            if t.get("name") == tool_name:
                return t.get("mock_response")
        # 如果前端没给，直接抛异常
        raise RuntimeError(f"Mock response for tool '{tool_name}' not found.")

    @classmethod
    def _parse_llm_stream_res(cls, stream_items):
        if not stream_items:
            return {"combined_content": "", "metadata": {}}
        res = {}
        tool_calls_delta: List[Dict[str, Any]] = []
        reasoning_content, normal_content = "", ""
        for chunk in stream_items:
            delta = chunk
            if getattr(delta, "reasoning_content", None):
                reasoning_content += delta.reasoning_content
            if delta.tool_calls is not None:
                for tc in delta.tool_calls:
                    tool_calls_delta.append(tc.model_dump())
            if delta.content:
                normal_content = delta.content

        res['choices'] = {
            'reasoning_content': reasoning_content,
            'normal_content': normal_content,
            'tool_call_delta': tool_calls_delta
        }
        return res

    @observe(
        span_type=SpanType.PromptRunner,
        process_inputs=lambda data: data['args'][0].variable_vals if len(data['args']) > 0 else None,
        baggage={
            'method': 'POST',
            'platform_type': PlatformType.Prompt,
            'language': 'Python'})
    async def stream_and_save(
            self,
            req: DebugStreamingRequest,
            llm_config: Dict[str, Any],
    ) -> AsyncGenerator[str, None]:
        """调用大模型进行流式输出，并保存调试上下文"""
        debug_id = self._generate_debug_id()  # 生成整数类型的debug_id
        inject(headers)
        set_attribute('input_tokens', calculate_input_tokens(str(req.variable_vals)))
        set_baggage('debug_id', debug_id)
        set_attribute('debug_id', debug_id)
        if req.prompt.get('prompt_basic', {}).get('display_name', ''):
            set_attribute('span_name', req.prompt.get('prompt_basic').get('display_name'))
        elif req.prompt.get('prompt_key', ''):
            set_attribute('span_name', req.prompt.get('prompt_key'))

        llm_protocol_config = llm_config.get("protocol_config", {})

        """参数准备和验证阶段"""
        debug_context = await self._init_debug_context(debug_id, req, llm_config)
        if debug_context.get('error'):
            yield debug_context['error']
            return

        debug_logs = debug_context.get('debug_logs', [])
        call_kwargs = debug_context.get('call_kwargs', {})

        """大模型流式调用处理阶段"""
        llm_span = start_span('llm_streaming', SpanType.LLMCall, child_of=headers)
        set_attribute('debug_id', debug_id)
        llm_span.set_input_tokens(calculate_input_tokens(str(req.variable_vals)))
        llm_span.set_space_id(req.prompt.get('workspace_id'))
        llm_span.set_stream(True)
        llm_span.set_input(call_kwargs)
        tool_calls_delta: List[Dict[str, Any]] = []
        tool_call_index = 0

        # ----------  第一段流：思维链 / 工具调用 / 普通文本 ----------
        try:
            debug_logs.append({
                "timestamp": time.time(),
                "level": "info",
                "message": "开始调用大模型",
                "step": "llm_call"
            })
            llm_span.set_start_time_first_rest()
            call_kwargs.pop('model', None)
            call_kwargs.pop('model_name', None)
            openai_coroutine = get_llm_client_by_protocol(llm_protocol_config).stream(**call_kwargs)
            logger.info(
                f"llm config:\n {json.dumps(mask_sensitive_fields(llm_protocol_config), indent=4, ensure_ascii=False)}")
            logger.info(
                f"llm call_params:\n {json.dumps(mask_sensitive_fields(call_kwargs), indent=4, ensure_ascii=False)}")

            async for chk in llm_span.set_async_stream_output(
                openai_coroutine, process_outputs=self._parse_llm_stream_res):
                delta = chk
                # 1. 思维链
                if getattr(delta, "reasoning_content", None):
                    yield f"""data: {DebugStreamingResponse(
                        delta={'reasoning_content': delta.reasoning_content},
                        finish_reason=None,
                        debug_id=str(debug_id),
                        debug_trace_key=req.debug_trace_key
                    ).model_dump_json()}\n\n"""
                    continue

                # 2. 工具调用
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    id_set = {items['id'] for items in tool_calls_delta}
                    for tc in delta.tool_calls:
                        if tc.id and tc.id in id_set:
                            new_item = tc.model_dump()
                            next((item.update({k: v for k, v in new_item.items() if v}) or item
                                  for item in tool_calls_delta if item['id'] == new_item['id']), new_item)
                        elif tc.id:
                            tool_calls_delta.append(tc.model_dump())
                            tool_call_index = tc.index
                        else:
                            tool_calls_delta[tool_call_index]["arguments"] += tc.arguments

                    debug_logs.append({
                        "timestamp": time.time(),
                        "level": "info",
                        "message": f"检测到工具调用: {[tc.get('name', '') for tc in tool_calls_delta]}",
                        "step": "tool_detection"
                    })
                    yield f"""data: {DebugStreamingResponse(
                        delta=delta.model_dump(exclude_unset=True),
                        finish_reason=None,
                        debug_id=str(debug_id),
                        debug_trace_key=req.debug_trace_key
                    ).model_dump_json()}\n\n"""
                    continue

                # 3. 普通文本
                if delta.content:
                    yield f"""data: {DebugStreamingResponse(
                        delta={'content': delta.content},
                        finish_reason=None,
                        debug_id=str(debug_id),
                        debug_trace_key=req.debug_trace_key
                    ).model_dump_json()}\n\n"""
            debug_logs.append({
                "timestamp": time.time(),
                "level": "info",
                "message": "大模型调用完成",
                "step": "llm_complete"
            })

        except OpenAIError as e:
            debug_logs.append({
                "timestamp": time.time(),
                "level": "error",
                "message": f"OpenAI调用错误: {e.type} - {e.message}",
                "step": "llm_call"
            })
            yield f"event: error\ndata: {json.dumps({'code': 500, 'msg': f'{e.type} - {e.message}'})}\n\n"
            end_span(llm_span)
            return
        except (TimeoutError, asyncio.TimeoutError) as e:
            err_msg = str(e)
            debug_logs.append({
                "timestamp": time.time(),
                "level": "error",
                "message": f"大模型调用超时: {err_msg}",
                "step": "llm_call"
            })
            hint = "Try increasing the timeout in the model configuration and retry."
            yield f"event: error\ndata: {json.dumps({'code': 500, 'msg': f'{err_msg} {hint}'.strip()})}\n\n"
            end_span(llm_span)
            return
        except Exception as e:
            debug_logs.append({
                "timestamp": time.time(),
                "level": "error",
                "message": f"大模型调用异常: {str(e)}",
                "step": "llm_call"
            })
            yield f"event: error\ndata: {json.dumps({'code': 500, 'msg': str(e)})}\n\n"
            end_span(llm_span)
            return
        end_span(llm_span)

        """工具调用执行阶段"""
        # ----------  第二段流：工具回调 ----------
        if tool_calls_delta:
            try:
                debug_logs.append({
                    "timestamp": time.time(),
                    "level": "info",
                    "message": "开始执行工具调用",
                    "step": "tool_execution"
                })

                async for pkt in self._execute_tools_and_stream(
                        tool_calls_delta,
                        call_kwargs["messages"].copy(),
                        call_kwargs,
                        debug_id,
                        llm_protocol_config,
                        req.debug_trace_key,
                        req.mock_tools,
                        debug_logs
                ):
                    yield pkt

                debug_logs.append({
                    "timestamp": time.time(),
                    "level": "info",
                    "message": "工具调用执行完成",
                    "step": "tool_complete"
                })
            except Exception as e:
                debug_logs.append({
                    "timestamp": time.time(),
                    "level": "error",
                    "message": f"工具调用执行失败: {str(e)}",
                    "step": "tool_execution"
                })
                yield f"event: error\ndata: {json.dumps({'code': 500, 'msg': f'tool_call: {str(e)}'})}\n\n"
                return
        """流程结束和资源清理阶段"""
        # ----------  结束 ----------
        async for chunk in self._finish_stream(req, debug_logs, {
            'debug_id': debug_id,
            'tool_calls_delta': tool_calls_delta,
            'start_time': debug_context.get('start_time')
        }):
            yield chunk

    async def _finish_stream(self, req, debug_logs, record: dict) -> AsyncGenerator[str, None]:
        """结束流程"""
        error = None
        try:
            res = DebugStreamingResponse(
                delta=None,
                finish_reason='stop',
                usage={'input_tokens': 0, 'output_tokens': 0},
                debug_id=str(record.get('debug_id')),
                debug_trace_key=req.debug_trace_key
            ).model_dump_json()
            yield f"data: {res}\n\n"

            debug_logs.append({
                "timestamp": time.time(),
                "level": "info",
                "message": "调试流程完成",
                "step": "complete"
            })
        except Exception as e:
            error = e
            debug_logs.append({
                "timestamp": time.time(),
                "level": "error",
                "message": f"结束流程异常: {str(e)}",
                "step": "complete"
            })
            raise
        finally:
            # 确保无论如何都保存调试日志
            try:
                asyncio.create_task(self._save_debug_log(SaveDebugLogParam(
                    prompt=req.prompt,
                    start_time=record['start_time'],
                    result={
                        "debug_id": record.get('debug_id'),
                        "debug_trace_key": req.debug_trace_key,
                        "status": "completed",
                        "tool_calls_count": len(record['tool_calls_delta'])
                    },
                    error=error,
                    single_step_debug=req.single_step_debug if hasattr(req, 'single_step_debug') else False,
                    debug_logs=debug_logs
                ), record.get('debug_id')))
            except Exception as e:
                logger.error(f"保存调试日志时发生错误: {e}")

    async def _init_debug_context(self, debug_id, req: DebugStreamingRequest, llm_config: Dict[str, Any]) -> dict:
        """初始化调试上下文"""
        params_span = start_span('build_call_kwargs', SpanType.Prompt, child_of=headers)
        set_attribute('debug_id', debug_id)
        params_span.set_input_tokens(calculate_input_tokens(str(req.variable_vals)))
        if req.prompt.get('prompt_key', ''):
            params_span.set_prompt_key(req.prompt.get('prompt_key'))
        if req.prompt.get('prompt_basic', '').get('latest_version', ''):
            params_span.set_prompt_version(req.prompt.get('prompt_basic').get('latest_version'))
        params_span.set_space_id(req.prompt.get('workspace_id'))
        params_span.set_stream(False)
        params_span.set_input(req.variable_vals)

        start_time = time.time()
        # 参数准备
        debug_logs = [{
            "timestamp": time.time(),
            "level": "info",
            "message": "开始调试流程",
            "step": "init",
            "debug_id": debug_id
        }]

        try:
            call_params = self._init_prompt_and_params(req)

            debug_logs.append({
                "timestamp": time.time(),
                "level": "info",
                "message": f"初始化参数完成，模型: {call_params.model_id}",
                "step": "params_init"
            })
            # 构建调用参数
            call_kwargs = build_call_kwargs(call_params, llm_config)
            debug_logs.append({
                "timestamp": time.time(),
                "level": "info",
                "message": "构建调用参数完成",
                "step": "build_kwargs"
            })
            params_span.set_output(call_kwargs)
            end_span(params_span)

            return {
                'debug_id': debug_id,
                'start_time': start_time,
                'debug_logs': debug_logs,
                'call_params': call_params,
                'call_kwargs': call_kwargs,
                'req': req,
                'tool_calls_delta': [],
               'error': None
            }
        except TemplateRenderError as e:
            error_msg = f"event: error\ndata: {json.dumps({'debug_id': debug_id, 'msg': f'{str(e)}'})}\n\n"
            end_span(params_span)
            return {'error': error_msg}
        except Exception as e:
            error_msg = (f"event: error\ndata: "
                         f"{json.dumps({'debug_id': debug_id, 'msg': f'build_call_kwargs: {str(e)}'})}\n\n")
            end_span(params_span)
            return {'error': error_msg}

    async def get_debug_context(self, prompt_id: int, user_id: str) -> Optional[DebugContext]:
        """
        查询调试上下文
        根据 prompt_id + workspace_id 查询 prompt_debug_context 表中最新记录
        """
        return await self.debug_ctx_repo.fetch(prompt_id, user_id)

    async def save_debug_context(self, user_id, req: SaveDebugContextRequest) -> Dict[str, Any]:
        """
        保存调试上下文
        1. upsert prompt_debug_context
        2. 新增一条 debug_log 记录（这里简单记录：把 debug_context 转 JSON）
        """
        save = req.model_dump()
        save["user_id"] = user_id
        await self.debug_ctx_repo.upsert(save)

        return {"saved": True}

    async def list_debug_history(
            self, prompt_id: int, workspace_id: str, days_limit: Optional[int], page_size: int,
            page_token: Optional[str]
    ) -> ListDebugHistoryResponse:
        """
        分页查询调试日志
        按时间倒序查询 prompt_debug_log 表
        """
        logs = await self.debug_log_repo.list_records(
            prompt_id, workspace_id, days_limit, page_size, page_token
        )
        return ListDebugHistoryResponse(
            debug_history=logs,
            has_more=len(logs) == page_size,
            next_page_token=str(int(page_token or 0) + page_size) if len(logs) == page_size else None,
        )

    def _render_template(self, config: TemplateRenderConfig) -> List[Dict[str, Any]]:
        """
        支持两种渲染模式：
        - normal：简单 {{key}} 替换
        - jinja2：完整 jinja2 语法
        """
        # 构建变量映射
        var_map = self._build_variable_map(config.variables, config.var_defs)

        # 渲染消息
        return self._render_messages(config.template_msgs, config.variables, var_map, config.template_type)

    def _build_variable_map(self, variables: List[Dict[str, Any]], var_defs: Optional[List[Dict[str, Any]]]) -> Dict[
        str, Any]:
        """构建变量映射"""
        var_map = {}
        type_map = {vd["key"]: VarType(vd["type"]) for vd in (var_defs or [])}

        for item in (variables or []):
            key = item["key"]
            var_type = type_map.get(key, VarType.STRING)

            # 对于 PLACEHOLDER 类型，不加入变量映射
            if var_type == VarType.PLACEHOLDER:
                continue

            var_map[key] = self._parse_variable(
                value=item.get("value") or "",
                var_type=var_type
            )
        return var_map

    def _render_messages(self, template_msgs: List[Dict[str, Any]], variables: List[Dict[str, Any]],
                         var_map: Dict[str, Any], template_type: str) -> List[Dict[str, Any]]:
        """渲染消息列表"""
        rendered = []
        # 展开 placeholder
        for msg in self._expand_placeholders(template_msgs, variables):
            raw_content = str(msg.get("content") or "")
            try:
                if template_type == "jinja2":
                    content = self.jinja_env.from_string(raw_content).render(**var_map)
                else:
                    # normal 模式
                    content = raw_content
                    for k, v in var_map.items():
                        content = content.replace(f"{{{k}}}", str(v))

            except (TemplateError, TypeError, UndefinedError, SecurityError) as e:
                raise TemplateRenderError(
                    "Jinja2 渲染失败，变量 map=%s，错误=%s", var_map, str(e)) from e

            rendered.append({**msg, "content": content})
        return rendered

    def _init_prompt_and_params(self, req: DebugStreamingRequest):
        """
        拼接prompt模板，获取工具列表，返回：
        model_id, final_messages, tools, tool_choice
        """
        # 取模板（从prompt_draft中获取）
        prompt_detail = req.prompt.get("prompt_draft", {}).get("detail", {})
        template_obj = prompt_detail.get("prompt_template", {})
        tools_raw = prompt_detail.get("tools", [])

        # 渲染系统模板
        rendered_system_msgs = self._render_template(
            TemplateRenderConfig(
                template_obj.get("messages", []),
                req.variable_vals or [],
                template_obj.get("variable_defs", []),
                template_obj.get("template_type", "normal")
            )
        )

        # 合并用户历史对话
        history = req.messages or []
        final_messages = [*rendered_system_msgs, *history]

        # 工具
        tools = [json.loads(tool) if isinstance(tool, str) else tool for tool in tools_raw]

        tool_choice = (
            prompt_detail.get("tool_call_config", {}).get("tool_choice")
            if tools else None
        )

        # model_id 来自入参
        model_cfg = prompt_detail.get("prompt_model_config", {})
        model_id = model_cfg.get("models_id")
        model_from = model_cfg.get("model_from")
        if not model_id:
            raise TemplateRenderError("models_id is missing in prompt_model_config")

        return ModelCallParams(
            model_id=model_id,
            model_from=model_from,
            temperature=model_cfg.get("temperature", None),
            top_p=model_cfg.get("top_p", None),
            max_tokens=model_cfg.get("max_tokens", None),
            messages=final_messages,
            tools=tools,
            tool_choice=tool_choice
        )

    @observe(
        span_type=SpanType.ToolCall,
        span_name='tool_execution',
        child_of=headers,
        process_inputs=lambda data: data['args'][2] if len(data['args']) > 0 else None)
    async def _execute_tools_and_stream(
            self,
            tool_calls_delta: List[Dict[str, Any]],
            messages: List[Dict[str, Any]],
            call_kwargs: Dict[str, Any],
            debug_id: int,  # 改为整数类型
            llm_protocol_config: Dict[str, Any],
            trace_key: str,
            mock_tools: List[Dict[str, Any]],
            debug_logs: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        current_span = trace.get_current_span()
        current_span.set_attribute('language', get_baggage('language'))
        current_span.set_attribute('debug_id', debug_id)
        current_span.set_attribute('space_id', get_baggage('space_id'))
        current_span.set_attribute('model_name', llm_protocol_config.get("model"))
        current_span.set_attribute('model.provider', llm_protocol_config.get("provider"))
        current_span.set_attribute('response.stream', True)
        """ 处理工具调用，流式返回答案 """
        messages.append(self._build_assistant_message(tool_calls_delta))

        # 2. 逐个执行函数，追加 tool 消息
        self._execute_tools(tool_calls_delta, messages, mock_tools, debug_logs)

        # 3. 第二次流式请求并 yield
        call_kwargs["messages"] = messages

        debug_logs.append({
            "timestamp": time.time(),
            "level": "info",
            "message": "开始第二次大模型调用（工具结果处理）",
            "step": "llm_second_call"
        })
        _first_response_time = None
        _start_time = time.time_ns()

        async for chk in get_llm_client_by_protocol(llm_protocol_config).stream(**call_kwargs):
            if not _first_response_time:
                _first_response_time = time.time_ns()
                latency = (_first_response_time - _start_time) // 1000000
                current_span.set_attribute('latency_first_resp', latency)
            if chk.content:
                yield f"""data: {DebugStreamingResponse(
                    delta={"content": chk.content},
                    finish_reason=None,
                    debug_id=str(debug_id),
                    debug_trace_key=trace_key,
                ).model_dump_json()}\n\n"""

        debug_logs.append({
            "timestamp": time.time(),
            "level": "info",
            "message": "第二次大模型调用完成",
            "step": "llm_second_complete"
        })

    @classmethod
    def _build_assistant_message(cls, tool_calls_delta: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建助手消息"""
        return {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": tc.get("id"),
                    "type": tc.get("type"),
                    "function": {
                        "name": tc.get("name"),
                        "arguments": tc.get("arguments"),
                    },
                }
                for tc in tool_calls_delta
            ],
        }

    def _execute_tools(
            self,
            tool_calls_delta: List[Dict[str, Any]],
            messages: List[Dict[str, Any]],
            mock_tools: List[Dict[str, Any]],
            debug_logs: List[Dict[str, Any]]
    ) -> None:
        """执行所有工具调用"""
        for tc in tool_calls_delta:
            args = json.loads(tc.get("arguments"))

            # 记录工具调用开始
            debug_logs.append({
                "timestamp": time.time(),
                "level": "info",
                "message": f"执行工具: {tc.get('name')}",
                "step": f"tool_{tc.get('name')}",
                "arguments": args
            })

            # 优先用 mock_tools，没有再退化
            result = self._get_mock_response(mock_tools, tc.get("name"))
            if callable(result):
                result = result(**args)

            # 添加工具消息
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })

            # 记录工具调用完成
            debug_logs.append({
                "timestamp": time.time(),
                "level": "info",
                "message": f"工具执行完成: {tc.get('name')}",
                "step": f"tool_{tc.get('name')}_complete",
                "result": result
            })

    def _generate_debug_id(self) -> int:
        """生成唯一的整数debug_id"""
        self._debug_id_counter += 1
        # 确保ID在合理范围内（1到2^31-1）
        return self._debug_id_counter % (2 ** 31 - 1)

    async def _save_debug_log(self, log_param: SaveDebugLogParam, debug_id: int) -> None:
        """保存调试日志到数据库"""
        try:
            # 计算执行时长
            duration = time.time() - log_param.start_time

            # 安全地获取 prompt_id，处理可能的类型转换问题
            prompt_id = log_param.prompt.get("id")
            if prompt_id is not None:
                # 尝试将 prompt_id 转换为整数，如果失败则使用字符串
                try:
                    prompt_id = int(prompt_id)
                except (ValueError, TypeError):
                    # 如果无法转换为整数，保持原样（可能是UUID字符串）
                    pass

            # 安全地获取 workspace_id
            workspace_id = log_param.prompt.get("workspace_id")
            if workspace_id is not None:
                try:
                    workspace_id = int(workspace_id)
                except (ValueError, TypeError):
                    pass

            # 安全地获取 user_id
            user_id = log_param.prompt.get("user_id", "unknown")
            if user_id is not None and user_id != "unknown":
                try:
                    user_id = int(user_id)
                except (ValueError, TypeError):
                    pass

            # 构建日志数据
            log_data = {
                "debug_id": debug_id,  # 使用整数类型的debug_id
                "prompt_id": prompt_id,
                "workspace_id": workspace_id,
                "user_id": user_id,
                "start_time": log_param.start_time,
                "end_time": time.time(),
                "duration": duration,
                "single_step_debug": log_param.single_step_debug,
                "error_message": str(log_param.error) if log_param.error else None,
                "debug_logs": log_param.debug_logs or [],
                "result": log_param.result,
                "status": "success" if not log_param.error else "failed"
            }

            # 清理数据，确保所有字段都是可序列化的
            for key, value in log_data.items():
                if value is None:
                    log_data[key] = None
                elif isinstance(value, (dict, list)):
                    # 确保嵌套结构也是可序列化的
                    log_data[key] = json.loads(json.dumps(value, default=str))

            await self.debug_log_repo.add_record(log_data)
            logger.info(f"Debug log saved successfully, debug_id: {debug_id}")

        except Exception as e:
            # 日志记录失败不应该影响主流程，但可以打印错误信息
            logger.error(f"保存调试日志失败: {e}", exc_info=True)