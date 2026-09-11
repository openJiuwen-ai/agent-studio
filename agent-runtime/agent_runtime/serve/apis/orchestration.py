"""
Orchestration API — MVP implementation of /v1/orchestration/ir/execute
"""

import json
import os
import asyncio
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass
from typing import Union

from agent_runtime.common.config import settings, ModelConfigStrategyType
from agent_runtime.common.ir_exceptions import IRBuildException
from agent_runtime.common.ir_interfaces import (
    StorageConfigError,
    StorageReadError,
)
from agent_runtime.context.request_context import _request_ctx
from agent_runtime.runner.controller_runner import ControllerRunner
from agent_runtime.runner.react_agent_runner import ReActAgentRunner
from agent_runtime.runner.workflow_runner import WorkflowRunner, ModelConfigStrategy
from agent_runtime.schemas.orchestration_mgr import (
    ComponentDebugRequest,
    ExecutionRequest,
    ResponseMode,
    DeleteExecutionInstanceRequest,
)
from agent_runtime.schemas.additional_questions import (
    AdditionalQuestionsContext,
    AdditionalQuestionsRequest,
    AdditionalQuestionsResponse,
)
from agent_runtime.additional_questions.service import (
    AdditionalQuestionsService,
)
from agent_runtime.moderation.stream_moderation import (
    apply_stream_moderation,
    block_event_generator,
    init_moderation_from_ir,
)
from common_utils.customer_header import get_config

from storage import get_storage_provider
from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse
from jiuwen.common.exception import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.serve.controllers.execution.manager import AsyncStateManager
from jiuwen.serve.controllers.execution.open_utils import async_ir_load, cache_workflow_queue
from openjiuwen.core.common.logging import workflow_logger
from pydantic import ValidationError

from agent_runtime.serve.execution_registry import RegistrationInfo, get_execution_registry
from agent_runtime.serve.apis.run_check import (
    _CODE_AGENT_PERMISSION,
    _CODE_WORKFLOW_PERMISSION,
    _build_error_response,
)
# 注：N2L chat 端点已随 agent_builder 抽离到 studio-builder 镜像（agent_builder/serve/apis/n2l_api.py），
# runtime 不再 import agent_builder.nl_to_agent.nl2（避免 runtime→agent_builder 耦合）。


#  全局安全修复：body header 默认不参与可信构造
# 保留/客户 header 出现在 body → 400（拒绝，非忽略）
def _build_runtime_execution_headers(
    platform_headers: dict,
    customer_headers: dict,
) -> dict:
    """构建运行时执行 header — 平台 header + 客户 header 合并"""
    result = {}
    for key, value in (platform_headers or {}).items():
        if value:
            result[key.lower()] = value
    for key, value in (customer_headers or {}).items():
        if value:
            result[key.lower()] = value
    return result



execution_app = APIRouter(tags=["execution_app"])

# Shared runner singletons; created lazily so env vars are loaded.
_workflow_runner: WorkflowRunner | None = None
_react_runner: ReActAgentRunner | None = None
_controller_runner: ControllerRunner | None = None
_DEFAULT = "default"


def _get_workflow_runner() -> WorkflowRunner:
    global _workflow_runner
    if _workflow_runner is None:
        strategy_env = settings.llm.model_config_strategy
        strategy_map = {
            ModelConfigStrategyType.ENV: ModelConfigStrategy.ENV,
            ModelConfigStrategyType.IR: ModelConfigStrategy.IR,
            ModelConfigStrategyType.OBS: ModelConfigStrategy.OBS,
        }
        _workflow_runner = WorkflowRunner(
            api_key=os.environ.get("API_KEY"),
            api_base=os.environ.get("API_BASE"),
            model_strategy=strategy_map.get(strategy_env, ModelConfigStrategy.IR),
        )
    return _workflow_runner


def _get_react_runner() -> ReActAgentRunner:
    global _react_runner
    if _react_runner is None:
        # 确保 model config provider factory 已初始化
        _get_workflow_runner()
        _react_runner = ReActAgentRunner(
            api_key=os.environ.get("API_KEY"),
            api_base=os.environ.get("API_BASE"),
        )
    return _react_runner


def _get_controller_runner() -> ControllerRunner:
    global _controller_runner
    if _controller_runner is None:
        # 确保 model config provider factory 已初始化
        _get_workflow_runner()
        _controller_runner = ControllerRunner(
            api_key=os.environ.get("API_KEY"),
            api_base=os.environ.get("API_BASE"),
        )
    return _controller_runner


def _get_runner_by_type(agent_type: str):
    """根据agent_type返回对应的runner"""
    if agent_type == "ReAct":
        return _get_react_runner()
    if agent_type in ("Controller", "PlanExecute"):
        return _get_controller_runner()
    return _get_workflow_runner()


@execution_app.get("/v1/health", response_class=PlainTextResponse, summary="健康检查")
async def health():
    """Restful API for server health."""
    return (
        settings.health_check.custom_rsp
        if settings.health_check.custom_rsp
        else "the health is good"
    )


@execution_app.post("/v1/orchestration/ir/execute", summary="IR 执行（流式/非流式）")
async def ir_execute(req_json: dict, request: Request):
    """
    IR execute endpoint.
    直接透传 openjiuwen 原生格式，不做额外包装
    """
    workflow_logger.debug(
        "IR Execute Request - URL: %s %s", request.method, request.url
    )
    workflow_logger.debug(
        "IR Execute Request - Headers: %s",
        json.dumps(dict(request.headers), ensure_ascii=False),
    )
    workflow_logger.debug(
        "IR Execute Request - Query Params: %s",
        json.dumps(dict(request.query_params), ensure_ascii=False),
    )
    workflow_logger.debug(
        "IR Execute Request - Body: %s", json.dumps(req_json, ensure_ascii=False)
    )

    try:
        req = ExecutionRequest.model_validate(req_json)
        #  全局安全修复：禁止 body 覆盖服务器认证/平台协议 Header
        # 保留/客户 header 出现在 body → 400
        request_ctx = _request_ctx.get()
        try:
            req.headers = _build_runtime_execution_headers(
                platform_headers=request_ctx.platform_headers,
                customer_headers=request_ctx.customer_headers,
            )
        except ValueError as e:
            return JSONResponse(
                status_code=400,
                content={"error": "reserved_header_in_body", "details": str(e)},
            )
        # Profile 启用时服务器覆盖 effective userId（防 body 伪造）
        cfg = get_config()
        if cfg.enabled:
            req.user_id = request_ctx.user_id
        req.params = prepare_params(req)
        req.params.global_variables = {
            "sys": {
                "conversationHistory": req.params.conversation_history,
                "conversationId": req.conversation_id,
                "userId": req.user_id,
                "dialogueCount": req_json.get("dialogueCount", 1),
                "currentTime": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "conversationId": req.conversation_id,
            "userId": req.user_id,
        } | req.params.global_variables
        req.params.is_debug = req.headers.get("x-invoke-mode", "").lower() == "debug"
    except ValidationError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "validation_failed", "details": str(e)},
        )

    execution_id = req.headers.get("x-execution-id", "")

    # 只读一次 IR（避免重复读取）
    exec_id = execution_id
    ir_path = req.ir_path
    try:
        ir_json = await async_ir_load(ir_path)
    except Exception as e:
        workflow_logger.error(f"Failed to load IR from {ir_path}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "ir_load_failed", "details": str(e)},
        )

    mode = (ir_json.get("configs") or {}).get("mode", "workflow")

    # 内容审核：初始化引擎 + 输入审核
    moderation_engine = init_moderation_from_ir(ir_json)
    if moderation_engine:
        is_safe, result = moderation_engine.check_input_query(req.query)
        if not is_safe:
            workflow_logger.info("Input moderation blocked query for execution_id=%s", execution_id)
            return StreamingResponse(
                content=block_event_generator(result, mode, execution_id),
                media_type="text/event-stream",
            )

    runner = _get_runner_by_type(mode)

    if req.response_mode == ResponseMode.STREAMING:
        entry_id = getattr(request.state, "instance_id", "")
        # entry_id=执行入口，由 app_run 三个执行端点写入 request.state.instance_id
        # （app_run.py:361-366 workflow 执行=workflow_id / :483-488 agent 执行=agent_id /
        # :583-593 另一 workflow 端点=workflow_id），作为注册记录 agent_id 供终止接口
        # 归属校验与回显。绕过 app_run 直调 ir_execute 时为空串：归属校验静默退化，
        # 记 warning 保证可观测（检视意见：入口校验依赖 instance_id 注入）。
        if not entry_id:
            workflow_logger.warning(
                "ir_execute without entry_id: request.state.instance_id not set "
                "(bypassed app_run endpoints?), cancel entry-level check will "
                "degrade, conv=%s",
                req.conversation_id,
            )
        return StreamingResponse(
            content=stream_response(
                req, execution_id, runner, moderation_engine,
                entry_id=entry_id,
            ),
            media_type="text/event-stream",
        )
    else:
        full_text = await runner.run_blocking(req)
        now_ms = int(time.time() * 1000)
        return JSONResponse(
            content={
                "event": "done",
                "createdTime": now_ms,
                "executionId": execution_id,
                "data": {"text": full_text},
            }
        )


def _stream_event_of(chunk) -> str:
    """识别 SSE chunk 的事件类型，供 stream_response 拦截终态 done(R-20)。

    接受 bytes(SSE 'data: {...}\\n\\n')与 dict(错误流 / 其他 runner)；其他类型或
    解码/解析失败返回 ''(保守不识别 → 该帧按普通帧透传，最坏退化为现状行为)。
    仅读取 event 字段，不重写 chunk。
    """
    if isinstance(chunk, dict):
        return chunk.get("event", "")
    if isinstance(chunk, (bytes, bytearray)):
        try:
            text = bytes(chunk).decode("utf-8")
        except UnicodeDecodeError:
            return ""
        if not text.startswith("data: "):
            return ""
        try:
            payload = json.loads(text[6:].strip())
        except json.JSONDecodeError:
            return ""
        return payload.get("event", "") if isinstance(payload, dict) else ""
    return ""


def _serialize_stream_chunk(chunk):
    """保持 bytes/bytearray 原样输出，dict 序列化为 SSE 帧；不重写非 done 的普通帧。"""
    if isinstance(chunk, (bytes, bytearray)):
        return bytes(chunk)
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


def _fallback_terminal_done(execution_id: str) -> str:
    """runner 未发送 done 时构造的兜底终态事件(空 data)。"""
    done_payload = {
        "event": "done",
        "data": {},
        "index": 0,
        "executionId": execution_id,
        "createdTime": int(time.time()),
    }
    return f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"


async def stream_response(
    req: ExecutionRequest,
    execution_id: str,
    runner,
    moderation_engine=None,
    entry_id: str = "",
):
    """
    透传 OutputSchema 格式
    输出格式: data: {"type": "end node stream", "index": 0, "payload": {"response": "text"}}\n\n

    审核层：在 dict 层插入 apply_stream_moderation()，对 message/message_end 事件的
    think/answer 做内容审核。事件包装层（未来）将作为另一个 generator wrapper 插入。

    终态 done 幂等(R-20，策略 A)：Controller 的 run_streaming 正常流产 SSE bytes，且自发一个
    带答案的 done#1(位于 task_end 之前，非末尾)。本方法吸收 runner 的 done，延迟到整个流结束
    时发送唯一一个 done，保证"唯一 + 末尾"。必须原样保留 runner done 的 payload——studio-runtime
    的 processOnControllerDoneMessage 消费 done.data.answer 写入会话消息(getMessages →
    updateConversation)，清空会导致本轮助手答案不入会话历史、第二轮上下文缺失；故仅当 runner
    未发 done 时才构造空兜底。

    执行注册（终止接口数据源）：开头注册 current_task + 归属四元组到 ExecutionRegistry
    （agent_id=entry_id，由 ir_execute 从 request.state.instance_id 传入：执行智能体时=agent_id、
    执行工作流时=workflow_id）；finally 首行注销，自然结束/异常/被取消三路径均无残留。
    运行中被取消时本生成器被 task.cancel() 掐断，末尾无 done（无 done 即中止约定）。
    """
    execution_id = execution_id or str(uuid.uuid4())
    registry = get_execution_registry()
    entry_task = asyncio.current_task()
    try:
        try:
            _ctx = _request_ctx.get()
        except LookupError:
            _ctx = None
        await registry.register(
            req.conversation_id,
            entry_task,
            execution_id,
            info=RegistrationInfo(
                project_id=(_ctx.project_id if _ctx is not None else ""),
                agent_id=entry_id,
                user_id=(_ctx.user_id if _ctx is not None else ""),
            ),
        )
        pending_done = None  # 暂存 runner 自发的首个 done(Controller done#1 / 异常 except done)

        raw_gen = runner.run_streaming(req, execution_id)
        moderated_gen = apply_stream_moderation(raw_gen, moderation_engine) if moderation_engine else raw_gen

        async for chunk in moderated_gen:
            if chunk is None:
                continue
            if _stream_event_of(chunk) == "done":
                # 拦截 runner 的 done，延迟到流末尾发送(出现多个 done 时保留第一个)
                if pending_done is None:
                    pending_done = chunk
                continue
            # 非 done 事件原样透传：bytes/bytearray 不重写，dict 序列化
            yield _serialize_stream_chunk(chunk)

        # 流末尾：发送唯一一个终态 done —— 有 runner done 则原样保留其 payload，否则空兜底
        if pending_done is not None:
            yield _serialize_stream_chunk(pending_done)
        else:
            yield _fallback_terminal_done(execution_id)
    finally:
        await registry.unregister(req.conversation_id, task=entry_task)


@dataclass
class CancelCheckContext:
    """cancel 归属校验上下文：路径 project + 可选入口 query（G.FNM.03 参数封装）。"""

    project_id: str
    agent_id: str = ""
    workflow_id: str = ""


async def _check_before_cancel(
    registry,
    conversation_id: str,
    ctx: CancelCheckContext,
    language: str,
):
    """终止接口运行时归属校验（与执行接口 run_check"项目匹配 403"同规格）。

    路径 project_id 强校验恒在；可选 query agentId/workflowId 提供任一则做入口级校验
    （与 exec:{conv} 注册记录的 agent_id 字段比对）。不匹配返回 403 ErrorRsp（403 时
    取消标记不置位——本函数只读不写）；无在飞注册记录幂等放行返回 None。
    403 错误码按入口分流复用统一码表两码（零新增 i18n key）：携带 agentId→02101016、
    其余（携带 workflowId 或仅 project 不匹配）→02201020。
    """
    registration = await registry.get_registration(conversation_id)
    if not registration:
        return None  # 无在飞记录：幂等放行（US9）；是否置位由调用方按挂起态决定
    provided_entry = ctx.agent_id or ctx.workflow_id
    project_mismatch = registration.get("project_id") != ctx.project_id
    entry_mismatch = (
        bool(provided_entry) and registration.get("agent_id") != provided_entry
    )
    if project_mismatch or entry_mismatch:
        code_key = _CODE_AGENT_PERMISSION if ctx.agent_id else _CODE_WORKFLOW_PERMISSION
        workflow_logger.info(
            "Cancel forbidden: conv=%s provided_entry=%s registered_project=%s",
            conversation_id,
            provided_entry,
            registration.get("project_id"),
        )
        return _build_error_response(403, code_key, language)
    return None


async def _has_suspended_checkpoint(conversation_id: str) -> bool:
    """会话是否存在挂起 checkpoint（fast/底层 checkpointer 均实现 session_exists）。

    checkpointer 探测失败时保守返回 True：挂起态取消是 US3 主路径，探测不可用期间
    维持"置位"既有行为，宁可多置位（TTL 过期兜底）也不静默丢失取消信号。
    """
    try:
        from openjiuwen.core.session.checkpointer.checkpointer import CheckpointerFactory

        checkpointer = CheckpointerFactory.get_checkpointer()
        return bool(await checkpointer.session_exists(conversation_id))
    except Exception as err:  # noqa: BLE001 探测失败按挂起处理（保守置位）
        workflow_logger.warning(
            "Suspend-check probe failed, fall back to mark: conv=%s, %s",
            conversation_id,
            err,
        )
        return True


@execution_app.post("/v1/{project_id}/conversations/{conversation_id}/cancel")
async def cancel_execution(
    request: Request,
    project_id: str,
    conversation_id: str,
    agent_id: str = "",
    workflow_id: str = "",
):
    """执行终止端点（工作流/多智能体/单智能体三类合并 1 接口，定位主键 conversation_id）。

    归属校验（_check_before_cancel）→ 置协作式取消标记（所有实例可见，幂等 TTL）
    + runtime:cancel 频道广播（持有实例本地 task.cancel 尽力即时）→ 200 五字段。
    cancelled=取消信号已受理（除 4xx/5xx 外恒 true，不代表终止完成）；running=调用时
    是否检测到在飞执行（仅参考，false 覆盖无在飞/已挂起/已结束，不视为失败）。
    运行中被终止的原 SSE 流末尾无 done（无 done 即中止，零改动约定）。
    """
    language = request.headers.get("x-language", "zh-cn")
    registry = get_execution_registry()

    forbidden_response = await _check_before_cancel(
        registry,
        conversation_id,
        CancelCheckContext(project_id=project_id, agent_id=agent_id, workflow_id=workflow_id),
        language,
    )
    if forbidden_response is not None:
        return forbidden_response

    registration = await registry.get_registration(conversation_id)
    running = bool(registration)  # 是否检测到在飞执行（仅参考信息）
    if not running and not await _has_suspended_checkpoint(conversation_id):
        # 无在飞且无挂起（从未执行/已结束会话）：幂等放行但绝不写取消标记。
        # 否则任意 conversation_id 可跨项目置位 cancel:true，污染该会话后续的
        # 挂起恢复（resume 误判为已取消、合法 checkpoint 被清）；标记仅对
        # 有意义的取消（在飞终止/挂起终止）置位（检视意见①）
        workflow_logger.info(
            "Cancel accepted as no-op: no in-flight registration and no suspended "
            "checkpoint, conv=%s",
            conversation_id,
        )
        return JSONResponse(
            status_code=200,
            content={
                "agent_id": registration.get("agent_id") or agent_id or workflow_id,
                "conversation_id": conversation_id,
                "cancelled": True,
                "running": False,
                "message": "cancel signal accepted",
            },
        )
    await registry.mark_cancelled(conversation_id)
    return JSONResponse(
        status_code=200,
        content={
            "agent_id": registration.get("agent_id") or agent_id or workflow_id,
            "conversation_id": conversation_id,
            "cancelled": True,
            "running": running,
            "message": "cancel signal accepted",
        },
    )


@execution_app.post("/v1/orchestration/ir/component/{component_id}/execute", summary="单组件调试执行")
async def component_debug_execute(component_id: str, req_json: dict, request: Request):
    """单组件调试端点（：与普通执行一致 — body 安全 + effective userId 服务器覆盖）"""
    try:
        req = ComponentDebugRequest.model_validate(req_json)
        # 禁止 body 覆盖服务器认证/平台协议 Header（与 ir_execute 同规则）
        request_ctx = _request_ctx.get()
        try:
            req.headers = _build_runtime_execution_headers(
                platform_headers=request_ctx.platform_headers,
                customer_headers=request_ctx.customer_headers,
            )
        except ValueError as e:
            return JSONResponse(
                status_code=400,
                content={"error": "reserved_header_in_body", "details": str(e)},
            )
        # Profile 启用时服务器覆盖 effective userId（防 body 伪造）
        cfg = get_config()
        if cfg.enabled:
            req.user_id = request_ctx.user_id
        req.params = prepare_params(req)
        req.params.global_variables = {
            "sys": {
                "conversationHistory": req.params.conversation_history,
                "conversationId": req.conversation_id,
                "userId": req.user_id,
            },
            "conversationId": req.conversation_id,
            "userId": req.user_id,
        } | req.params.global_variables
    except ValidationError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "validation_failed", "details": str(e)},
        )

    execution_id = getattr(request.state, "execution_id", None) or str(uuid.uuid4())
    runner = _get_workflow_runner()

    return StreamingResponse(
        content=debug_stream_response(req, component_id, execution_id, runner),
        media_type="text/event-stream",
    )


async def debug_stream_response(
    req: ComponentDebugRequest,
    component_id: str,
    execution_id: str,
    runner: WorkflowRunner,
):
    """单组件调试 SSE 流"""
    async for chunk in runner.run_debug_streaming(req, component_id, execution_id):
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


def prepare_params(req: Union[ExecutionRequest, ComponentDebugRequest]):
    """
    格式化请求参数并将请求头中的信息添加到参数中。

    此函数用于处理请求参数，特别是插件配置部分。它将请求头中的信息合并到插件配置中，并返回处理后的参数。

    Args:
        req (Union[ExecutionRequest, ComponentDebugRequest]): 执行请求或组件执行请求对象，包含请求参数和请求头。

    Returns:
        ExecutionParams 或 ComponentParams: 处理后的请求参数，包含更新后的插件配置。

    Raises:
        无特定异常抛出。

    Notes:
        - 函数首先创建请求参数的深拷贝以避免修改原始参数。
        - 将请求头中的信息转换为小写，并合并到每个插件配置中。
        - 如果请求中没有插件配置，则至少为默认配置添加请求头信息。
    """
    params = deepcopy(req.params)

    # 处理插件鉴权信息，需要将请求头中所带的信息加入params
    headers_dict = {key.lower(): value for key, value in dict(req.headers).items()}
    prepared_plugin_configs = {}
    if req.params.plugin_configs:
        for plugin_config in req.params.plugin_configs:
            prepared_plugin_configs[plugin_config.plugin_id] = {
                **headers_dict,
                **plugin_config.config,
            }
    prepared_plugin_configs[_DEFAULT] = {**headers_dict}
    params.plugin_configs = prepared_plugin_configs

    return params


async def _load_ir_json(ir_path: str) -> dict:
    """从对象存储读取 IR JSON，返回解析后的 dict

    ir_runner 只做 dict → workflow；存储读取由 Runner 编排。
    """
    provider = get_storage_provider()
    try:
        ir_json_str = await provider.get_content(ir_path)
    except (StorageConfigError, StorageReadError) as e:
        workflow_logger.error(f"Failed to read IR file from storage: {ir_path}, {e}")
        raise IRBuildException(
            f"Failed to read IR file from storage: {ir_path}, {e}"
        ) from e

    try:
        return json.loads(ir_json_str)
    except json.JSONDecodeError as e:
        workflow_logger.error(f"IR file JSON format error: {ir_path}, {e}")
        raise IRBuildException(f"IR file JSON format error: {ir_path}, {e}") from e


@execution_app.delete("/v1/orchestration/ir/execute", summary="删除执行实例")
async def delete_ir_execution_instance(req_json: dict):
    """
    Restful API for delete Agent instance and Workflow instance by executionId.
    """
    # Verifying and preprocessing the user request
    try:
        req = DeleteExecutionInstanceRequest.model_validate(req_json)
    except ValidationError as e:
        raise JiuWenBaseException(
            error_code=StatusCode.PARAM_CHECK_FAILED_ERROR.code,
            message=StatusCode.PARAM_CHECK_FAILED_ERROR.errmsg,
        ) from e
    try:
        await AsyncStateManager().delete_state(key=req.conversation_id)
        # 清除 WorkFlow spec缓存
        if req.ir_path:
            await cache_workflow_queue.apop(req.ir_path)
    except JiuWenBaseException:
        raise
    except Exception as e:
        workflow_logger.error("delete state failed: %s", e, exc_info=True)
        raise JiuWenBaseException(
            error_code=StatusCode.WORKFLOW_EXECUTE_ERROR.code,
            message=f"delete state error: {e}",
        ) from e
    return {
        "code": StatusCode.SUCCESS.code,
        "message": StatusCode.SUCCESS.errmsg,
    }


# 注：N2L chat 端点（/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat）
# 已随 agent_builder 抽离到 studio-builder 镜像（agent_builder/serve/apis/n2l_api.py）。


# ── Additional Questions (追问) ──────────────────────────────────────
_additional_questions_service: AdditionalQuestionsService | None = None


def _get_additional_questions_service() -> AdditionalQuestionsService:
    global _additional_questions_service
    if _additional_questions_service is None:
        _additional_questions_service = AdditionalQuestionsService()
    return _additional_questions_service


@execution_app.post(
    "/v1/{project_id}/agents/{agent_id}/conversations/{conversation_id}/additional-questions",
    summary="生成追问（智能体场景）",
)
async def agent_additional_questions(
    project_id: str,
    agent_id: str,
    conversation_id: str,
    workspace_id: str = Query(...),
    req_json: dict = Body(...),
):
    """自动生成追问（Agent 场景）。"""
    ctx = AdditionalQuestionsContext(
        resource_type="agent",
        resource_id=agent_id,
        project_id=project_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
    )
    return await _handle_additional_questions(ctx=ctx, req_json=req_json)


@execution_app.post(
    "/v1/{project_id}/workflows/{workflow_id}/conversations/{conversation_id}/additional-questions",
    summary="生成追问（工作流场景）",
)
async def workflow_additional_questions(
    project_id: str,
    workflow_id: str,
    conversation_id: str,
    workspace_id: str = Query(...),
    req_json: dict = Body(...),
):
    """自动生成追问（Workflow 场景）。"""
    ctx = AdditionalQuestionsContext(
        resource_type="workflow",
        resource_id=workflow_id,
        project_id=project_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
    )
    return await _handle_additional_questions(ctx=ctx, req_json=req_json)


async def _handle_additional_questions(
    ctx: AdditionalQuestionsContext,
    req_json: dict,
):
    """追问接口统一处理入口 — 解析请求、调用 Service、返回响应。"""
    workflow_logger.debug(
        "Additional questions request: resource_type=%s, resource_id=%s, "
        "conversation_id=%s, workspace_id=%s",
        ctx.resource_type, ctx.resource_id, ctx.conversation_id, ctx.workspace_id,
    )
    try:
        req = AdditionalQuestionsRequest.model_validate(req_json)
    except ValidationError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "validation_failed", "details": str(e)},
        )

    service = _get_additional_questions_service()
    try:
        from agent_runtime.context.request_context import _request_ctx
        req_ctx = _request_ctx.get()
        headers = req_ctx.headers if req_ctx else {}
        result = await service.generate(
            ctx=ctx,
            request=req,
            headers=headers,
        )
        return JSONResponse(content=result.model_dump())
    except JiuWenBaseException as e:
        workflow_logger.error(
            "Additional questions error: code=%s, message=%s",
            e.error_code, e.message,
        )
        return JSONResponse(
            status_code=400,
            content={"code": e.error_code, "message": e.message},
        )
    except Exception as e:
        workflow_logger.error(
            "Unexpected error in additional questions: %s", e, exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "details": str(e)},
        )



