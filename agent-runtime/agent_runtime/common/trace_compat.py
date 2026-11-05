# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""trace_id 传递 / LLM span 覆盖兼容层。

openjiuwen 0.1.16 的 create_workflow_session / create_agent_session 尚不接受 trace_id 参数，
待新版本已支持。本模块在 import 时检测签名，仅在底层支持时
才透传 trace_id，保证升级前后均不会报错。

build_traced_model 把裸 core Model 交给 openjiuwen 装饰器（on_llm_start /
on_llm_end，携带 usage 与 ttft），按 core 装饰器测量能力门控：旧 core 上探不到
OtelAgentHandler.LLM_SPAN_DECORATOR_CAPABILITY 时原样返回裸模型——旧 handler
读不到容器级 usage 兄弟键，装饰只会白发 span 且层间无去重。
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
# LLM span 覆盖：裸 Model -> 装饰器（usage / ttft 测量）
# ---------------------------------------------------------------------------

# 一次性探测 core 是否具备装饰器测量 llm span 的消费能力
# （OtelAgentHandler.LLM_SPAN_DECORATOR_CAPABILITY，core 侧纯新增线引入）。
# 旧 core 无该常量：handler 读不到容器级 usage_metadata 兄弟键，装饰器发射的
# llm span 只见事件不见数据（usage/ttft 全丢），且层间双计只能靠后端去重规则
# 兜底；探测不到即退回裸模型，把覆盖缺口封闭在 core 升级窗口内。
# 常量契约以 core !3570/!3571 合入 head 为准（d896e39f1/848dd77a9 起）：
# int 版本号（=1，consumed shape 变化时 bump），数值比较 >= 1 判开。11-06
# 曾对着已撤回的合并线旧提交误核实（11-04 短暂存在 LLM_SPAN_MERGE_CAPABILITY，
# 随合并逻辑一并撤回）改成 MERGE 字符串判等——对着真 head 恒探不到、门控
# 静默常闭；跨仓核实必须对着 API 权威 PR head，勿信本地陈旧 ref/安装副本。
_LLM_SPAN_DECORATOR_CAPABLE = None


def _llm_span_decorator_capable() -> bool:
    """core handler 是否能消费装饰器测量的 llm span（结果进程内缓存）。"""
    global _LLM_SPAN_DECORATOR_CAPABLE
    if _LLM_SPAN_DECORATOR_CAPABLE is None:
        capable = False
        try:
            from openjiuwen.extensions.tracer_otel.handler import OtelAgentHandler

            capable = getattr(OtelAgentHandler, "LLM_SPAN_DECORATOR_CAPABILITY", 0) >= 1
        except Exception:  # noqa: BLE001 - 旧 core 无 tracer_otel 扩展时按无能力处理
            capable = False
        _LLM_SPAN_DECORATOR_CAPABLE = capable
    return _LLM_SPAN_DECORATOR_CAPABLE


# 定义级产物（工作流 IR 转换出的组件/模型，跨执行复用）的会话身份：构建时
# 不存在按会话归因的真实 id，绑定任一请求的 id（含 trace_id）都会错归属，
# 故显式落此常量且不绑请求 trace；会话归因由执行期 trace 树（span 挂在
# 真实组件壳/工作流 trace 下）承担。
DEFINITION_SCOPED_SESSION_ID = "workflow-llm"


# 一次性探测 core 装饰器是否支持 identity 归因参数（core 侧纯新增线引入：
# decorate_model_with_trace(model, agent_session, identity=None)，把
# workflow_id 等业务身份键 flat 并入 instance_info，由 handler 在 span 上
# write-if-absent 盖属性）。旧 core 无该参数：传了会在调用点抛 TypeError，
# 把整段装饰降级成裸模型（span 全丢），故必须先探测再决定是否透传。
_DECORATOR_ACCEPTS_IDENTITY = None


def _decorator_accepts_identity() -> bool:
    """core 装饰器是否接受 identity 参数（结果进程内缓存）。"""
    global _DECORATOR_ACCEPTS_IDENTITY
    if _DECORATOR_ACCEPTS_IDENTITY is None:
        accepted = False
        try:
            from openjiuwen.core.session.tracer import decorate_model_with_trace

            accepted = "identity" in inspect.signature(decorate_model_with_trace).parameters
        except Exception:  # noqa: BLE001 - 旧 core 无该入口时按不支持处理
            accepted = False
        _DECORATOR_ACCEPTS_IDENTITY = accepted
    return _DECORATOR_ACCEPTS_IDENTITY


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

    - 能力门槛：core handler 消费不了装饰器测量数据时原样返回裸模型（宁可
      无 span 不白发）；
    - ``session`` 显式传入则直接复用（当前生产调用点均传 session_id 由工厂
      建轻量会话，该参数供测试与后续接线预留）。轻量会话不触碰任何既有
      会话——OTel 父链按调用时 ambient 上下文解析（组件壳/rail span 下的
      真实子 span，见 core LLM_SPAN_DECORATOR_CAPABILITY 旁注释），与会话对象无关，
      不会因执行会话与装饰会话是两个对象而分叉 trace；层间双计由后端
      "优先计子、无子再计桥" 规则去重；
    - 轻量会话的会话身份与 trace 均不得绑定构建期请求（定义级产物跨执行
      复用，绑定任一请求都会错归属）：无显式 session_id 时落
      ``DEFINITION_SCOPED_SESSION_ID`` 且不绑请求 trace；每执行新建模型的
      请求级场景传当次会话 id，trace 沿用请求上下文；
    - ``identity`` 透传业务归因键（workflow_id / agent_id / ...，core 侧
      write-if-absent 盖属性）：独立/子 llm span 带上业务身份。旧 core
      装饰器无该参数时自动退化为不传（保留 span，仅缺身份键），不因
      TypeError 丢整段装饰；
    - 遥测侧任何失败（探测 / 导入 / 建会话 / 装饰）都降级返回裸模型，
      绝不影响模型创建与业务语义。
    """
    if not _llm_span_decorator_capable():
        return model
    try:
        from openjiuwen.core.session.tracer import decorate_model_with_trace
    except Exception as e:  # noqa: BLE001 - 旧 core 无该入口
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
        if identity and _decorator_accepts_identity():
            return decorate_model_with_trace(model, session, identity=identity)
        return decorate_model_with_trace(model, session)
    except Exception as e:  # noqa: BLE001 - 遥测失败不得阻断模型创建
        logger.warning("build_traced_model: trace decoration degraded to bare model: %s", e)
        return model
