#  Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""
Flow stream transform component.

This component is designed to post-process an async stream of dict frames using
AsyncDictStreamTransformer, and emit workflow streaming events similarly to FlowMessage.

Supports two modes:
1. **Template mode** (new): Use \	emplate\ config to render each frame with Jinja2-like syntax
   - Supports {{raw_output}} for full dict
   - Supports {{raw_output.field}} for specific fields
2. **Transformer mode** (legacy): Use \	ransformer\ config with AsyncDictStreamTransformer
"""

from __future__ import annotations

import json
import re
from typing import Any, AsyncIterable, AsyncIterator, Dict, Optional

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.utils.async_dict_stream_transform import (
    AsyncDictStreamTransformConfig,
    AsyncDictStreamTransformer,
)
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.callbacks.span import Span
from jiuwen.orchestration.flow.components.util import (
    get_data_of_streaming_with_metadata,
)
from jiuwen.orchestration.flow.constant import USER_FIELDS
from jiuwen.orchestration.flow.enum import StreamDataMsg
from jiuwen.orchestration.flow.model.workflow_data_class import (
    WorkflowMetadata,
    WorkflowStreamingData,
)
from jiuwen.orchestration.flow.runtime_context import RuntimeContext
from jiuwen.orchestration.flow.stream.base import StreamCode, StreamData


class FlowStreamTransform(Invokable):
    """
    Transform an async dict stream and emit StreamData events.

    Config (snake_case recommended):
        - template: str, optional. Template string for rendering each frame.
          Supports Jinja2-like syntax: {{raw_output}} or {{raw_output.field}}.
          If provided, takes precedence over transformer config.
        - transformer: dict, optional. Transformer config passed to AsyncDictStreamTransformConfig.from_dict().
          Used when template is not provided.
        - parse_json_strings: bool, optional. If True, attempts to parse string/bytes chunks as JSON dicts.
          Default: True.
        - userFields: dict, optional. Defines input and (optional) output fields.
          - inputs: list, optional. List of input field definitions (only one input allowed).
            - id: str, optional. The field name used in inputs[USER_FIELDS]. Default: "_input".
            The input field value should be an AsyncIterable (e.g., a generator).
          - outputs: list, optional. List of output field definitions (only one output allowed).
            - id: str, optional. The field name used in outputs[USER_FIELDS]. If not provided,
              result will be assigned directly to user_fields.
    """

    def __init__(
        self, conf: dict, runtime_context: RuntimeContext, metadata: WorkflowMetadata
    ):
        super().__init__()
        self._conf = conf or {}
        self.runtime_context = runtime_context
        self.metadata = metadata

        # Check if template mode is enabled
        self._template_content: Optional[str] = self._conf.get("template")
        self._use_template_mode = bool(self._template_content)

        self._transformer_conf: dict = self._conf.get("transformer") or {}
        self._parse_json_strings: bool = bool(
            self._conf.get(
                "parse_json_strings", self._conf.get("parseJsonStrings", True)
            )
        )

        # Infer source_field and output_field from config.userFields
        user_fields_config = self._conf.get("userFields", {})

        # Infer source_field from userFields.inputs, default to "_input"
        self._source_field: str = "_input"
        user_fields_inputs = user_fields_config.get("inputs", [])
        if isinstance(user_fields_inputs, list) and len(user_fields_inputs) == 1:
            first_input = user_fields_inputs[0]
            if isinstance(first_input, dict) and "id" in first_input:
                self._source_field = first_input["id"]

        # Infer output_field from userFields.outputs, can be empty
        self._output_field: str = ""
        self._direct_assign_output: bool = (
            True  # Default: assign result directly to user_fields
        )
        user_fields_outputs = user_fields_config.get("outputs", [])
        if isinstance(user_fields_outputs, list) and len(user_fields_outputs) == 1:
            first_output = user_fields_outputs[0]
            if isinstance(first_output, dict) and "id" in first_output:
                self._output_field = first_output["id"]
                self._direct_assign_output = False

        # Only validate transformer config if not using template mode
        if not self._use_template_mode:
            if not isinstance(self._transformer_conf, dict):
                raise JiuWenBaseException(
                    error_code=StatusCode.WORKFLOW_INITIAL_CONFIG_ERROR.code,
                    message=StatusCode.WORKFLOW_INITIAL_CONFIG_ERROR.errmsg.format(
                        error_msg="'transformer' must be a dict"
                    ),
                )

    def invoke(self, inputs: Dict[str, Any], **kwargs):
        logger.info(
            "FlowStreamTransform does not support sync invoke, please use ainvoke instead"
        )
        return {}

    async def ainvoke(self, inputs: Dict[str, Any], **kwargs):
        """
        Transform stream frames and (optionally) emit StreamData to stream_callback.
        """
        stream_callback = kwargs.get("stream_callback")
        span: Optional[Span] = kwargs.get("span")
        execution_id = span.trace_id if span else ""

        user_fields = (inputs or {}).get(USER_FIELDS, {}) or {}
        origin_stream = user_fields.get(self._source_field)
        if origin_stream is None:
            return self._build_result(None)
        if not hasattr(origin_stream, "__aiter__"):
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_INITIAL_CONFIG_ERROR.code,
                message=StatusCode.WORKFLOW_INITIAL_CONFIG_ERROR.errmsg.format(
                    error_msg=f"'{self._source_field}' must be an async iterable"
                ),
            )

        # Use template mode if configured
        if self._use_template_mode:
            out_stream = self._apply_template_to_frames(origin_stream)
        else:
            # Legacy transformer mode
            cfg = AsyncDictStreamTransformConfig.from_dict(self._transformer_conf)
            transformer = AsyncDictStreamTransformer(cfg)
            out_stream = transformer.transform(self._iter_dict_frames(origin_stream))

        if stream_callback is None:
            last_frame = None
            async for frame in out_stream:
                last_frame = frame
            return self._build_result(last_frame)

        last_frame = await self._handle_streaming(
            out_stream, stream_callback, execution_id
        )
        return self._build_result(last_frame)

    def _render_template(self, template: str, variables: dict) -> str:
        """Render template with variable substitution.
        
        Supports {{variable}} and {{variable.field}} syntax.
        
        Args:
            template: Template string with placeholders
            variables: Dictionary of variables to substitute
            
        Returns:
            Rendered string with placeholders replaced
        """
        def replace_placeholder(match):
            placeholder = match.group(1).strip()
            if not placeholder:
                return match.group(0)  # Empty placeholder, return as-is
            
            # Split by dot to support nested field access
            parts = placeholder.split(".")
            value = variables
            
            try:
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    elif hasattr(value, part):
                        value = getattr(value, part)
                    else:
                        # Field not found, return empty string
                        return ""
                    
                    if value is None:
                        return ""
                
                # Convert to string
                if isinstance(value, (str, int, float, bool)):
                    return str(value)
                else:
                    # For dict/list, use JSON serialization
                    return json.dumps(value, ensure_ascii=False)
            except Exception:
                # Any error during rendering, return empty string
                return ""
        
        # Find all {{...}} placeholders and replace them
        return re.sub(r"\{\{([^{}]+)\}\}", replace_placeholder, template)

    async def _apply_template_to_frames(
        self, origin_stream: AsyncIterable
    ) -> AsyncIterator[Dict[str, Any]]:
        """Apply template rendering to each frame in the stream."""
        async for frame in self._iter_dict_frames(origin_stream):
            try:
                # Build variables dict with raw_output
                variables = {"raw_output": frame}
                
                # Render template
                rendered = self._render_template(self._template_content, variables)
                
                # Return rendered string as answer
                yield rendered
            except Exception as e:
                logger.warning(f"Failed to render template for frame: {e}")
                # Fallback to original frame if template rendering fails
                yield frame

    async def _iter_dict_frames(
        self, origin_stream: AsyncIterable
    ) -> AsyncIterator[Dict[str, Any]]:
        async for item in origin_stream:
            if isinstance(item, dict):
                yield item
                continue

            # If upstream is StreamData, extract answer if possible.
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
                    logger.warning("Failed to decode bytes to str: %s", e)
                    continue
            if isinstance(item, str):
                s = item.strip()
                if s.startswith("data:"):
                    s = s[5:].strip()
                try:
                    obj = json.loads(s)
                except Exception as e:
                    logger.warning("Failed to parse JSON string: %s", e)
                    continue
                if isinstance(obj, dict):
                    yield obj

    def _build_result(self, value: Optional[Any]) -> Dict[str, Any]:
        if self._direct_assign_output:
            return {USER_FIELDS: value}
        return {USER_FIELDS: {self._output_field: value}}

    def _format_answer(self, frame):
        """Serialize dict/list frames to JSON string for frontend display."""
        if isinstance(frame, (dict, list)):
            return json.dumps(frame, ensure_ascii=False, default=str)
        return frame

    async def _handle_streaming(
        self,
        out_stream: AsyncIterator[Any],
        stream_callback,
        execution_id: str,
    ) -> Optional[Any]:
        stream_related_info = WorkflowStreamingData(
            stream_callback=stream_callback, execution_id=execution_id
        )
        idx = 0
        prev: Optional[Any] = None

        async for frame in out_stream:
            if prev is not None:
                await stream_related_info.stream_callback.on_recv(
                    StreamData(
                        code=StreamCode.PARTIAL_CONTENT.value,
                        msg=StreamDataMsg.SUCCESS.value,
                        data=get_data_of_streaming_with_metadata(
                            answer=self._format_answer(prev), metadata=self.metadata
                        ),
                        execution_id=stream_related_info.execution_id,
                        index=idx,
                    )
                )
                idx += 1
            prev = frame

        if prev is not None:
            await stream_related_info.stream_callback.on_recv(
                StreamData(
                    code=StreamCode.MESSAGE_END.value,
                    msg=StreamDataMsg.MESSAGE_END.value,
                    data=get_data_of_streaming_with_metadata(
                        answer=self._format_answer(prev), metadata=self.metadata
                    ),
                    execution_id=stream_related_info.execution_id,
                    index=idx,
                )
            )
        return prev
