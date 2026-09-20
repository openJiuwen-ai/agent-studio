# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

"""
FlowStreamTransform - 流式转换组件

迁移自 jiuwen/orchestration/flow/components/flow_stream_transform.py，
适配 openjiuwen 框架。

功能特性:
- 使用 AsyncDictStreamTransformer 对异步字典流进行后处理转换
- 支持流式输出 StreamData 事件
- 支持从 dict/StreamData/JSON 字符串等多种格式解析输入帧
- 支持配置输入/输出字段映射

设计说明:
- 继承 WorkflowComponent（openjiuwen 标准组件基类）
- 使用 invoke 方法执行流式转换
- 使用 session.write_stream() 输出流式数据
- 使用 OutputSchema 作为流式数据结构
"""

import json
from dataclasses import replace as _dc_replace
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Dict,
    Optional,
    Union,
)

from jiuwen.extension.workflow_node.utils import (
    AsyncDictStreamTransformConfig,
    AsyncDictStreamTransformer,
    JiuWenBaseException,
    WorkflowMetadata,
)
from openjiuwen.core.common.logging import workflow_logger, LogEventType
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.session.stream import OutputSchema
from openjiuwen.core.workflow.components.component import WorkflowComponent

USER_FIELDS = "userFields"

STREAM_TYPE_PARTIAL_CONTENT = "end node stream"
STREAM_TYPE_MESSAGE_END = "message_end"


class FlowStreamTransformStatusCode:
    """FlowStreamTransform 组件专用错误码"""

    CONFIG_ERROR = (
        101170,
        "flow_stream_transform config error, reason: {error_msg}",
    )
    INPUT_INVALID = (
        101171,
        "flow_stream_transform input invalid, reason: {error_msg}",
    )
    TRANSFORMER_CONFIG_ERROR = (
        101172,
        "flow_stream_transform transformer config error, reason: {error_msg}",
    )


def build_flow_stream_transform_error(
    error_code: int,
    message: str,
) -> JiuWenBaseException:
    """构建 FlowStreamTransform 组件异常

    Args:
        error_code: 错误代码
        message: 错误信息

    Returns:
        JiuWenBaseException 实例
    """
    return JiuWenBaseException(
        error_code=error_code,
        message=message,
    )


def get_data_of_streaming_with_metadata(
    answer: Union[str, Dict[str, Any]],
    metadata: WorkflowMetadata,
    outputs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """封装流式输出的结果，包括原始输出、节点ID、节点类型

    Args:
        answer: 输出内容
        metadata: 工作流元数据
        outputs: 用户字段输出

    Returns:
        封装后的流式输出数据
    """
    base: Dict[str, Any] = {
        "answer": answer,
        "node_id": metadata.node_id,
        "node_name": metadata.node_name,
        "node_type": metadata.node_type,
        "should_interrupt": metadata.should_interrupt,
    }
    if outputs:
        base["outputs"] = {USER_FIELDS: outputs}
    return base


class FlowStreamTransform(WorkflowComponent):
    """
    流式转换组件

    使用 AsyncDictStreamTransformer 对异步字典流进行后处理转换，
    并发出工作流流式事件（OutputSchema）。

    Args:
        conf: 组件配置字典，包含以下字段：
            - transformer: dict, 必需。传递给 AsyncDictStreamTransformConfig 的配置
            - parse_json_strings: bool, 可选。是否解析 JSON 字符串，默认 True
            - userFields: dict, 可选。定义输入和输出字段
                - inputs: list, 可选。输入字段定义（仅允许一个输入）
                    - id: str, 可选。输入字段名，默认 "_input"
                - outputs: list, 可选。输出字段定义（仅允许一个输出）
                    - id: str, 可选。输出字段名
        metadata: 工作流元数据，包含 node_id, node_type, node_name
    """

    def __init__(self, conf: dict, metadata: WorkflowMetadata) -> None:
        super().__init__()
        self._conf = conf or {}
        self.metadata = metadata

        self._transformer_conf: dict = self._conf.get("transformer") or {}
        self._parse_json_strings: bool = bool(
            self._conf.get(
                "parse_json_strings", self._conf.get("parseJsonStrings", True)
            )
        )

        user_fields_config = self._conf.get("userFields", {})

        self._source_field: str = "_input"
        user_fields_inputs = user_fields_config.get("inputs", [])
        if isinstance(user_fields_inputs, list) and len(user_fields_inputs) == 1:
            first_input = user_fields_inputs[0]
            if isinstance(first_input, dict) and "id" in first_input:
                self._source_field = first_input["id"]

        self._output_field: str = ""
        self._direct_assign_output: bool = True
        user_fields_outputs = user_fields_config.get("outputs", [])
        if isinstance(user_fields_outputs, list) and len(user_fields_outputs) == 1:
            first_output = user_fields_outputs[0]
            if isinstance(first_output, dict) and "id" in first_output:
                self._output_field = first_output["id"]
                self._direct_assign_output = False

        if not isinstance(self._transformer_conf, dict):
            raise build_flow_stream_transform_error(
                error_code=FlowStreamTransformStatusCode.CONFIG_ERROR[0],
                message=FlowStreamTransformStatusCode.CONFIG_ERROR[1].format(
                    error_msg="'transformer' must be a dict"
                ),
            )

    def _build_transformer_config(self) -> AsyncDictStreamTransformConfig:
        """Build transformer config, binding the input param name to the whole frame.

        When a frame_template placeholder matches the input parameter name
        (e.g. ``{{raw_output}}`` while the input param id is ``raw_output``),
        its variable ``src_path`` is cleared so that ``_read_src`` returns the
        entire frame instead of looking up a sub-field. This lets users
        reference the complete input object without splitting it into
        ``{{raw_output.a}}``/``{{raw_output.b}}``.
        """
        cfg = AsyncDictStreamTransformConfig.from_dict(self._transformer_conf)
        if not self._source_field:
            return cfg
        new_vars = [
            # Only clear src_path when it is the default value (src_path == name),
            # to support whole-frame reference like {{{{raw_output}}}}.
            # If user explicitly configures src_path to a different value,
            # respect their configuration.
            _dc_replace(v, src_path="") if (v.name == self._source_field and v.src_path == v.name) else v
            for v in cfg.variables
        ]
        return _dc_replace(cfg, variables=new_vars)

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """执行流式转换

        Args:
            inputs: 输入数据
            session: 工作流会话
            context: 模型上下文

        Returns:
            Output: 输出结果
        """
        workflow_logger.info(
            "FlowStreamTransform invoke started",
            event_type=LogEventType.WORKFLOW_COMPONENT_START,
            component_id=session.get_component_id(),
            component_type_str="FlowStreamTransform",
            metadata={
                "source_field": self._source_field,
                "output_field": self._output_field,
            },
        )

        user_fields = (inputs or {}).get(USER_FIELDS, {}) or {}
        origin_stream = user_fields.get(self._source_field)

        if origin_stream is None:
            workflow_logger.info(
                "FlowStreamTransform: source stream is None, returning empty result",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_id=session.get_component_id(),
                component_type_str="FlowStreamTransform",
            )
            return self._build_result(None)

        if not hasattr(origin_stream, "__aiter__"):
            # Handle plain string input (e.g. from batch path where streaming
            # output was concatenated into a single string)
            if isinstance(origin_stream, str):
                async def _string_to_async_gen(s):
                    yield s
                origin_stream = _string_to_async_gen(origin_stream)
            else:
                raise build_flow_stream_transform_error(
                    error_code=FlowStreamTransformStatusCode.INPUT_INVALID[0],
                    message=FlowStreamTransformStatusCode.INPUT_INVALID[1].format(
                        error_msg=f"'{self._source_field}' must be an async iterable or string"
                    ),
                )

        try:
            cfg = self._build_transformer_config()
        except Exception as e:
            raise build_flow_stream_transform_error(
                error_code=FlowStreamTransformStatusCode.TRANSFORMER_CONFIG_ERROR[0],
                message=FlowStreamTransformStatusCode.TRANSFORMER_CONFIG_ERROR[
                    1
                ].format(error_msg=str(e)),
            ) from e

        transformer = AsyncDictStreamTransformer(cfg)
        out_stream = transformer.transform(self._iter_dict_frames(origin_stream))

        last_frame = await self._handle_streaming(out_stream, session)

        workflow_logger.info(
            "FlowStreamTransform invoke completed",
            event_type=LogEventType.WORKFLOW_COMPONENT_END,
            component_id=session.get_component_id(),
            component_type_str="FlowStreamTransform",
        )

        return self._build_result(last_frame)

    async def _iter_dict_frames(
        self, origin_stream: AsyncIterable
    ) -> AsyncIterator[Dict[str, Any]]:
        """迭代字典帧，处理多种输入格式

        Args:
            origin_stream: 原始流数据

        Yields:
            Dict[str, Any]: 字典帧
        """
        async for item in origin_stream:
            # Handle OutputSchema objects from plugin streaming
            if hasattr(item, "payload") and isinstance(getattr(item, "payload", None), dict):
                _ans = item.payload.get("answer")
                item = _ans if _ans is not None else item.payload
            if isinstance(item, dict):
                yield item
                continue

            if hasattr(item, "data") and isinstance(getattr(item, "data", None), dict):
                ans = item.data.get("answer")
                if isinstance(ans, dict):
                    yield ans
                    continue
                if isinstance(ans, (str, bytes)):
                    item = ans

            if not self._parse_json_strings:
                continue

            if isinstance(item, bytes):
                try:
                    item = item.decode("utf-8", errors="strict")
                except Exception as e:
                    workflow_logger.warning("Failed to decode bytes to str: %s", e)
                    continue

            if isinstance(item, str):
                s = item.strip()
                if s.startswith("data:"):
                    s = s[5:].strip()
                try:
                    decoder = json.JSONDecoder()
                    pos = 0
                    while pos < len(s):
                        while pos < len(s) and s[pos] in " \t\r\n":
                            pos += 1
                        if pos >= len(s):
                            break
                        obj, end_pos = decoder.raw_decode(s, pos)
                        pos = end_pos
                        if isinstance(obj, dict):
                            yield obj
                except Exception:
                    remainder = s[pos:]
                    try:
                        import ast
                        obj = ast.literal_eval(remainder)
                        if isinstance(obj, dict):
                            yield obj
                        elif isinstance(obj, str):
                            yield {"answer": obj}
                    except (ValueError, SyntaxError):
                        if remainder:
                            yield {"answer": remainder}
                    workflow_logger.debug("JSON parse failed, used ast fallback: %s", remainder[:100])

    def _build_result(self, value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """构建返回结果

        Args:
            value: 输出值

        Returns:
            Dict[str, Any]: 返回结果
        """
        if self._direct_assign_output:
            return {USER_FIELDS: value}
        return {USER_FIELDS: {self._output_field: value}}

    async def _handle_streaming(
        self,
        out_stream: AsyncIterator[Dict[str, Any]],
        session: Session,
    ) -> Optional[Dict[str, Any]]:
        """处理流式输出

        Args:
            out_stream: 转换后的输出流
            session: 工作流会话

        Returns:
            Optional[Dict[str, Any]]: 最后一帧数据
        """
        idx = 0
        prev: Optional[Dict[str, Any]] = None

        async for frame in out_stream:
            if prev is not None:
                await session.write_stream(
                    OutputSchema(
                        type=STREAM_TYPE_PARTIAL_CONTENT,
                        index=idx,
                        payload=get_data_of_streaming_with_metadata(
                            answer=prev, metadata=self.metadata
                        ),
                    )
                )
                idx += 1
            prev = frame

        if prev is not None:
            await session.write_stream(
                OutputSchema(
                    type=STREAM_TYPE_MESSAGE_END,
                    index=idx,
                    payload=get_data_of_streaming_with_metadata(
                        answer=prev, metadata=self.metadata
                    ),
                )
            )
        return prev

    async def collect(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        """
        流式输入聚合为批量输出。

        旧框架中 StreamTransform 在 _pre_process 被豁免生成器预解析
        （与 End、Message、Card 同组），直接接收上游组件的 AsyncGenerator 输出。
        此方法将流式输入聚合后委托给 invoke() 进行流式转换。
        """
        resolved = await self._resolve_stream_inputs(inputs)
        return await self.invoke(resolved, session, context)

    async def transform(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> AsyncIterator[Output]:
        """
        流式输入转换为流式输出。

        当 StreamTransform 同时作为流式接收端和流式发送端时
        （如 LLM → StreamTransform → End(isStreamOut)），
        auto_complete_abilities 授予 TRANSFORM 能力。
        此方法聚合流式输入，逐帧转换后 yield OutputSchema 给下游。
        """
        # Do NOT consume AsyncGenerator - keep it alive for per-frame processing
        if not isinstance(inputs, dict):
            # Non-dict inputs (e.g. bare AsyncGenerator): delegate to invoke path
            resolved = await self._resolve_stream_inputs(inputs)
            result = await self.invoke(resolved, session, context)
            if result is not None:
                yield result
            return
        user_fields = (inputs or {}).get(USER_FIELDS, {}) or {}
        origin_stream = user_fields.get(self._source_field)

        if origin_stream is None:
            return

        if not hasattr(origin_stream, "__aiter__"):
            if isinstance(origin_stream, str):
                async def _str_to_gen(s):
                    yield s
                origin_stream = _str_to_gen(origin_stream)
            else:
                raise build_flow_stream_transform_error(
                    error_code=FlowStreamTransformStatusCode.INPUT_INVALID[0],
                    message=FlowStreamTransformStatusCode.INPUT_INVALID[1].format(
                        error_msg=f"'{self._source_field}' must be an async iterable or string"
                    ),
                )

        try:
            cfg = self._build_transformer_config()
        except Exception as e:
            raise build_flow_stream_transform_error(
                error_code=FlowStreamTransformStatusCode.TRANSFORMER_CONFIG_ERROR[0],
                message=FlowStreamTransformStatusCode.TRANSFORMER_CONFIG_ERROR[
                    1
                ].format(error_msg=str(e)),
            ) from e

        transformer = AsyncDictStreamTransformer(cfg)
        out_stream = transformer.transform(self._iter_dict_frames(origin_stream))

        idx = 0
        prev = None
        async for frame in out_stream:
            if prev is not None:
                yield OutputSchema(
                    type=STREAM_TYPE_PARTIAL_CONTENT,
                    index=idx,
                    payload=get_data_of_streaming_with_metadata(
                        answer=prev, metadata=self.metadata
                    ),
                )
                idx += 1
            prev = frame

        if prev is not None:
            yield OutputSchema(
                type=STREAM_TYPE_MESSAGE_END,
                index=idx,
                payload=get_data_of_streaming_with_metadata(
                    answer=prev, metadata=self.metadata
                ),
            )

    @staticmethod
    async def _resolve_stream_inputs(inputs: Input) -> dict:
        """
        将 inputs 中的 AsyncGenerator 值解析为最终内容。

        当上游组件（如 LLM）通过流式连接输出时，inputs 中对应的变量值
        是 AsyncGenerator 对象。此方法迭代所有 AsyncGenerator 并聚合为最终文本。
        """
        if inputs is None:
            return {}
        if not isinstance(inputs, dict):
            if hasattr(inputs, "__aiter__"):
                collected = []
                async for chunk in inputs:
                    if isinstance(chunk, dict):
                        collected.append(chunk)
                if not collected:
                    return {}
                return collected[-1] if len(collected) > 1 else collected[0]
            return {}
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, AsyncGenerator):
                chunks = []
                async for frame in value:
                    if isinstance(frame, str):
                        chunks.append(frame)
                    elif isinstance(frame, dict):
                        resp = frame.get("response", frame.get("answer", ""))
                        if resp:
                            chunks.append(str(resp))
                    else:
                        chunks.append(str(frame))
                resolved[key] = "".join(chunks)
            else:
                resolved[key] = value
        return resolved
