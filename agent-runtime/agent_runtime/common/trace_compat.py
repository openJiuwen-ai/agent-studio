# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""trace_id 传递 / LLM span 覆盖兼容层。

openjiuwen 0.1.16 的 create_workflow_session / create_agent_session 尚不接受 trace_id 参数，
待新版本已支持。本模块在 import 时检测签名，仅在底层支持时
才透传 trace_id，保证升级前后均不会报错。

build_traced_model 把裸 core Model 交给 openjiuwen 装饰器（on_llm_start /
on_llm_end，携带 usage 与 ttft），按 core 壳合并能力门控：旧 core 上探不到
OtelAgentHandler.LLM_SPAN_MERGE_CAPABILITY 时原样返回裸模型，避免
"组件壳 + 独立 llm span" 双计。
"""

from __future__ import annotations

import inspect

from jiuwen.common.log.base import get_x_request_id, logger
from openjiuwen.core.session.agent import create_agent_session as _create_agent_session
from openjiuwen.core.workflow import create_workflow_session as _create_workflow_session


# 一次性检测底层是否支持 trace_id 参数
def _accepts_trace_id(sig_params) -> bool:
    """Check if a function accepts trace_id — either as explicit param or via **kwargs."""
    if "trace_id" in sig_params:
        return True
    for p in sig_params.values():
        if p.kind == inspect.Parameter.VAR_KEYWORD:
            return True
    return False


_agent_params = inspect.signature(_create_agent_session).parameters
_wf_params = inspect.signature(_create_workflow_session).parameters
_agent_accepts_trace_id = _accepts_trace_id(_agent_params)
_wf_accepts_trace_id = _accepts_trace_id(_wf_params)


# 定义级会话"显式不绑请求 trace"的哨兵：定义级产物跨执行复用，绑定任一
# 请求的 trace 都会把后续执行的 span 错归到该请求（区别于缺省 None =
# 沿用请求上下文）。
_DEFINITION_NO_TRACE = object()


def create_agent_session_with_trace(session_id: str = None, trace_id=None, **kwargs):
    """创建 agent session，底层支持时透传 trace_id。

    trace_id 缺省（None）沿用请求上下文；显式传 ``_DEFINITION_NO_TRACE``
    表示不绑任何请求 trace（定义级会话专用）。
    """
    if trace_id is None:
        trace_id = get_x_request_id()
    if trace_id is not _DEFINITION_NO_TRACE and _agent_accepts_trace_id and trace_id:
        kwargs["trace_id"] = trace_id
    return _create_agent_session(session_id=session_id, **kwargs)


def create_workflow_session_with_trace(session_id: str = None, trace_id: str = None, **kwargs):
    """创建 workflow session，底层支持时透传 trace_id。"""
    # 优先使用显式传入的 trace_id（如 QA 恢复时从 Redis 读取的）
    if trace_id is None:
        trace_id = get_x_request_id()

    if _wf_accepts_trace_id and trace_id:
        kwargs["trace_id"] = trace_id
    return _create_workflow_session(session_id=session_id, **kwargs)


# ---------------------------------------------------------------------------
# LLM span 覆盖：裸 Model -> 装饰器（usage / ttft / 壳合并）
# ---------------------------------------------------------------------------

# 一次性探测 core 是否具备 LLM 组件壳合并能力
# （OtelAgentHandler.LLM_SPAN_MERGE_CAPABILITY，core 侧 PR 随壳合并逻辑引入）。
# 旧 core 无该类常量：装饰器发射的 on_llm_start 无法并入组件壳，同一真实调用
# 会同时出现组件壳与独立 llm span（双计）；探测不到即退回裸模型，把覆盖缺口
# 封闭在 core 升级窗口内，杜绝新旧组合下的双计。
_LLM_SHELL_MERGE_CAPABLE = None


def _llm_shell_merge_capable() -> bool:
    """core 是否具备 LLM 组件壳合并能力（结果进程内缓存）。"""
    global _LLM_SHELL_MERGE_CAPABLE
    if _LLM_SHELL_MERGE_CAPABLE is None:
        capable = False
        try:
            from openjiuwen.extensions.tracer_otel.handler import OtelAgentHandler

            capable = getattr(OtelAgentHandler, "LLM_SPAN_MERGE_CAPABILITY", None) == "1"
        except Exception:  # noqa: BLE001 - 旧 core 无 tracer_otel 扩展时按无能力处理
            capable = False
        _LLM_SHELL_MERGE_CAPABLE = capable
    return _LLM_SHELL_MERGE_CAPABLE


# 定义级产物（工作流 IR 转换出的组件/模型，跨执行复用）的会话身份：构建时
# 不存在按会话归因的真实 id，绑定任一请求的 id（含 trace_id）都会错归属，
# 故显式落此常量且不绑请求 trace；会话归因由执行期 trace 树（span 挂在
# 真实组件壳/工作流 trace 下）承担。
DEFINITION_SCOPED_SESSION_ID = "workflow-llm"


def build_traced_model(model, session=None, session_id: str = None):
    """把裸 core Model 交给 openjiuwen 装饰器，补齐每次调用的 llm span。

    - 能力门槛：core 不具备壳合并能力时原样返回裸模型（宁可无 span 不双计）；
    - ``session`` 显式传入则直接复用（当前生产调用点均传 session_id 由工厂
      建轻量会话，该参数供测试与后续接线预留）。轻量会话不触碰任何既有
      会话——OTel 父链按调用时 ambient 上下文解析（组件壳/rail span 合并，
      见 core LLM_SPAN_MERGE_CAPABILITY），与会话对象无关，不会因执行会话
      与装饰会话是两个对象而分叉 trace；
    - 轻量会话的会话身份与 trace 均不得绑定构建期请求（定义级产物跨执行
      复用，绑定任一请求都会错归属）：无显式 session_id 时落
      ``DEFINITION_SCOPED_SESSION_ID`` 且不绑请求 trace；react 这类每执行
      新建模型的请求级场景传当次会话 id，trace 沿用请求上下文；
    - 遥测侧任何失败（探测 / 导入 / 建会话 / 装饰）都降级返回裸模型，
      绝不影响模型创建与业务语义。
    """
    if not _llm_shell_merge_capable():
        return model
    try:
        from openjiuwen.core.session.tracer import decorate_model_with_trace
    except Exception as e:  # noqa: BLE001 - 旧 core 无该入口
        logger.warning("build_traced_model: decorate entry missing, bare model kept: %s", e)
        return model
    try:
        if session is None:
            resolved = session_id or get_x_request_id() or DEFINITION_SCOPED_SESSION_ID
            if resolved == DEFINITION_SCOPED_SESSION_ID:
                # 定义级产物：会话 id 与 trace 都不绑构建期请求，归因由执行期
                # ambient 壳/rail 父链承担（绑首次请求会把后续执行错归其 trace）
                session = create_agent_session_with_trace(
                    session_id=resolved, trace_id=_DEFINITION_NO_TRACE
                )
            else:
                session = create_agent_session_with_trace(session_id=resolved)
        return decorate_model_with_trace(model, session)
    except Exception as e:  # noqa: BLE001 - 遥测失败不得阻断模型创建
        logger.warning("build_traced_model: trace decoration degraded to bare model: %s", e)
        return model
