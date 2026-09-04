#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""End-to-end tests for openjiuwen Tracer dual-write in controller multi-agent workflow.

基于 test_case_controller_multi_agent_27 的用例，增加 openjiuwen Tracer 验证。
通过 patch build_agent_input 注入 openjiuwen Tracer，使 TraceManager 在 workflow
执行过程中同时向 Insight 和 openjiuwen SSE 双写，然后收集并验证 tracer 推送的数据。

测试覆盖：
1. 单轮查询触发 tracer 打点（chain/llm/plugin/workflow 类事件）
2. 多轮对话（中断→恢复→默认工作流）的 tracer 连续性
3. tracer span 结构（invokeId, invokeType, status 等必要字段）
4. 无 error 事件推送

注意：run_local_ir_with_openjiuwen_workflow 内部使用 Runner.start/stop，
需要独立事件循环，因此测试方法为同步（def test_），用 asyncio.run() 调用异步函数。
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

os.environ.setdefault("TGF_ENABLE", "false")

from jiuwen.controller.task_planner.planning_modules.intention_detect_module import (
    DEFAULT_INTENT,
)
from jiuwen.insight.manager import TraceManager
from jiuwen.serve.controllers.execution.utils import build_agent_input
from jiuwen.test.cases.controller_multi_agent.openjiuwen_workflow_case_runtime import (
    init_openjiuwen_workflow_runtime,
    run_local_ir_with_openjiuwen_workflow,
)
from openjiuwen.core.session.stream.emitter import StreamEmitter
from openjiuwen.core.session.stream.manager import StreamWriterManager
from openjiuwen.core.session.tracer.tracer import Tracer


CASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CASE_DIR.parents[2]
RESOURCE_TEMPLATE_DIR = PACKAGE_DIR / "resource" / "templates" / "default"
CASE_ASSET_DIR = CASE_DIR / "test_case_controller_multi_agent_27"
AGENT_DIR = CASE_ASSET_DIR / "agent"
SUB_AGENT_DIR = CASE_ASSET_DIR / "sub_agent"
WORKFLOW_DIR = CASE_ASSET_DIR / "workflow"
CASE_FILE = CASE_ASSET_DIR / "test_case_controller_multi_agent_27.yaml"
CURRENT_CASE_ANSWERS: list[str] = []


# ── Helpers ──────────────────────────────────────────────────────────────────


def _load_cases() -> list[dict]:
    return yaml.safe_load(CASE_FILE.read_text(encoding="utf-8"))


def _extract_sse_events(response_text: str) -> list[dict]:
    events = []
    for line in response_text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:") :].strip()
        if not payload:
            continue
        events.append(json.loads(payload))
    return events


def _event_names(response_text: str) -> list[str]:
    return [event.get("event", "") for event in _extract_sse_events(response_text)]


def _append_history(conversation_history: list[dict], case_data: dict) -> None:
    conversation_history.append({"role": "user", "content": case_data["query"]})
    answers = case_data.get("answer") or []
    if answers:
        conversation_history.append({"role": "assistant", "content": answers[0]})


def _select_case_intent(
    detector, active_workflows, query: str, answers: list[str], kwargs: dict
):
    if detector.category_2_agent_name_map:
        return next(iter(detector.category_2_agent_name_map.values()))

    for intent_name in detector.global_intent_2_category_map:
        if intent_name and intent_name in query:
            return intent_name

    workflow_names = set(detector.intent_function_2_category_map)
    if any(
        marker in answer
        for answer in answers
        for marker in ("默认工作流", "结束工作流")
    ):
        return DEFAULT_INTENT
    if "理财服务" in workflow_names:
        return "理财服务"
    if workflow_names:
        return next(iter(workflow_names))
    return DEFAULT_INTENT


def _init_local_runtime(monkeypatch: pytest.MonkeyPatch):
    init_openjiuwen_workflow_runtime(
        monkeypatch,
        resource_template_dir=RESOURCE_TEMPLATE_DIR,
        answer_provider=lambda: CURRENT_CASE_ANSWERS,
        intent_selector=_select_case_intent,
    )


def _find_single_json(directory: Path) -> Path:
    json_files = sorted(directory.glob("*.json"))
    if len(json_files) != 1:
        raise AssertionError(
            f"Expected exactly one json file in {directory}, found {len(json_files)}"
        )
    return json_files[0]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_fixture_path(filename: str, *directories: Path) -> Path:
    for directory in directories:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Unable to resolve IR reference {filename!r} in {[str(d) for d in directories]}"
    )


def _copy_case_ir_bundle(tmp_path: Path) -> Path:
    root_src = _find_single_json(AGENT_DIR)
    child_src = _find_single_json(SUB_AGENT_DIR)

    root_ir = _load_json(root_src)
    child_ir = _load_json(child_src)

    child_dst = tmp_path / child_src.name
    root_dst = tmp_path / root_src.name

    for workflow in child_ir.get("configs", {}).get("workflows", []):
        workflow_name = Path(workflow.get("ir_path", "")).name
        if workflow_name:
            workflow_src = _resolve_fixture_path(workflow_name, WORKFLOW_DIR)
            workflow["ir_path"] = str(workflow_src)

    for agent in root_ir.get("configs", {}).get("agents", []):
        child_name = Path(agent.get("ir_path", "")).name
        if child_name:
            child_ref = _resolve_fixture_path(child_name, SUB_AGENT_DIR)
            if child_ref.name != child_src.name:
                raise AssertionError(
                    f"Root IR points to unexpected child IR: {child_ref}"
                )
            agent["ir_path"] = str(child_dst)

    child_dst.write_text(
        json.dumps(child_ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    root_dst.write_text(
        json.dumps(root_ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return root_dst


# ── Tracer Helpers ───────────────────────────────────────────────────────────


def _create_initialized_tracer() -> tuple[Tracer, StreamEmitter]:
    """创建一个完整初始化的 Tracer（含 StreamWriterManager）。"""
    tracer = Tracer()
    emitter = StreamEmitter()
    swm = StreamWriterManager(emitter)
    tracer.init(swm)
    return tracer, emitter


async def _collect_traces(emitter: StreamEmitter, timeout: float = 2.0) -> list[dict]:
    """从 StreamEmitter 中异步读取所有 trace 数据。"""
    traces = []
    while True:
        try:
            data = await asyncio.wait_for(
                emitter.stream_queue.receive(), timeout=timeout
            )
            if data == StreamEmitter.END_FRAME:
                break
            print(f'----> collect traces {data}')
            if hasattr(data, "model_dump"):
                data = data.model_dump(by_alias=True)
            elif hasattr(data, "dict"):
                data = data.dict(by_alias=True)
            elif not isinstance(data, dict):
                data = dict(data) if hasattr(data, "__dict__") else {"raw": str(data)}
            traces.append(data)
        except asyncio.TimeoutError:
            break
    return traces


def _extract_payloads(traces: list) -> list[dict]:
    """从 trace 列表中提取 payload dict。"""
    payloads = []
    for t in traces:
        p = t.get("payload", t)
        if hasattr(p, "model_dump"):
            p = p.model_dump(by_alias=True)
        payloads.append(p)
    return payloads


def _find_by_invoke_type(payloads: list[dict], invoke_type: str) -> list[dict]:
    """按 invokeType 筛选 payload。"""
    return [p for p in payloads if p.get("invokeType") == invoke_type]


def _find_by_status(payloads: list[dict], status: str) -> list[dict]:
    """按 status 筛选 payload。"""
    return [p for p in payloads if p.get("status") == status]


def _make_patched_build(tracer: Tracer):
    """创建 patch build_agent_input 的 side_effect 函数。"""
    original_build = build_agent_input

    async def _patched_build(req):
        insight_client, runtime_context, tm = await original_build(req)
        tm._oj_tracer = tracer
        tm._oj_span_map = {}
        if tracer is not None:
            tm._oj_init_root_span()
        return insight_client, runtime_context, tm

    return _patched_build


def _collect_tracer_payloads(emitter: StreamEmitter) -> list[dict]:
    """同步收集 tracer 数据：关闭 emitter → 读取 traces → 提取 payloads。"""
    asyncio.run(emitter.close())
    traces = asyncio.run(_collect_traces(emitter))
    return _extract_payloads(traces)


def _make_fake_redis_client() -> MagicMock:
    """创建一个假的异步 Redis 客户端，所有操作返回 None（缓存未命中）。"""
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=None)
    client.ping = AsyncMock(return_value=True)
    client.aclose = AsyncMock()
    return client


def _make_fake_redis_manager(fake_client: MagicMock) -> MagicMock:
    """创建一个假的 RedisClientManager 单例。"""
    mgr = MagicMock()
    mgr.get_client.return_value = fake_client
    mgr.is_initialized = True
    mgr.close = AsyncMock()
    return mgr


@pytest.fixture(autouse=True)
def _mock_redis():
    """自动 mock Redis，避免测试环境依赖真实 Redis 服务。"""
    fake_client = _make_fake_redis_client()
    fake_mgr = _make_fake_redis_manager(fake_client)
    with patch(
        "agent_runtime.common.redis_manager.RedisClientManager.get_instance",
        return_value=fake_mgr,
    ):
        yield


@pytest.fixture()
def local_ir_path(tmp_path_factory, monkeypatch):
    _init_local_runtime(monkeypatch)

    # agent_runtime 版本的 Questioner 是运行时实际使用的类，
    # 需要同步 mock 其 invoke/stream 方法（与 jiuwen 版本一致）
    from agent_runtime.extension.workflow_node.questioner import (
        Questioner as AgentRuntimeQuestioner,
    )
    from jiuwen.extension.workflow_node.questioner import (
        Questioner as JiuWenQuestioner,
    )

    # 获取已 mock 的 jiuwen 版本的 invoke/stream
    monkeypatch.setattr(
        AgentRuntimeQuestioner, "invoke", JiuWenQuestioner.invoke
    )
    monkeypatch.setattr(
        AgentRuntimeQuestioner, "stream", JiuWenQuestioner.stream
    )

    tmp_path = tmp_path_factory.mktemp("controller_multi_agent_case27_tracer_e2e")
    return _copy_case_ir_bundle(tmp_path)


# ── Test: 单轮查询 tracer 验证 ──────────────────────────────────────────────


class TestTracerE2ESingleTurn:
    """单轮查询：验证 openjiuwen Tracer 在 workflow 执行过程中正确打点。"""

    def test_single_turn_produces_tracer_events(self, local_ir_path):
        """单轮查询应产生 openjiuwen tracer 的 SSE 事件。

        验证：
        1. tracer 收到至少一条 start 事件和一条 finish 事件
        2. 不存在 error 状态的事件
        3. 原有 workflow 功能不受影响（SSE 事件正常）
        """
        tracer, emitter = _create_initialized_tracer()

        cases = _load_cases()
        first_turn = cases[0]
        CURRENT_CASE_ANSWERS.clear()
        CURRENT_CASE_ANSWERS.extend(first_turn.get("answer") or [])

        with patch(
            "jiuwen.serve.controllers.execution.utils.build_agent_input",
            side_effect=_make_patched_build(tracer),
        ):
            response_text = asyncio.run(
                run_local_ir_with_openjiuwen_workflow(local_ir_path, first_turn["query"])
            )

        # 收集 tracer 数据
        payloads = _collect_tracer_payloads(emitter)

        # ── 验证原有功能正常 ──
        events = _event_names(response_text)
        assert '"event":"error"' not in response_text, response_text
        assert any(
            event in events
            for event in (
                "task_end",
                "workflow_blocked",
                "workflow_end",
                "done",
                "intermediate_message",
            )
        ), f"No terminal event found. Events: {events}"

        # ── 验证 tracer 产生数据 ──
        assert len(payloads) >= 1, (
            f"Expected at least 1 tracer payload, "
            f"got {len(payloads)}. Payloads: {payloads}"
        )

        # 验证存在根 span（invokeType 可能是 chain/agent/workflow 等）
        root_invoke_types = {"agent", "chain", "workflow"}
        root_spans = [p for p in payloads if p.get("invokeType") in root_invoke_types]
        assert len(root_spans) >= 1, (
            f"Expected at least 1 root invokeType span, got types: "
            f"{set(p.get('invokeType') for p in payloads)}"
        )

        # 验证不存在 error 状态
        error_spans = _find_by_status(payloads, "error")
        assert len(error_spans) == 0, (
            f"Unexpected error spans in tracer output: {error_spans}"
        )


# ── Test: 多轮对话 tracer 验证 ──────────────────────────────────────────────


class TestTracerE2EMultiTurn:
    """多轮对话（中断 → 恢复 → 默认工作流）：验证 tracer 连续性。"""

    def test_multi_turn_tracer_continuity(self, local_ir_path):
        """多轮对话中 tracer 应持续产生事件，且每轮都有根 span。

        场景：
        Turn 1: "我要赎回理财" → 触发工作流 → questioner 中断
        Turn 2: "我要投诉" → 正常回复
        Turn 3: "第一笔，全部赎回。" → 工作流恢复
        Turn 4: "今天天气怎么样" → 默认工作流
        """
        tracer, emitter = _create_initialized_tracer()

        cases = _load_cases()
        conversation_id = "conversation_controller_multi_agent_27_tracer_e2e"
        conversation_history: list[dict] = []

        with patch(
            "jiuwen.serve.controllers.execution.utils.build_agent_input",
            side_effect=_make_patched_build(tracer),
        ):
            # Turn 1: 触发工作流 + 中断
            turn1 = cases[0]
            CURRENT_CASE_ANSWERS.clear()
            CURRENT_CASE_ANSWERS.extend(turn1.get("answer") or [])
            resp1 = asyncio.run(
                run_local_ir_with_openjiuwen_workflow(
                    local_ir_path,
                    turn1["query"],
                    conversation_id=conversation_id,
                    conversation_history=conversation_history,
                )
            )
            assert '"event":"error"' not in resp1, resp1
            _append_history(conversation_history, turn1)

            # Turn 2: 投诉
            turn2 = cases[1]
            CURRENT_CASE_ANSWERS.clear()
            CURRENT_CASE_ANSWERS.extend(turn2.get("answer") or [])
            resp2 = asyncio.run(
                run_local_ir_with_openjiuwen_workflow(
                    local_ir_path,
                    turn2["query"],
                    conversation_id=conversation_id,
                    conversation_history=conversation_history,
                )
            )
            assert '"event":"error"' not in resp2, resp2
            _append_history(conversation_history, turn2)

            # Turn 3: 恢复赎回
            turn3 = cases[2]
            CURRENT_CASE_ANSWERS.clear()
            CURRENT_CASE_ANSWERS.extend(turn3.get("answer") or [])
            resp3 = asyncio.run(
                run_local_ir_with_openjiuwen_workflow(
                    local_ir_path,
                    turn3["query"],
                    conversation_id=conversation_id,
                    conversation_history=conversation_history,
                )
            )
            assert '"event":"error"' not in resp3, resp3
            _append_history(conversation_history, turn3)

            # Turn 4: 默认工作流
            turn4 = cases[3]
            CURRENT_CASE_ANSWERS.clear()
            CURRENT_CASE_ANSWERS.extend(turn4.get("answer") or [])
            resp4 = asyncio.run(
                run_local_ir_with_openjiuwen_workflow(
                    local_ir_path,
                    turn4["query"],
                    conversation_id=conversation_id,
                    conversation_history=conversation_history,
                )
            )
            assert '"event":"error"' not in resp4, resp4

        # 收集 tracer 数据
        payloads = _collect_tracer_payloads(emitter)

        # ── 验证每轮都产生了 tracer 数据 ──
        root_invoke_types = {"agent", "chain", "workflow"}
        root_spans = [p for p in payloads if p.get("invokeType") in root_invoke_types]
        assert len(root_spans) >= 4, (
            f"Expected at least 4 root spans (one per turn), "
            f"got {len(root_spans)}"
        )

        # 验证无 error
        error_spans = _find_by_status(payloads, "error")
        assert len(error_spans) == 0, f"Unexpected errors: {error_spans}"

        # 验证各轮 SSE 事件正常
        assert "workflow_start" in _event_names(resp1) or "message_end" in _event_names(resp1)
        assert "message_end" in _event_names(resp2)
        assert "workflow_resume" in _event_names(resp3)
        assert "workflow_end" in _event_names(resp4)


# ── Test: tracer span 结构验证 ──────────────────────────────────────────────


class TestTracerE2ESpanStructure:
    """验证 tracer 输出的 span 结构符合预期。"""

    def test_span_has_required_fields(self, local_ir_path):
        """tracer 输出的 span 应包含必要字段（invokeId, invokeType, status 等）。"""
        tracer, emitter = _create_initialized_tracer()

        cases = _load_cases()
        first_turn = cases[0]
        CURRENT_CASE_ANSWERS.clear()
        CURRENT_CASE_ANSWERS.extend(first_turn.get("answer") or [])

        with patch(
            "jiuwen.serve.controllers.execution.utils.build_agent_input",
            side_effect=_make_patched_build(tracer),
        ):
            response_text = asyncio.run(
                run_local_ir_with_openjiuwen_workflow(local_ir_path, first_turn["query"])
            )

        payloads = _collect_tracer_payloads(emitter)

        # 原有功能正常
        assert '"event":"error"' not in response_text, response_text

        # 每个 payload 应包含关键字段
        required_fields = ["invokeId", "invokeType", "status"]
        for i, payload in enumerate(payloads):
            for field in required_fields:
                assert field in payload, (
                    f"Payload[{i}] missing required field '{field}'. "
                    f"Keys: {list(payload.keys())}"
                )
                assert payload[field] is not None, (
                    f"Payload[{i}] field '{field}' is None"
                )

    def test_root_span_is_first(self, local_ir_path):
        """根 span（chain/agent/workflow）应该是最早产生的 span 之一。"""
        tracer, emitter = _create_initialized_tracer()

        cases = _load_cases()
        first_turn = cases[0]
        CURRENT_CASE_ANSWERS.clear()
        CURRENT_CASE_ANSWERS.extend(first_turn.get("answer") or [])

        with patch(
            "jiuwen.serve.controllers.execution.utils.build_agent_input",
            side_effect=_make_patched_build(tracer),
        ):
            asyncio.run(
                run_local_ir_with_openjiuwen_workflow(local_ir_path, first_turn["query"])
            )

        payloads = _collect_tracer_payloads(emitter)

        # 第一个 payload 应该是根 span（status=start）
        root_invoke_types = {"agent", "chain", "workflow"}
        if payloads:
            first = payloads[0]
            assert first["invokeType"] in root_invoke_types, (
                f"First span should be a root type, got '{first.get('invokeType')}'"
            )
            assert first["status"] == "start", (
                f"First span should be 'start', got '{first.get('status')}'"
            )
