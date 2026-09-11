# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""终止端点与 stream_response 注册/注销单元测试（REQ-2026-002）。

覆盖：
- cancel_execution 端点校验矩阵：403（project/入口不匹配，标记不置位）、200（在飞/无在飞幂等）、
  响应五字段（契约 v0.6 §4.1）、403 错误码按入口分流复用两码（OQ-3 定案）；
- stream_response：执行注册（含四元组数据源）与 finally 注销（正常/异常路径）。
"""

# pylint: disable=no-self-use

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.responses import JSONResponse

from agent_runtime.schemas.orchestration_mgr import ExecutionRequest
from agent_runtime.serve.apis import orchestration
from agent_runtime.serve.apis.orchestration import (
    _CODE_AGENT_PERMISSION,
    _CODE_WORKFLOW_PERMISSION,
    StreamEntryContext,
    _build_error_response,
    cancel_execution,
    stream_response,
)


def _sse(event: str, data: dict | None = None) -> bytes:
    payload = {"event": event, "data": data or {}}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


def _make_request(headers: dict | None = None):
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/proj-1/conversations/conv-1/cancel",
        "headers": [
            (k.lower().encode("utf-8"), v.encode("utf-8")) for k, v in (headers or {}).items()
        ],
        "query_string": b"",
    }
    from fastapi import Request

    return Request(scope)


def _make_registry(registration: dict | None):
    registry = MagicMock()
    registry.get_registration = AsyncMock(return_value=registration or {})
    registry.get_suspension = AsyncMock(return_value={})
    registry.mark_cancelled = AsyncMock()
    registry.register = AsyncMock()
    registry.unregister = AsyncMock()
    return registry


def _patch_registry(registry):
    return patch("agent_runtime.serve.apis.orchestration.get_execution_registry", lambda: registry)


def _req(conversation_id: str = "conv-1") -> ExecutionRequest:
    return ExecutionRequest.model_validate({"conversationId": conversation_id, "query": "hi"})


class TestCancelEndpoint403:
    @pytest.mark.asyncio
    async def test_project_mismatch_without_entry_uses_workflow_code(self):
        """仅 project 不匹配（无入口 query）→ 02201020（其 reason 即 projectId 不一致语义）。"""
        registry = _make_registry(
            {"instance_id": "i-1", "project_id": "proj-other", "agent_id": "wf-1", "user_id": "u-1"}
        )
        sentinel = JSONResponse(status_code=403, content={"error_code": "sentinel"})

        with patch("agent_runtime.serve.apis.orchestration._build_error_response") as ber:
            ber.return_value = sentinel
            with _patch_registry(registry):
                resp = await cancel_execution(
                    _make_request({"x-language": "zh-cn"}),
                    project_id="proj-1",
                    conversation_id="conv-1",
                )

        assert resp is sentinel
        ber.assert_called_once_with(403, _CODE_WORKFLOW_PERMISSION, "zh-cn")
        registry.mark_cancelled.assert_not_awaited()  # 403 时不置标记

    @pytest.mark.asyncio
    async def test_agent_entry_mismatch_uses_agent_code(self):
        registry = _make_registry(
            {"instance_id": "i-1", "project_id": "proj-1", "agent_id": "agent-real", "user_id": "u-1"}
        )
        sentinel = JSONResponse(status_code=403, content={"error_code": "sentinel"})

        with patch("agent_runtime.serve.apis.orchestration._build_error_response") as ber:
            ber.return_value = sentinel
            with _patch_registry(registry):
                resp = await cancel_execution(
                    _make_request(), project_id="proj-1", conversation_id="conv-1", agent_id="agent-wrong"
                )

        assert resp is sentinel
        ber.assert_called_once_with(403, _CODE_AGENT_PERMISSION, "zh-cn")
        registry.mark_cancelled.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_workflow_entry_mismatch_uses_workflow_code(self):
        registry = _make_registry(
            {"instance_id": "i-1", "project_id": "proj-1", "agent_id": "wf-real", "user_id": "u-1"}
        )
        sentinel = JSONResponse(status_code=403, content={"error_code": "sentinel"})

        with patch("agent_runtime.serve.apis.orchestration._build_error_response") as ber:
            ber.return_value = sentinel
            with _patch_registry(registry):
                resp = await cancel_execution(
                    _make_request(), project_id="proj-1", conversation_id="conv-1", workflow_id="wf-wrong"
                )

        assert resp is sentinel
        ber.assert_called_once_with(403, _CODE_WORKFLOW_PERMISSION, "zh-cn")

    @pytest.mark.asyncio
    async def test_403_response_uses_run_check_errorrsp_builder(self):
        """未 patch 时经 run_check._build_error_response 构建（ErrorRsp 四字段 + i18n）。"""
        registry = _make_registry(
            {"instance_id": "i-1", "project_id": "proj-other", "agent_id": "wf-1", "user_id": "u-1"}
        )
        with _patch_registry(registry):
            resp = await cancel_execution(
                _make_request({"x-language": "zh-cn"}), project_id="proj-1", conversation_id="conv-1"
            )
        assert resp.status_code == 403
        assert resp.body


class TestCancelEndpoint200:
    @pytest.mark.asyncio
    async def test_running_execution_marked_and_echoed(self):
        registry = _make_registry(
            {"instance_id": "i-1", "project_id": "proj-1", "agent_id": "agent-1", "user_id": "u-1"}
        )

        with _patch_registry(registry):
            resp = await cancel_execution(
                _make_request(), project_id="proj-1", conversation_id="conv-1"
            )

        assert resp.status_code == 200
        body = json.loads(resp.body)
        assert body == {
            "agent_id": "agent-1",
            "conversation_id": "conv-1",
            "cancelled": True,
            "running": True,
            "message": "cancel signal accepted",
        }
        registry.mark_cancelled.assert_awaited_once_with("conv-1")

    @pytest.mark.asyncio
    async def test_no_inflight_suspended_marks_and_succeeds(self):
        """无在飞但有挂起归属快照且 project 匹配（挂起态取消）→ 200 且标记置位（US3 依赖）。"""
        registry = _make_registry(None)
        registry.get_suspension = AsyncMock(return_value={
            "instance_id": "i-1", "project_id": "proj-1", "agent_id": "agent-1", "user_id": "u-1"
        })

        with _patch_registry(registry):
            resp = await cancel_execution(
                _make_request(), project_id="proj-1", conversation_id="conv-none", agent_id="agent-9"
            )

        assert resp.status_code == 200
        body = json.loads(resp.body)
        assert body["cancelled"] is True
        assert body["running"] is False
        registry.mark_cancelled.assert_awaited_once_with("conv-none")

    @pytest.mark.asyncio
    async def test_no_inflight_suspended_project_mismatch_403(self):
        """挂起态归属校验（检视 High×3）：快照 project 与路径不符 → 403、不置位。"""
        registry = _make_registry(None)
        registry.get_suspension = AsyncMock(return_value={
            "instance_id": "i-1", "project_id": "proj-owner", "agent_id": "agent-1", "user_id": "u-1"
        })

        with _patch_registry(registry):
            resp = await cancel_execution(
                _make_request({"x-language": "zh-cn"}),
                project_id="proj-1", conversation_id="conv-none",
            )

        assert resp.status_code == 403
        registry.mark_cancelled.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_inflight_no_suspension_is_noop(self):
        """无在飞且无挂起快照（从未执行/已结束）→ 200 幂等放行但**不置位标记**
        （检视①：否则任意 conv id 可跨项目污染 cancel:true，误伤该会话后续挂起恢复）。
        """
        registry = _make_registry(None)
        registry.get_suspension = AsyncMock(return_value={})

        with _patch_registry(registry):
            resp = await cancel_execution(
                _make_request(), project_id="proj-1", conversation_id="conv-none", agent_id="agent-9"
            )

        assert resp.status_code == 200
        body = json.loads(resp.body)
        assert body["cancelled"] is True
        assert body["running"] is False
        assert body["agent_id"] == "agent-9"  # 无注册记录时回显调用方传入的入口 ID
        registry.mark_cancelled.assert_not_awaited()  # 关键断言：无意义取消不留痕

    @pytest.mark.asyncio
    async def test_project_match_with_entry_match_passes(self):
        registry = _make_registry(
            {"instance_id": "i-1", "project_id": "proj-1", "agent_id": "agent-1", "user_id": "u-1"}
        )

        with _patch_registry(registry):
            resp = await cancel_execution(
                _make_request(), project_id="proj-1", conversation_id="conv-1", agent_id="agent-1"
            )

        assert resp.status_code == 200


class TestStreamRegistration:
    class _FakeRunner:
        def __init__(self, chunks):
            self._chunks = chunks

        async def run_streaming(self, req, execution_id):
            for chunk in self._chunks:
                yield chunk

    class _BrokenRunner:
        async def run_streaming(self, req, execution_id):
            raise RuntimeError("boom")
            yield  # pragma: no cover - 不可达但语法必需：无 yield 则为 coroutine，
            # stream_response 的 async for 将抛 TypeError 而非期望的 RuntimeError

    async def _collect(self, gen):
        out = []
        async for frame in gen:
            out.append(frame)
        return out

    @pytest.mark.asyncio
    async def test_registers_with_entry_id_and_unregisters_in_finally(self):
        registry = _make_registry(None)

        with _patch_registry(registry):
            frames = await self._collect(
                stream_response(_req(), "exec-1", self._FakeRunner([_sse("message")]), entry=StreamEntryContext(entry_id="agent-1"))
            )

        assert len(frames) == 2  # message + 兜底 done
        registry.register.assert_awaited_once()
        (conv_id, task, exec_id), kwargs = registry.register.await_args
        assert conv_id == "conv-1"
        assert exec_id == "exec-1"
        reg_info = kwargs["info"]  # RegistrationInfo（G.FNM.03 参数封装）
        assert reg_info.agent_id == "agent-1"
        assert reg_info.project_id == ""  # 无 _request_ctx 时防御为空串
        registry.unregister.assert_awaited_once_with("conv-1", task=task)

    @pytest.mark.asyncio
    async def test_unregister_called_on_runner_exception(self):
        """执行异常路径 finally 注销仍生效（无注册残留）。"""
        registry = _make_registry(None)

        with _patch_registry(registry), pytest.raises(RuntimeError):
            await self._collect(
                stream_response(_req(), "exec-1", self._BrokenRunner(), entry=StreamEntryContext(entry_id="agent-1"))
            )

        registry.register.assert_awaited_once()
        registry.unregister.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_registration_uses_request_context_ids(self):
        """_request_ctx 存在时四元组取 ctx 的 project_id/user_id（协程隔离数据源）。"""
        registry = _make_registry(None)
        ctx = MagicMock(project_id="proj-ctx", user_id="user-ctx")
        token = orchestration._request_ctx.set(ctx)
        try:
            with _patch_registry(registry):
                await self._collect(
                    stream_response(_req(), "exec-1", self._FakeRunner([_sse("message")]), entry=StreamEntryContext(entry_id="wf-1"))
                )
        finally:
            orchestration._request_ctx.reset(token)

        _, kwargs = registry.register.await_args
        reg_info = kwargs["info"]  # RegistrationInfo（G.FNM.03 参数封装）
        assert reg_info.project_id == "proj-ctx"
        assert reg_info.user_id == "user-ctx"
        assert reg_info.agent_id == "wf-1"
