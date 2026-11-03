# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.

"""模板转换节点：用 Jinja2 沙箱把上游变量渲染成一段文本。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Union

from agent_runtime.extension.workflow_node.flow_code import _coerce_inputs
from agent_runtime.extension.workflow_node.template_jinja import TemplateRenderError, render_jinja
from openjiuwen.core.common.constants.constant import USER_FIELDS
from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import build_error
from openjiuwen.core.common.logging import LogEventType, workflow_logger
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow.components.component import WorkflowComponent

JIUWEN_TEMPLATE_TRANSFORM_TYPE = "jiuwen.templateTransform"
OUTPUT_KEY = "output"


@dataclass
class FlowTemplateTransformConfig:
    template: str = ""
    user_fields: dict = field(default_factory=dict)


class FlowTemplateTransform(WorkflowComponent):
    """工作流模板转换节点。输入变量来自上游，输出固定为 output: string。"""

    def __init__(self, conf: Union[FlowTemplateTransformConfig, dict, None] = None):
        super().__init__()
        self._conf: Optional[FlowTemplateTransformConfig] = None
        if conf is not None:
            self._init_conf(conf)

    def _init_conf(self, conf: Union[FlowTemplateTransformConfig, dict]) -> None:
        try:
            if isinstance(conf, dict):
                self._conf = FlowTemplateTransformConfig(
                    template=conf.get("template", "") or "",
                    user_fields=conf.get("userFields", {}) or {},
                )
            else:
                self._conf = conf
        except Exception as exc:
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_SCHEMA_INVALID,
                comp_id="flow_template_transform",
                reason=str(exc),
                workflow="n/a",
                cause=exc,
            ) from exc

        if not isinstance(self._conf.template, str) or not self._conf.template.strip():
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_SCHEMA_INVALID,
                comp_id="flow_template_transform",
                reason="template must be a non-empty string",
                workflow="n/a",
            )

    def init(self, conf=None, **kwargs):
        if conf is not None:
            self._init_conf(conf)
        super().init(**kwargs)

    def component_type(self) -> str:
        return JIUWEN_TEMPLATE_TRANSFORM_TYPE

    async def invoke(self, inputs: Input, session: Session, context: ModelContext) -> Output:
        try:
            workflow_logger.debug(
                "FlowTemplateTransform component invoke started",
                event_type=LogEventType.WORKFLOW_COMPONENT_START,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_TEMPLATE_TRANSFORM_TYPE,
                session_id=session.get_session_id(),
            )
            user_fields = inputs.get(USER_FIELDS, inputs) if inputs else {}
            inputs_schema = self._conf.user_fields.get("inputs", []) if self._conf.user_fields else []
            if inputs_schema and isinstance(user_fields, dict):
                user_fields = _coerce_inputs(user_fields, inputs_schema)
            rendered = render_jinja(self._conf.template, user_fields if isinstance(user_fields, dict) else {})
            workflow_logger.debug(
                "FlowTemplateTransform component invoke succeeded",
                event_type=LogEventType.WORKFLOW_COMPONENT_END,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_TEMPLATE_TRANSFORM_TYPE,
                session_id=session.get_session_id(),
            )
            return {USER_FIELDS: {OUTPUT_KEY: rendered}}
        except Exception as exc:
            workflow_logger.error(
                "FlowTemplateTransform invoke failed",
                event_type=LogEventType.WORKFLOW_COMPONENT_ERROR,
                component_id=session.get_component_id(),
                component_type_str=JIUWEN_TEMPLATE_TRANSFORM_TYPE,
                session_id=session.get_session_id(),
                exception=exc,
            )
            raise build_error(
                StatusCode.WORKFLOW_COMPONENT_EXECUTION_ERROR,
                comp=session.get_component_id(),
                ability="invoke",
                reason=str(exc),
                workflow=session.get_workflow_id(),
                cause=exc,
            ) from exc

    async def stream(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> AsyncIterator[Output]:
        yield await self.invoke(inputs, session, context)


__all__ = [
    "FlowTemplateTransform",
    "FlowTemplateTransformConfig",
    "JIUWEN_TEMPLATE_TRANSFORM_TYPE",
    "render_jinja",
    "TemplateRenderError",
]
