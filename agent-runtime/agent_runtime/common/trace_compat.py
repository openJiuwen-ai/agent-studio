# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""trace_id 传递 / LLM span 覆盖兼容层。

openjiuwen 0.1.16 的 create_workflow_session / create_agent_session 尚不接受 trace_id 参数，
待新版本已支持。本模块在 import 时检测签名，仅在底层支持时
才透传 trace_id，保证升级前后均不会报错。

build_traced_model 把裸 core Model 交给 openjiuwen 装饰器（on_llm_start /
on_llm_end，携带 usage 与 ttft）。identity 通道（get_model / 装饰器的
identity 参数）按 core 能力门控：callable_accepts_kwarg 一次性签名探测，
旧 core 不支持时退既有两参调用形态——新旧 studio × 新旧 core 四象限最差
维持现状、绝不崩；遥测侧运行期失败仍整体降级返回裸模型（不阻断模型创建）。
"""

from __future__ import annotations

import inspect
from contextvars import ContextVar

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


# core 能力探测缓存：底层函数对象 → 是否接受某关键字参数。绑定方法先归一
# 到 __func__（每次属性访问都会生成新绑定对象，不归一缓存永远打不中）。
_KWARG_SUPPORT_CACHE: dict = {}


def callable_accepts_kwarg(func, name: str) -> bool:
    """一次性探测 callable 是否接受关键字参数 name（显式参数或 **kwargs）。

    新旧 core 混布的守门人：旧 core 的 get_model / 装饰器签名没有
    identity 参数且无 **kwargs，带上传即 TypeError。不支持时调用方退
    既有参数形态——最差维持现状，绝不崩。签名不可得时保守返回 False。
    """
    func = getattr(func, "__func__", func)
    key = (func, name)
    cached = _KWARG_SUPPORT_CACHE.get(key)
    if cached is None:
        try:
            params = inspect.signature(func).parameters
            param = params.get(name)
            cached = (
                param is not None
                and param.kind
                in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
            ) or any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
            )
        except (TypeError, ValueError):
            cached = False
        _KWARG_SUPPORT_CACHE[key] = cached
    return cached


# 本次运行的用户事实：runner 建会话时随 source_metadata 播种（req.user_id）。
# 仅在有值时 set、绝不 clear——后续 per-call 轻量会话不带 source_metadata，
# 不得抹掉已播种值；读取方：core rail 自读 session（react 引擎路径）、
# ModelWrapper._trace_identity_kwargs 兜底（装饰器路径 handler 只认 identity）。
_CURRENT_USER_ID = ContextVar("oj_current_user_id", default=None)


def current_user_id():
    """当前运行的用户 id（runner 播种；未播种返回 None）。"""
    return _CURRENT_USER_ID.get()


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

    ``source_metadata``（core 基线参数，2026-03 起）原样透传；携带
    ``user_id`` 时同步记录到 ``_CURRENT_USER_ID``（runner 建会话处播种，
    rail 路径 core 自读 session、装饰器路径 ModelWrapper 兜底取用）。
    """
    source_metadata = kwargs.get("source_metadata") or {}
    user_id = source_metadata.get("user_id")
    if user_id:
        _CURRENT_USER_ID.set(str(user_id))
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
# LLM span 覆盖：裸 Model -> 装饰器（usage / ttft 测量）
# ---------------------------------------------------------------------------

# 定义级产物（工作流 IR 转换出的组件/模型，跨执行复用）的会话身份：构建时
# 不存在按会话归因的真实 id，绑定任一请求的 id（含 trace_id）都会错归属，
# 故显式落此常量且不绑请求 trace；会话归因由执行期 trace 树（span 挂在
# 真实组件壳/工作流 trace 下）承担。
DEFINITION_SCOPED_SESSION_ID = "workflow-llm"


def workflow_identity_from_session(session) -> dict | None:
    """从 openjiuwen Session 提取工作流身份（workflow_id）。

    正常执行 Session.get_workflow_id() 返回业务工作流 id（workflow.py 落卡
    片 id）；单组件调试的 Session 以 node_id 充当 workflow_id，业务 id 需由
    调试构建路径显式注入（见 resolve_trace_identity 的 ``_trace_identity``）。

    只提取 workflow_id：component_* 身份键刻意不提取——openjiuwen.workflow.
    component_id 是后端区分组件壳 span 的判别键，内层 llm span 带上它会让
    去重规则误判；组件级归因走 metadata。
    任何读取失败返回 None，绝不抛出。
    """
    try:
        workflow_id = session.get_workflow_id() if session is not None else None
    except Exception:  # noqa: BLE001 - 身份提取失败不构成遥测失败
        return None
    if workflow_id:
        return {"workflow_id": str(workflow_id)}
    return None


def resolve_trace_identity(component, session=None) -> dict | None:
    """组件级 LLM 归因身份解析：显式注入优先，缺省从执行期 Session 提取。

    - ``component._trace_identity``：构建路径显式注入的业务身份（单组件调试
      场景——Session 的 workflow_id 是 node_id，业务 workflowId 只存在于 IR，
      由 create_single_component_info 在构建期挂上）；
    - 否则 ``workflow_identity_from_session``：执行期 Session 的业务工作流 id
      （懒初始化组件首调时 Session 已在手上）。
    """
    explicit = getattr(component, "_trace_identity", None)
    if explicit:
        return explicit
    effective = session if session is not None else getattr(component, "_session", None)
    return workflow_identity_from_session(effective)


def build_traced_model(model, session=None, session_id: str = None, identity: dict = None):
    """把裸 core Model 交给 openjiuwen 装饰器，补齐每次调用的 llm span。

    - ``session`` 显式传入则直接复用（当前生产调用点均传 session_id 由工厂
      建轻量会话，该参数供测试与后续接线预留）。轻量会话不触碰任何既有
      会话——OTel 父链按调用时 ambient 上下文解析（组件壳/rail span 下的
      真实子 span），与会话对象无关，不会因执行会话与装饰会话是两个对象
      而分叉 trace；层间双计由后端 "优先计子、无子再计桥" 规则去重；
    - 轻量会话的会话身份与 trace 均不得绑定构建期请求（定义级产物跨执行
      复用，绑定任一请求都会错归属）：无显式 session_id 时落
      ``DEFINITION_SCOPED_SESSION_ID`` 且不绑请求 trace；每执行新建模型的
      请求级场景传当次会话 id，trace 沿用请求上下文；
    - ``identity`` 透传业务归因键（workflow_id / agent_id / request_params /
      message_count / 会话事实 / ...，core 侧 write-if-absent 盖属性）：
      独立/子 llm span 带上业务身份与调用事实；旧 core 装饰器无 identity
      参数时按能力门控退两参调用（普通 llm span，不退裸模型）；
    - 遥测侧任何失败（导入 / 建会话 / 装饰）都降级返回裸模型，
      绝不影响模型创建与业务语义。
    """
    try:
        from openjiuwen.core.session.tracer import decorate_model_with_trace
    except Exception as e:  # noqa: BLE001 - core 无该入口
        logger.warning("build_traced_model: decorate entry missing, bare model kept: %s", e)
        return model
    try:
        if session is None:
            # 无显式 session_id 一律落定义级：不得退 x-request-id——定义级模型
            # 跨执行复用，绑构建期请求会把后续执行错归该请求的 trace/会话。
            resolved = session_id or DEFINITION_SCOPED_SESSION_ID
            if resolved == DEFINITION_SCOPED_SESSION_ID:
                # 定义级产物：会话 id 与 trace 都不绑构建期请求，归因由执行期
                # ambient 壳/rail 父链承担（绑首次请求会把后续执行错归其 trace）
                session = create_agent_session_with_trace(
                    session_id=resolved, trace_id=_DEFINITION_NO_TRACE
                )
            else:
                session = create_agent_session_with_trace(session_id=resolved)
        # 能力门控：旧 core 装饰器无 identity 参数——退两参调用仍产出普通
        # llm span（不退裸模型、不刷告警），新 studio × 旧 core 最差=现状
        if identity and callable_accepts_kwarg(decorate_model_with_trace, "identity"):
            return decorate_model_with_trace(model, session, identity=identity)
        return decorate_model_with_trace(model, session)
    except Exception as e:  # noqa: BLE001 - 遥测失败不得阻断模型创建
        logger.warning("build_traced_model: trace decoration degraded to bare model: %s", e)
        return model
