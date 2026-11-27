# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""OtelWorkflowHandler 的本仓扩展：HTTP/API 节点业务失败标红（Jaeger 可见）。

为什么在 agent-studio 侧继承覆写：openjiuwen 上游 handler 不识别
business_error 标记（组件正常返回但该次调用失败，如 HTTP 4xx/5xx），因此
该场景在 Jaeger 上无错误显示。span 的写权限只在 handler，而 handler 的
实例化/注册点在本仓（agent_runtime/observability/tracer_otel.py），故通过
子类在 agent-studio 侧提供等价能力，openjiuwen 源码零改动（零上游依赖）。

实现要点：
- on_invoke（非异常分支）：识别 business_error 标记 → span 置 ERROR 并记录
  错误信息（只标故障事实轴，不改 openjiuwen.status 业务状态）；
- on_call_done：span 已处于 ERROR（business_error 标记或 trace_error 异常路径）
  时保留标红，不为 OK；正常完成（UNSET）才置 OK。

版本绑定与升级核对（重要）：本文件与 openjiuwen 版本强绑定——
1. on_call_done 为整段覆写（上游无扩展点），方法体复制自
   openjiuwen handler.on_call_done；
2. 依赖上游私有符号：_extract_retrieval_documents、_is_retrieval_component_span、
   _span_manager / _refresh_inputs_attribute / _flush_buffered_data /
   _set_workflow_end_attrs / _detach_state / _layer_root_spans / _component_spans。
升级 openjiuwen 时须按清单核对：①上述私有符号是否存在/改名；②on_call_done 上游
是否新增收尾逻辑（清理/属性写入）需同步；③以 tests/unit_tests/observability/
test_tracer_otel_studio.py 全量回归兜底；符号缺失时 tracer_otel.setup_otel_tracer
会回退官方 handler（见 tracer_otel.py），保证不静默停用 OTel。
"""

import json

from opentelemetry.trace import Status, StatusCode

from openjiuwen.core.common.logging import session_logger
from openjiuwen.core.session.tracer.data import NodeStatus
from openjiuwen.extensions.tracer_otel.handler import (
    OtelWorkflowHandler,
    _extract_retrieval_documents,
    _is_retrieval_component_span,
)
from openjiuwen.extensions.tracer_otel.redaction import redact
from openjiuwen.extensions.tracer_otel.semconv import (
    GEN_AI_RETRIEVAL_DOCUMENTS,
    OJ_STATUS,
    OJ_WORKFLOW_ERROR_MESSAGE,
    OJ_WORKFLOW_OUTPUTS,
)

# 业务失败标记使用的 span 属性键（与 HTTP 业务失败上报方约定的键名一致）
OJ_BUSINESS_ERROR = "openjiuwen.workflow.business_error"


class StudioOtelWorkflowHandler(OtelWorkflowHandler):
    """在官方 OtelWorkflowHandler 基础上支持 business_error 业务失败标红。"""

    async def on_invoke(
        self,
        invoke_id: str,
        on_invoke_data: dict = None,
        exception: Exception = None,
        **kwargs,
    ):
        await super().on_invoke(
            invoke_id,
            on_invoke_data=on_invoke_data,
            exception=exception,
            **kwargs,
        )
        if (
            exception is None
            and isinstance(on_invoke_data, dict)
            and "business_error" in on_invoke_data
        ):
            self._mark_business_error(invoke_id, on_invoke_data["business_error"])

    async def on_call_done(self, invoke_id: str, outputs=None, **kwargs):
        try:
            state = self._span_manager.get(invoke_id)
            if state is not None and state.recorded:
                self._refresh_inputs_attribute(invoke_id)
                self._flush_buffered_data(invoke_id)

            state = self._span_manager.pop(invoke_id)
            if state is None:
                return

            if state.recorded:
                if outputs is not None:
                    state.span.set_attribute(
                        OJ_WORKFLOW_OUTPUTS, redact(outputs, self._config)
                    )
                    if _is_retrieval_component_span(state.span):
                        documents = _extract_retrieval_documents(outputs)
                        if documents is not None:
                            state.span.set_attribute(
                                GEN_AI_RETRIEVAL_DOCUMENTS,
                                [redact(doc, self._config) for doc in documents],
                            )

                self._set_workflow_end_attrs(state)
                state.span.set_attribute(OJ_STATUS, NodeStatus.FINISH.value)
                # 故障事实轴：span 已处于 ERROR（business_error 标记或 trace_error
                # 异常路径）时保留标红，不覆盖；仅在正常完成（UNSET）时置 OK。
                # 业务状态属性仍为 finish（业务结果轴），两轴并存互不覆盖。
                if state.span.status.status_code != StatusCode.ERROR:
                    state.span.set_status(Status(StatusCode.OK))
            state.span.end()
            self._detach_state(state)

            # Remove from mappings
            self._layer_root_spans.pop(invoke_id, None)
            self._component_spans.pop(invoke_id, None)
            root_state = self._layer_root_spans.get("")
            if root_state is state:
                self._layer_root_spans.pop("", None)
        except Exception as exc:
            session_logger.warning("otel workflow handler: on_call_done failed: %s", exc)

    def _mark_business_error(self, invoke_id: str, business_error: dict) -> None:
        """组件正常返回但该次调用失败（如 HTTP 4xx/5xx）：span 标红并保留错误信息。

        仅改故障事实轴（span.status=ERROR），不改变 openjiuwen.status 等
        业务状态属性（仍由引擎按正常完成记为 finish），流程与输出不受影响。
        """
        state = self._span_manager.get(invoke_id)
        if state is None or not state.recorded:
            return
        message = str(business_error)
        if isinstance(business_error, dict):
            code = business_error.get("status_code") or business_error.get("error_code")
            reason = business_error.get("reason")
            body = business_error.get("body")
            parts = []
            if code is not None:
                parts.append(f"status code {code}")
            if reason:
                parts.append(str(reason))
            if body:
                parts.append(str(body)[:300])
            if parts:
                message = "HTTP request failed: " + ", ".join(parts)
        state.span.set_status(Status(StatusCode.ERROR))
        # 与 on_call_done 对 outputs 的处理对齐：经 redact 脱敏（开启时哈希）并
        # 受 max_attr_length 限制，避免 body/url 等敏感信息明文落库。
        state.span.set_attribute(OJ_WORKFLOW_ERROR_MESSAGE, redact(message, self._config))
        try:
            safe_business_error = json.dumps(business_error, ensure_ascii=False)
        except (TypeError, ValueError):
            # 非 JSON 可序列化内容（bytes/异常对象等）兜底为字符串，避免观测链路抛错
            safe_business_error = str(business_error)
        state.span.set_attribute(
            OJ_BUSINESS_ERROR,
            redact(safe_business_error, self._config),
        )