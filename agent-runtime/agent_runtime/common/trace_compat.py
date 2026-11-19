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
定义级产物（跨执行复用的工作流组件模型）经 _CallScopedTracedModel 调用期
解析会话：每次调用继承 ambient 上层 span 的会话 id/trace id，无上层退
DEFINITION_SCOPED_SESSION_ID 哨兵。
"""

from __future__ import annotations

import inspect
from collections import OrderedDict
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


def bind_current_user_id(user_id):
    """绑定当前执行的用户 id（有值才绑，绝不清除既有值）。

    供跨任务/线程边界的载体在执行入口回填：多智能体消息经队列与
    ``asyncio.create_task`` 投递，处理任务继承的是消费循环上下文（用户
    事实为空），由 ``SendMessageEnvelope.user_id`` 在
    ``_process_send_message`` 入口回绑——下游 ``current_user_id`` 读取方
    （ModelWrapper 兜底 / build_traced_model 注入）即恢复可见。
    """
    if user_id:
        _CURRENT_USER_ID.set(str(user_id))


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

# 定义级产物（工作流 IR 转换出的组件/模型，跨执行复用）的会话身份兜底：
# 构建时不存在按会话归因的真实 id，绑定任一请求的 id（含 trace_id）都会
# 错归属，故无上层 span 可继承时显式落此常量且不绑请求 trace；有上层
# span 时按调用继承其会话身份（见 _CallScopedTracedModel）。
DEFINITION_SCOPED_SESSION_ID = "workflow-llm"

# core OTel 侧 span 的会话属性键（openjiuwen/extensions/tracer_otel/
# semconv.py 的 OJ_SESSION_ID）——跨仓冻结线格式，勿本地改名。
_OJ_SESSION_ID_ATTR = "openjiuwen.session_id"

# 调用期装饰缓存上限：键为 (会话 id, trace id)，单工作流并发执行的会话数
# 有限；超限 LRU 逐出最久未用域（遥测侧缓存宁缺勿涨——被逐域复现时重建，
# 代价一次轻量会话创建，不丢 span）。
_CALL_SCOPE_CACHE_LIMIT = 32


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


def _model_display_name(model) -> str:
    """读取 provider 随 client_config 带出的模型显示名；缺失返回空串。

    探针两级同构（foundation 顶层 / 组件 config 包装），只为显示名，绝不
    触碰 model_name（那是路由身份，OBS 生态装 modelServiceId）。
    """
    configs = (
        getattr(model, "model_client_config", None),
        getattr(getattr(model, "config", None), "model_client_config", None),
    )
    for cfg in configs:
        name = getattr(cfg, "model_display_name", None) if cfg is not None else None
        if name:
            return str(name)
    return ""


def _ambient_session_refs() -> tuple[str | None, str | None]:
    """读 ambient OTel 当前 span 的 (会话 id, trace id)；无有效父返 (None, None)。

    llm span 的 OTel 父链本就按调用时 ambient 上下文解析（组件壳/rail span
    下的真实子 span），此处读的是同一上下文同一属性——父链能挂对，会话
    身份就能继承对。任何读取失败返回 (None, None)，绝不抛出。
    """
    try:
        from opentelemetry import context as otel_context
        from opentelemetry import trace as otel_trace

        span = otel_trace.get_current_span(otel_context.get_current())
        span_context = span.get_span_context()
        if not span_context.is_valid:
            return None, None
        session_id = (getattr(span, "attributes", None) or {}).get(_OJ_SESSION_ID_ATTR)
        if not session_id:
            return None, None
        return str(session_id), format(span_context.trace_id, "032x")
    except Exception:  # noqa: BLE001 - ambient 解析失败不构成遥测失败
        return None, None


def _decorate_model_with_facts(decorate, model, session, identity):
    """身份增补 + 能力门控后装饰（显式会话与调用期路径共用）。

    增补均为缺省才补、绝不覆盖显式值；有增补才拷贝，无事实保持 identity
    引用原样透传：
    - user_id：workflow 五节点身份只带 workflow 归因，用户事实经 runner 建
      会话播种的 current_user_id() 兜底注入（显式传入优先）；
    - class_name：模型显示名覆盖——OBS 模型服务生态下 model_name 装的是
      modelServiceId（UUID），provider 把元数据里的真实模型名随
      client_config.model_display_name 带出，此处覆盖装饰器探针结果，
      llm span 名与 gen_ai.request.model 显示真名（缺名不覆盖）。
    旧 core 装饰器无 identity 参数时退两参调用（普通 llm span，不退裸
    模型、不刷告警），新 studio × 旧 core 最差=现状。
    """
    user_id = "" if identity and identity.get("user_id") else (current_user_id() or "")
    display_name = _model_display_name(model)
    if user_id or display_name:
        identity = dict(identity) if identity else {}
        if user_id:
            identity["user_id"] = str(user_id)
        if display_name:
            identity["class_name"] = display_name
    if identity and callable_accepts_kwarg(decorate, "identity"):
        return decorate(model, session, identity=identity)
    return decorate(model, session)


class _CallScopedTracedModel:
    """定义级模型的调用期装饰代理：每次调用继承上层 span 的会话身份。

    装饰期绑定会话的定义级产物（跨执行复用的组件模型）会把构建期请求的
    会话/trace 错归到后续所有执行（缓存模型保留首调会话，检视 198236863）。
    本代理把装饰推迟到每次 invoke/stream：读 ambient 当前 span（组件壳/
    上层 llm span——llm span 的 OTel 父链本就按它解析），继承其会话 id
    动态建轻量会话、装饰当次调用（ambient 的 trace id 一并传入会话工厂
    ——core 0.1.17_hotfix 工厂暂不转发该参数，OTel 父链按 ambient 解析、
    与旧版一致，传入是为 core 补齐转发后的前向兼容）——同一缓存模型在
    不同会话的执行各自归属，无跨请求污染，域缓存超限 LRU 逐出。无
    ambient 父（单组件调试等）退定义级哨兵（DEFINITION_SCOPED_SESSION_ID
    + 不绑请求 trace），装饰产物按调用期用户分桶复用（user_id 是装饰期
    事实，整体单值缓存会让首个用户的身份错归后续所有无父调用）。解析/
    装饰任何失败退裸模型直调；产物的 invoke/stream 兼容同步形态
    （await 非协程/async for 非异步迭代器会 TypeError），绝不阻断业务
    调用。
    """

    def __init__(self, model, identity, decorate) -> None:
        self._model = model
        # 调用方 identity 的私有副本：装饰期增补绝不改写调用方字典
        self._identity = dict(identity) if identity else {}
        self._decorate = decorate
        self._scoped_cache: OrderedDict[tuple[str, str], object] = OrderedDict()
        self._fallbacks: OrderedDict[str, object] = OrderedDict()
        self._degrade_logged = False

    def _decorated_for_call(self) -> object:
        try:
            session_id, trace_id = _ambient_session_refs()
            if session_id is None:
                # 无 ambient 父：退定义级哨兵（不绑请求 trace）；装饰产物
                # 按调用期用户分桶缓存——跨用户复用会错归属（见类 docstring）
                user_key = current_user_id() or ""
                decorated = self._fallbacks.get(user_key)
                if decorated is not None:
                    self._fallbacks.move_to_end(user_key)
                    return decorated
                session = create_agent_session_with_trace(
                    session_id=DEFINITION_SCOPED_SESSION_ID,
                    trace_id=_DEFINITION_NO_TRACE,
                )
                decorated = _decorate_model_with_facts(
                    self._decorate, self._model, session, self._identity
                )
                self._fallbacks[user_key] = decorated
                while len(self._fallbacks) > _CALL_SCOPE_CACHE_LIMIT:
                    self._fallbacks.popitem(last=False)
                return decorated
            key = (session_id, trace_id)
            decorated = self._scoped_cache.get(key)
            if decorated is not None:
                self._scoped_cache.move_to_end(key)
                return decorated
            session = create_agent_session_with_trace(
                session_id=session_id, trace_id=trace_id
            )
            decorated = _decorate_model_with_facts(
                self._decorate, self._model, session, self._identity
            )
            self._scoped_cache[key] = decorated
            while len(self._scoped_cache) > _CALL_SCOPE_CACHE_LIMIT:
                self._scoped_cache.popitem(last=False)
            return decorated
        except Exception as e:  # noqa: BLE001 - 遥测失败退裸模型直调
            if not self._degrade_logged:
                logger.warning(
                    "build_traced_model: per-call trace decoration degraded to bare model: %s", e
                )
                self._degrade_logged = True
            return self._model

    async def invoke(self, *args, **kwargs):
        # 产物兼容同步形态：降级退裸模型等场景 invoke 可能不是协程，
        # 盲 await 会 TypeError（与旧版直接返回裸模型的接口契约等宽）
        result = self._decorated_for_call().invoke(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    async def stream(self, *args, **kwargs):
        # 同上：stream 可能是同步可迭代对象，按形态分流
        result = self._decorated_for_call().stream(*args, **kwargs)
        if hasattr(result, "__aiter__"):
            async for chunk in result:
                yield chunk
        else:
            for chunk in result:
                yield chunk

    def __getattr__(self, name: str):
        return getattr(self._model, name)


def build_traced_model(model, session=None, session_id: str = None, identity: dict = None):
    """把裸 core Model 交给 openjiuwen 装饰器，补齐每次调用的 llm span。

    - ``session`` 显式传入则直接复用（测试与后续接线预留）；请求级场景
      （每执行新建模型）传当次会话 id：装饰期绑定该会话，trace 沿用请求
      上下文。轻量会话不触碰任何既有会话——OTel 父链按调用时 ambient
      上下文解析（组件壳/rail span 下的真实子 span），与会话对象无关，
      不会因执行会话与装饰会话是两个对象而分叉 trace；层间双计由后端
      "优先计子、无子再计桥" 规则去重；
    - 定义级产物（工作流 IR 转换出的组件模型，跨执行复用；session_id
      缺省、空串等 falsy 值或传 ``DEFINITION_SCOPED_SESSION_ID``）不装
      饰期绑定会话——绑
      任一构建期请求会把后续执行错归该请求的 trace/会话；返回
      ``_CallScopedTracedModel`` 调用期解析代理：每次 invoke/stream 继承
      ambient 上层 span 的会话 id 动态装饰（trace id 一并传入会话工厂，
      core 工厂暂不转发、OTel 父链仍按 ambient 解析，见代理类 docstring），
      无上层（单组件调试等）退定义级哨兵且不绑请求 trace；
    - ``identity`` 透传业务归因键（workflow_id / agent_id / request_params /
      message_count / 会话事实 / ...，core 侧 write-if-absent 盖属性）：
      独立/子 llm span 带上业务身份与调用事实；user_id / 模型显示名在
      装饰时增补（定义级路径随调用期取值，用户事实按当次执行归属）；
    - 遥测侧任何失败都降级：导入失败退裸模型；显式/请求级路径建会话或
      装饰失败退裸模型；定义级路径逐调用失败退裸模型直调——绝不影响
      模型创建与业务语义。
    """
    try:
        from openjiuwen.core.session.tracer import decorate_model_with_trace
    except Exception as e:  # noqa: BLE001 - core 无该入口
        logger.warning("build_traced_model: decorate entry missing, bare model kept: %s", e)
        return model
    if session is not None or (session_id and session_id != DEFINITION_SCOPED_SESSION_ID):
        # 显式会话 / 请求级会话 id：装饰期绑定（既有语义）
        try:
            if session is None:
                session = create_agent_session_with_trace(session_id=session_id)
            return _decorate_model_with_facts(decorate_model_with_trace, model, session, identity)
        except Exception as e:  # noqa: BLE001 - 遥测失败不得阻断模型创建
            logger.warning("build_traced_model: trace decoration degraded to bare model: %s", e)
            return model
    # 定义级产物：调用期解析会话（装饰期绑定会跨执行错归属）
    return _CallScopedTracedModel(model, identity, decorate_model_with_trace)
