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


def create_agent_session_with_trace(session_id: str = None, **kwargs):
    """创建 agent session，底层支持时透传 trace_id。"""
    trace_id = get_x_request_id()
    if _agent_accepts_trace_id and trace_id:
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
# 不存在按会话归因的真实 id，绑定任一请求的 id 都会错归属，故显式落此常量；
# 会话归因由执行期 trace 树（span 挂在真实组件壳/工作流 trace 下）承担。
DEFINITION_SCOPED_SESSION_ID = "workflow-llm"


def build_traced_model(model, session=None, session_id: str = None):
    """把裸 core Model 交给 openjiuwen 装饰器，补齐每次调用的 llm span。

    - 能力门槛：core 不具备壳合并能力时原样返回裸模型（宁可无 span 不双计）；
    - ``session`` 已有（如 react 执行会话）则直接复用其父链；否则按
      ModelWrapper 既有范式新建轻量 agent session（trace_id 走请求上下文），
      不触碰任何既有会话；
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
            session = create_agent_session_with_trace(
                session_id=session_id or get_x_request_id() or DEFINITION_SCOPED_SESSION_ID
            )
        return decorate_model_with_trace(model, session)
    except Exception as e:  # noqa: BLE001 - 遥测失败不得阻断模型创建
        logger.warning("build_traced_model: trace decoration degraded to bare model: %s", e)
        return model
