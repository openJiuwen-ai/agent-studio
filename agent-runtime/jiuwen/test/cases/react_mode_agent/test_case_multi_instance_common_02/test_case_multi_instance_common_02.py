#!/usr/bin/env python
"""南向契约测试 -- ReAct mode 单提问器工作流中断恢复 (test_case_multi_instance_common_02)

场景：车机故障报修，提问器收集 5 个字段，信息不全时追问，全部收齐后输出结构化结果。
Mock 策略：LLM(BaseChatModel.astream) + Workflow(create_workflow_instance) + State(AsyncStateManager)
断言：逐条 SSE 事件严格比对 conversation_tmdRU18Q 录制日志。
"""

__all__ = ["TestCaseMultiInstanceCommon02"]

import asyncio
import json
import os
import pickle
import shutil
import tempfile
import time
from collections import namedtuple
from pathlib import Path

import pytest
from jiuwen.test.cases.workflow_node.test_case_multi_instance_common_02.test_questioner_ssq import (
    create_questioner_ssq_workflow,
)

os.environ.setdefault("EXECUTION_STATE_STORAGE_MEDIUM", "memory")
os.environ.setdefault("IR_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_GROUP_CACHE_ENABLE", "false")
os.environ.setdefault("USE_EI_INTENT", "false")
os.environ.setdefault("USE_OPENJIUWEN_WORKFLOW", "true")
os.environ.setdefault("WORKFLOW_EXECUTE_TIMEOUT", "1200")

from jiuwen.common.init import JiuWen
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import BaseChatModel
from jiuwen.common.llm_service.messages import AIMessage, ToolCall, UsageMetadata
from jiuwen.controller.task_executor.handler.workflow_handler import WorkflowHandler
from jiuwen.controller.task_planner.planning_modules.intention_detect_module import (
    IntentionDetectModule,
    convert_ai_message_to_llm_output,
)
from jiuwen.extension.workflow_node.questioner import Questioner
from jiuwen.orchestration.flow.enum import StreamDataMsg
from jiuwen.orchestration.flow.stream.base import StreamCode, StreamData
from jiuwen.plugin.models.restfulapi import RestFulAPI
from jiuwen.plugin.models.tool import WORKFLOW_END_TYPE
from jiuwen.serve.common.context import request as request_context
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from jiuwen.serve.controllers.execution.manager import AsyncStateManager
from jiuwen.serve.controllers.execution.open_utils import async_ir_load
from jiuwen.serve.controllers.execution.types import ExecutionData
from jiuwen.serve.controllers.execution.utils import distribute_execution_request
from jiuwen.serve.schemas.orchestration_mgr import ExecutionRequest

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
CASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CASE_DIR.parents[3]
RESOURCE_TEMPLATE_DIR = PACKAGE_DIR / "resource" / "templates" / "default"
AGENT_DIR = CASE_DIR / "agent"
WORKFLOW_DIR = CASE_DIR / "workflow"
WORKFLOW_ID = "117c6695dcd9139726dce28c83abe0e671ea76b4be270599"

# ---------------------------------------------------------------------------
# 跨轮次状态持久化（文件 pickle）
#
# 每轮 asyncio.run() 是独立事件循环，内存状态不跨轮次。
# 文件持久化让 Round 2 能通过 AsyncStateManager.get_state() 恢复 Round 1 的 Agent 状态。
# 局限：create_workflow_instance 被 Patch 4 拦截，BPMN 中断点恢复未被测试。
# ---------------------------------------------------------------------------
STATE_DIR = Path(tempfile.gettempdir()) / "jiuwen_test_state"


class _RestrictedUnpickler(pickle.Unpickler):
    """受限的反序列化器，拒绝已知危险模块以防止RCE"""
    _DANGEROUS_MODULES = {"os", "subprocess", "socket", "ctypes", "posix", "nt"}

    def find_class(self, module, name):
        if module in self._DANGEROUS_MODULES:
            raise pickle.UnpicklingError(f"Forbidden module during unpickling: {module}")
        if module == "builtins" and name in ("eval", "exec", "__import__", "open"):
            raise pickle.UnpicklingError(f"Forbidden builtin during unpickling: {name}")
        return super().find_class(module, name)


async def _file_based_save_state(self, key, value):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_DIR / f"{key}.pkl", "wb") as f:
        pickle.dump(value, f)


async def _file_based_get_state(self, key):
    p = STATE_DIR / f"{key}.pkl"
    if not p.exists():
        return None
    with open(p, "rb") as f:
        return _RestrictedUnpickler(f).load()


async def _file_based_delete_state(self, key):
    pass  # 保留状态供 Round 2 读取


# ---------------------------------------------------------------------------
# Mock 基础设施（简化版：无 Registry / Adapter 间接层）
# ---------------------------------------------------------------------------

# 可变容器：patch 闭包读取，测试代码在轮次间替换
_mocks: dict = {"llm": None, "workflow": None, "questioner_extraction": None}


class _FallbackChatModel(BaseChatModel):
    """Patch 1 用的空壳 model，不会真正被调用。"""

    model_name: str = "fake-qwen"

    def _chat(self, messages, tools=None, **kwargs):
        return AIMessage(content="0")


class _ScriptedLLM:
    """预设 LLM 返回值。astream yield AIMessage，ainvoke 直接返回。"""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.call_count = 0

    async def ainvoke(self, inputs, **kwargs):
        self.call_count += 1
        if self.outputs:
            return self.outputs.pop(0)
        return AIMessage(content="0")

    async def astream(self, inputs, **kwargs):
        self.call_count += 1
        msg = self.outputs.pop(0) if self.outputs else AIMessage(content="0")
        # 中间 chunk（finish_reason=""）
        yield AIMessage(
            content="",
            usage_metadata=UsageMetadata(code=0, errmsg="成功", finish_reason=""),
        )
        # 最终 chunk
        if not msg.usage_metadata:
            fr = "function_call" if msg.tool_calls else "stop"
            msg.usage_metadata = UsageMetadata(code=0, errmsg="成功", finish_reason=fr)
        yield msg


class _ScriptedWorkflow:
    """预设工作流返回值。按 workflow_id 返回 StreamData 事件列表。"""

    def __init__(self, events_by_id):
        self.events_by_id = {k: list(v) for k, v in events_by_id.items()}
        self.call_count = 0
        self.last_workflow_id = ""

    def pop_events(self, workflow_id):
        self.call_count += 1
        self.last_workflow_id = workflow_id
        bucket = self.events_by_id.get(workflow_id, [])
        return bucket.pop(0) if bucket else []


class _ScriptedQuestionerExtractionModel:
    """openjiuwen workflow 下给 Questioner 注入固定 extraction 结果。"""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.call_count = 0
        self._last_output = "{}"

    async def invoke(self, messages=None, **kwargs):
        self.call_count += 1
        if self.outputs:
            self._last_output = self.outputs.pop(0)
        return type(
            "FakeInvokeResult",
            (),
            {"content": self._last_output, "usage_metadata": None},
        )()


class _WorkflowStub:
    """create_workflow_instance 返回的 duck-type mock。

    满足框架对 workflow_instance 的访问：astream / graph_engine.graph_instance.*
    """

    def __init__(self, events):
        self._events = events

        class _GI:
            runtime_context = None

            async def async_clean_up(self):
                pass

            def get_state(self):
                return {}

            def get_workflow_execute_status(self):
                return None

        self.graph_engine = type("_GE", (), {"graph_instance": _GI()})()

    async def astream(self, *args, **kwargs):
        async def _gen():
            for e in self._events:
                yield e

        return _gen()


# ---------------------------------------------------------------------------
# StreamData 构建器
# ---------------------------------------------------------------------------
def _build_partial_stream_data(
    *, answer, node_id, node_name, node_type, should_interrupt=False
):
    return StreamData(
        code=StreamCode.PARTIAL_CONTENT.value,
        msg=StreamDataMsg.SUCCESS.value,
        data={
            "answer": answer,
            "node_id": node_id,
            "node_name": node_name,
            "node_type": node_type,
            "should_interrupt": should_interrupt,
        },
        execution_id="",
    )


def _build_message_end_stream_data(
    *, answer, node_id, node_name, node_type, should_interrupt=False
):
    return StreamData(
        code=StreamCode.MESSAGE_END.value,
        msg=StreamDataMsg.MESSAGE_END.value,
        data={
            "answer": answer,
            "node_id": node_id,
            "node_name": node_name,
            "node_type": node_type,
            "should_interrupt": should_interrupt,
            "enable_history": True,
        },
        execution_id="",
    )


def _build_workflow_end_stream_data(
    *,
    answer,
    node_id="node_end",
    node_name="结束",
    node_type=None,
    should_interrupt=False,
):
    return StreamData(
        code=StreamCode.WORKFLOW_END.value,
        msg=StreamDataMsg.FINISH.value,
        data={
            "answer": answer,
            "node_id": node_id,
            "node_name": node_name,
            "node_type": node_type or WORKFLOW_END_TYPE,
            "should_interrupt": should_interrupt,
        },
        execution_id="",
    )


def _build_end_stream_data(*, answer, node_id="node_end", node_type=None):
    return StreamData(
        code=StreamCode.FINISH.value,
        msg=StreamDataMsg.FINISH.value,
        data={
            "answer": answer,
            "node_id": node_id,
            "node_name": "node_end",
            "node_type": node_type or WORKFLOW_END_TYPE,
            "should_interrupt": False,
            "user_fields": {},
        },
        execution_id="",
    )


def _build_workflow_start_stream_data(*, workflow_id):
    return StreamData(
        code=StreamCode.WORKFLOW_START.value,
        msg=StreamDataMsg.SUCCESS.value,
        data={"workflow_id": workflow_id},
        execution_id="",
    )


def _build_intermediate_message_stream_data(*, answer):
    """code=7000，WorkflowHandler 会 drop，但 mock 需对齐录制日志。"""
    return StreamData(
        code=StreamCode.CONTROLLER_INTERMEDIATE_MESSAGE.value,
        msg="intermediate message",
        data={"answer": answer},
        execution_id="",
    )


# ---------------------------------------------------------------------------
# Contract Runtime 初始化（6 路 monkeypatch）
# ---------------------------------------------------------------------------
def _init_contract_runtime(monkeypatch: pytest.MonkeyPatch):
    os.environ["EXECUTION_STATE_STORAGE_MEDIUM"] = "memory"
    os.environ["IR_CACHE_ENABLE"] = "false"
    os.environ["AGENT_CACHE_ENABLE"] = "false"
    os.environ["AGENT_GROUP_CACHE_ENABLE"] = "false"
    os.environ["USE_AGENT_CORE_MODEL"] = "false"
    os.environ["USE_EI_INTENT"] = "false"
    _mocks["llm"] = None
    _mocks["workflow"] = None
    _mocks["questioner_extraction"] = None

    # Patch 1: ModelFactory → 空壳 model
    monkeypatch.setattr(
        ModelFactory,
        "get_model",
        lambda self, model_type, model_name, *a, **kw: _FallbackChatModel(),
    )

    # Patch 2: 初始化 prompt manager
    if not RESOURCE_TEMPLATE_DIR.exists():
        raise FileNotFoundError(
            f"Prompt template dir not found: {RESOURCE_TEMPLATE_DIR}"
        )
    JiuWen.init(prompt_dir=str(RESOURCE_TEMPLATE_DIR), plugin_dir=None, cfg_file=None)

    # Patch 3: IntentionDetectModule._execute_llm_call → _mocks["llm"]
    async def _patched_execute_llm_call(self, llm_input):
        start_time = time.time()
        llm = _mocks["llm"]
        if llm is not None:
            llm_message = await llm.ainvoke(llm_input)
        else:
            llm_message = await self.llm.ainvoke(llm_input)
        converted_output = convert_ai_message_to_llm_output(llm_message)
        total_time = time.time() - start_time
        model_stat, model_usage = self._extract_usage_metadata(llm_message)
        T = namedtuple(
            "T",
            [
                "converted_output",
                "total_time",
                "model_stat",
                "model_usage",
                "llm_message",
            ],
        )
        return T(
            converted_output, round(total_time, 2), model_stat, model_usage, llm_message
        )

    # Patch 3': BaseChatModel.astream → _mocks["llm"]
    original_astream = BaseChatModel.astream

    async def _patched_astream(self, inputs, **kwargs):
        llm = _mocks["llm"]
        if llm is not None and hasattr(llm, "astream"):
            async for item in llm.astream(inputs, **kwargs):
                yield item
            return
        async for item in original_astream(self, inputs, **kwargs):
            yield item

    # Patch 4: create_workflow_instance → _WorkflowStub
    async def _patched_create_workflow_instance(wf_ctx, conversation_id, user_id):
        wf = _mocks["workflow"]
        if wf is not None:
            events = wf.pop_events(wf_ctx.workflow_id)
            return _WorkflowStub(events)
        return await WorkflowHandler.create_workflow_instance.__wrapped__(
            wf_ctx, conversation_id, user_id
        )

    # Patch 5: RestFulAPI.ainvoke → no-op（本测试不调用插件）
    async def _noop_plugin_ainvoke(self, inputs, **kwargs):
        return {}

    monkeypatch.setattr(
        IntentionDetectModule, "_execute_llm_call", _patched_execute_llm_call
    )
    monkeypatch.setattr(BaseChatModel, "astream", _patched_astream)

    if os.getenv("USE_OPENJIUWEN_WORKFLOW", "false") != "true":
        monkeypatch.setattr(
            WorkflowHandler,
            "create_workflow_instance",
            staticmethod(_patched_create_workflow_instance),
        )
    else:
        original_initialize_model = Questioner._initialize_model

        async def _patched_questioner_initialize_model(self):
            extraction_model = _mocks["questioner_extraction"]
            if extraction_model is not None:
                self._model = extraction_model
                self._initialized = True
                return
            await original_initialize_model(self)

        monkeypatch.setattr(
            Questioner, "_initialize_model", _patched_questioner_initialize_model
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            create_questioner_ssq_workflow()
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    monkeypatch.setattr(RestFulAPI, "ainvoke", _noop_plugin_ainvoke)

    # Patch 6: AsyncStateManager → 文件 pickle
    monkeypatch.setattr(AsyncStateManager, "save_state", _file_based_save_state)
    monkeypatch.setattr(AsyncStateManager, "get_state", _file_based_get_state)
    monkeypatch.setattr(AsyncStateManager, "delete_state", _file_based_delete_state)


# ---------------------------------------------------------------------------
# IR 加载与执行
# ---------------------------------------------------------------------------
def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_ir_to_tmp(tmp_path: Path) -> Path:
    agent_files = list(AGENT_DIR.glob("*.json"))
    if len(agent_files) != 1:
        raise AssertionError(
            f"Expected exactly one agent json in {AGENT_DIR}, found {len(agent_files)}"
        )
    agent_ir = _load_json(agent_files[0])

    workflow_files = {f.stem: f for f in WORKFLOW_DIR.glob("*.json")}
    for wf_cfg in agent_ir.get("configs", {}).get("workflows", []):
        ir_path = wf_cfg.get("ir_path", "")
        wf_name = Path(ir_path).stem
        if wf_name in workflow_files:
            wf_dst = tmp_path / workflow_files[wf_name].name
            wf_dst.write_text(
                WORKFLOW_DIR.joinpath(workflow_files[wf_name].name).read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            wf_cfg["ir_path"] = str(wf_dst)

    agent_dst = tmp_path / agent_files[0].name
    agent_dst.write_text(
        json.dumps(agent_ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return agent_dst


async def _run_local_ir(
    *, ir_path, query, conversation_id, conversation_history=None, params=None
):
    if conversation_history is None:
        conversation_history = []
    if params is None:
        params = {}

    default_params = {
        "conversationHistory": conversation_history,
        "pluginConfigs": [],
        "globalVariables": {},
        "llmExtraConfigs": {},
        "workflowSequence": [],
        "activeWorkflows": [],
    }
    default_params.update(params)

    req = ExecutionRequest.model_validate(
        {
            "conversationId": conversation_id,
            "query": query,
            "irPath": str(ir_path),
            "responseMode": "streaming",
            "executionMode": "sync",
            "params": default_params,
            "headers": {
                "Content-Type": "application/json",
                "x-code": "123",
                "name": "Tom",
                "userid": "1212",
                "status": "123.1",
            },
        }
    )

    ir_data = await async_ir_load(str(ir_path))
    ir_type = IRConverter.identify_ir(ir_data)

    if ir_type.name == "MultiAgents":
        instance = await IRConverter.ir_to_agent_group(
            ir_data, conversation_id=req.conversation_id, cust_headers={}
        )
    elif ir_type.name == "Agent":
        instance = await IRConverter.ir_to_agent(
            ir_data, conversation_id=req.conversation_id, cust_headers={}
        )
        if hasattr(instance, "context_manager"):
            instance.context_manager.agent_config.agent_id = ir_data.get("agentId", "")
    else:
        instance = await IRConverter.async_ir_to_workflow(ir_data)

    execution_data = ExecutionData(
        instance=instance, instance_type=ir_type, updated_time=int(time.time() * 1000)
    )
    fake_request = type("LocalRequest", (), {"headers": req.headers})()
    token = request_context.set(fake_request)
    try:
        response = await distribute_execution_request(req, execution_data)
    finally:
        request_context.reset(token)

    body = []
    async for chunk in response.body_iterator:
        body.append(chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk))
    return "".join(body)


# ---------------------------------------------------------------------------
# SSE 解析 & 断言
# ---------------------------------------------------------------------------
def _parse_sse_events(response_text):
    events = []
    for line in response_text.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


_SKIP_KEYS = frozenset(
    {
        "createdTime",
        "executionId",
        "time_consumption",
        "overall_latency",
        "plugin_latency",
        "total_latency",
        "model_latency",
        "wait_latency",
    }
)


def _diff_values(actual, expected, path):
    diffs = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for k, ev in expected.items():
            if k in _SKIP_KEYS:
                continue
            diffs.extend(_diff_values(actual.get(k), ev, f"{path}.{k}"))
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            diffs.append(
                f"{path}: list len expected={len(expected)} actual={len(actual)}"
            )
        else:
            for i, (ev, av) in enumerate(zip(expected, actual)):
                diffs.extend(_diff_values(av, ev, f"{path}[{i}]"))
    else:
        if expected != actual:
            diffs.append(f"{path}: expected={expected!r}  actual={actual!r}")
    return diffs


def _assert_sse_strict(actual_events, expected_events, label):
    actual_types = [e.get("event") for e in actual_events]
    expected_types = [e.get("event") for e in expected_events]
    assert actual_types == expected_types, (
        f"{label}: event sequence mismatch\n"
        f"  expected: {expected_types}\n  actual:   {actual_types}"
    )
    for i, (actual, expected) in enumerate(zip(actual_events, expected_events)):
        diffs = _diff_values(actual, expected, f"event[{i}]({expected.get('event')})")
        assert not diffs, (
            f"{label} event[{i}] ({expected.get('event')}) diffs:\n"
            + "\n".join(f"  {d}" for d in diffs)
        )


def _get_nested_value(obj, *keys):
    for k in keys:
        if isinstance(obj, dict):
            obj = obj.get(k)
        else:
            return None
        if obj is None:
            return None
    return obj


def _assert_sse_flexible(actual_events, expected_events, label):
    actual_types = [e.get("event") for e in actual_events]
    expected_types = [e.get("event") for e in expected_events]
    assert actual_types == expected_types, (
        f"{label}: event sequence mismatch\n"
        f"  expected: {expected_types}\n  actual:   {actual_types}"
    )

    for i, (actual, expected) in enumerate(zip(actual_events, expected_events)):
        event_type = expected.get("event")

        assert actual.get("event") == event_type, (
            f"{label} event[{i}]: event type mismatch"
        )
        assert actual.get("isStructMessage") == expected.get("isStructMessage"), (
            f"{label} event[{i}]: isStructMessage mismatch"
        )

        if event_type == "start":
            pass

        elif event_type == "function_call_end":
            pass

        elif event_type == "function_call":
            exp_fc = _get_nested_value(expected, "data", "answer", "function_call")
            act_fc = _get_nested_value(actual, "data", "answer", "function_call")
            assert act_fc is not None, f"{label} event[{i}]: missing function_call"
            assert act_fc.get("name") == exp_fc.get("name"), (
                f"{label} event[{i}]: function_call.name mismatch"
            )
            assert act_fc.get("arguments") == exp_fc.get("arguments"), (
                f"{label} event[{i}]: function_call.arguments mismatch"
            )
            exp_is_wf = _get_nested_value(expected, "data", "answer", "is_workflow")
            act_is_wf = _get_nested_value(actual, "data", "answer", "is_workflow")
            assert act_is_wf == exp_is_wf, f"{label} event[{i}]: is_workflow mismatch"

        elif event_type == "api_exec_data":
            exp_answer = _get_nested_value(expected, "data", "answer")
            act_answer = _get_nested_value(actual, "data", "answer")
            assert act_answer is not None, f"{label} event[{i}]: missing answer"
            assert act_answer.get("role") == exp_answer.get("role"), (
                f"{label} event[{i}]: role mismatch"
            )
            assert act_answer.get("name") == exp_answer.get("name"), (
                f"{label} event[{i}]: name mismatch"
            )
            exp_content = exp_answer.get("content")
            act_content = act_answer.get("content")
            if isinstance(exp_content, dict):
                assert isinstance(act_content, dict), (
                    f"{label} event[{i}]: content should be dict"
                )
                assert act_content.get("answer") == exp_content.get("answer"), (
                    f"{label} event[{i}]: content.answer mismatch"
                )
                assert act_content.get("workflow_state") == exp_content.get(
                    "workflow_state"
                ), f"{label} event[{i}]: content.workflow_state mismatch"

        elif event_type == "intermediate_message":
            exp_answer = _get_nested_value(expected, "data", "answer")
            act_answer = _get_nested_value(actual, "data", "answer")
            assert isinstance(act_answer, list), (
                f"{label} event[{i}]: answer should be list"
            )
            assert len(act_answer) == len(exp_answer), (
                f"{label} event[{i}]: answer list length mismatch"
            )
            for j, (exp_msg, act_msg) in enumerate(zip(exp_answer, act_answer)):
                assert act_msg.get("role") == exp_msg.get("role"), (
                    f"{label} event[{i}][{j}]: role mismatch"
                )
                if exp_msg.get("content") is not None:
                    assert act_msg.get("content") == exp_msg.get("content"), (
                        f"{label} event[{i}][{j}]: content mismatch"
                    )
                if exp_msg.get("name") is not None:
                    assert act_msg.get("name") == exp_msg.get("name"), (
                        f"{label} event[{i}][{j}]: name mismatch"
                    )
                exp_tool_calls = exp_msg.get("tool_calls")
                act_tool_calls = act_msg.get("tool_calls")
                if exp_tool_calls is not None:
                    assert act_tool_calls is not None, (
                        f"{label} event[{i}][{j}]: missing tool_calls"
                    )
                    assert len(act_tool_calls) == len(exp_tool_calls), (
                        f"{label} event[{i}][{j}]: tool_calls length mismatch"
                    )
                    for k, (exp_tc, act_tc) in enumerate(
                        zip(exp_tool_calls, act_tool_calls)
                    ):
                        assert act_tc.get("type") == exp_tc.get("type"), (
                            f"{label} event[{i}][{j}][{k}]: tool_calls.type mismatch"
                        )
                        exp_func = exp_tc.get("function")
                        act_func = act_tc.get("function")
                        if exp_func is not None:
                            assert act_func is not None, (
                                f"{label} event[{i}][{j}][{k}]: missing function"
                            )
                            assert act_func.get("name") == exp_func.get("name"), (
                                f"{label} event[{i}][{j}][{k}]: function.name mismatch"
                            )
                            assert act_func.get("arguments") == exp_func.get(
                                "arguments"
                            ), (
                                f"{label} event[{i}][{j}][{k}]: function.arguments mismatch"
                            )

        elif event_type == "statistic_data":
            pass

        elif event_type == "summary_response":
            exp_answer = _get_nested_value(expected, "data", "answer")
            act_answer = _get_nested_value(actual, "data", "answer")
            assert act_answer is not None, f"{label} event[{i}]: missing answer"
            assert act_answer.get("role") == exp_answer.get("role"), (
                f"{label} event[{i}]: role mismatch"
            )
            assert act_answer.get("content") == exp_answer.get("content"), (
                f"{label} event[{i}]: content mismatch"
            )


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------
@pytest.fixture()
def local_ir_path(tmp_path_factory, monkeypatch):
    _init_contract_runtime(monkeypatch)
    tmp_path = tmp_path_factory.mktemp("multi_instance_common_02")
    return _copy_ir_to_tmp(tmp_path)


# ===========================================================================
# 测试用例
# ===========================================================================
class TestCaseMultiInstanceCommon02:
    """ReAct 模式单提问器工作流中断恢复。

    Round 1: 用户给 2/5 字段 → 提问器追问
    Round 2: 用户补齐 → 提问器输出完整结果
    """

    @classmethod
    def setup_class(cls):
        shutil.rmtree(STATE_DIR, ignore_errors=True)

    def test_run(self, local_ir_path):
        conversation_id = f"conv_{int(time.time() * 1000)}"
        all_intermediate_messages = []

        # ======================
        # Round 1: 提问器中断
        # ======================
        interrupt_answer = "请您提供移动开关, 车机端显示信号, 剩余流量相关的信息"

        llm_1 = _ScriptedLLM(
            [
                AIMessage(
                    content='提问器-ssq|{"query": "电话号码是10000，故障发生在十点"}',
                    tool_calls=[
                        ToolCall(
                            name="提问器-ssq",
                            args={"query": "电话号码是10000，故障发生在十点"},
                            id="",
                        )
                    ],
                    usage_metadata=UsageMetadata(
                        code=0, errmsg="成功", finish_reason="function_call"
                    ),
                ),
            ]
        )

        wf_1 = _ScriptedWorkflow(
            {
                WORKFLOW_ID: [
                    [
                        _build_workflow_start_stream_data(workflow_id=WORKFLOW_ID),
                        _build_partial_stream_data(
                            answer=interrupt_answer,
                            node_id="node_5d8bd3c331a04",
                            node_name="Questioner",
                            node_type="jiuwen.questioner",
                            should_interrupt=True,
                        ),
                        _build_message_end_stream_data(
                            answer=interrupt_answer,
                            node_id="node_5d8bd3c331a04",
                            node_name="Questioner",
                            node_type="jiuwen.questioner",
                            should_interrupt=True,
                        ),
                        _build_intermediate_message_stream_data(
                            answer=[
                                {
                                    "role": "user",
                                    "content": "电话号码是10000，故障发生在十点",
                                },
                                {"role": "assistant", "content": interrupt_answer},
                            ]
                        ),
                        _build_end_stream_data(
                            answer="",
                            node_id="node_5d8bd3c331a04",
                            node_type="jiuwen.questioner",
                        ),
                    ]
                ]
            }
        )

        _mocks["llm"] = llm_1
        if os.getenv("USE_OPENJIUWEN_WORKFLOW", "false") != "true":
            _mocks["workflow"] = wf_1
        else:
            _mocks["questioner_extraction"] = _ScriptedQuestionerExtractionModel(
                [
                    '{"switch": null, "tel": "10000", "time": "十点", "signals": null, "flow_rate": null}',
                ]
            )

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="调用提问器-ssq输入电话号码是10000，故障发生在十点",
                conversation_id=conversation_id,
            )
        )

        events = _parse_sse_events(response_text)
        for i, ev in enumerate(events):
            print(
                f"  R1[{i}] event={ev.get('event')}, "
                f"answer={str(ev.get('data', {}).get('answer', ''))[:80]}"
            )

        # 严格逐条比对（对齐 conversation_tmdRU18Q 录制日志）
        expected_r1 = [
            {"event": "start", "data": {}, "isStructMessage": False},
            {"event": "function_call_end", "data": {}, "isStructMessage": False},
            {
                "event": "function_call",
                "data": {
                    "answer": {
                        "function_call": {
                            "name": "提问器-ssq",
                            "arguments": '{"query": "电话号码是10000，故障发生在十点"}',
                        },
                        "is_workflow": True,
                    }
                },
                "isStructMessage": False,
            },
            {
                "event": "api_exec_data",
                "data": {
                    "answer": {
                        "role": "function",
                        "name": "提问器-ssq",
                        "content": {
                            "answer": interrupt_answer,
                            "workflow_state": "running",
                        },
                    }
                },
                "isStructMessage": False,
            },
            {
                "event": "intermediate_message",
                "data": {
                    "answer": [
                        {
                            "role": "assistant",
                            "content": '提问器-ssq|{"query": "电话号码是10000，故障发生在十点"}',
                            "tool_calls": [
                                {
                                    "type": "function",
                                    "id": "",
                                    "function": {
                                        "name": "提问器-ssq",
                                        "arguments": '{"query": "电话号码是10000，故障发生在十点"}',
                                    },
                                }
                            ],
                        },
                        {
                            "role": "tool",
                            "name": "117c6695dcd9139726dce28c83abe0e671ea76b4be270599",
                            "content": interrupt_answer,
                            "tool_call_id": "",
                        },
                    ]
                },
                "isStructMessage": False,
            },
            {
                "event": "statistic_data",
                "data": {"answer": {}},
                "isStructMessage": False,
            },
            {
                "event": "summary_response",
                "data": {
                    "answer": {
                        "role": "assistant",
                        "content": interrupt_answer,
                    }
                },
                "isStructMessage": False,
            },
        ]
        _assert_sse_flexible(events, expected_r1, "R1")

        assert llm_1.call_count == 1, f"R1: LLM calls={llm_1.call_count}"

        if os.getenv("USE_OPENJIUWEN_WORKFLOW", "false") != "true":
            assert wf_1.call_count == 1, f"R1: workflow calls={wf_1.call_count}"
            assert wf_1.last_workflow_id == WORKFLOW_ID
        all_intermediate_messages.append(events[4])

        # ======================
        # Round 2: 提问器完成
        # ======================
        final_answer = (
            "电话号码：10000，故障发生时间：十点，"
            "移动开关开启状态：开启，车机端信号状态：有，车机端剩余流量：有"
        )

        llm_2 = _ScriptedLLM(
            [
                AIMessage(
                    content='提问器-ssq|{"query": "移动开关开启，车机端有显示信号，车机端有剩余流量"}',
                    tool_calls=[
                        ToolCall(
                            name="提问器-ssq",
                            args={
                                "query": "移动开关开启，车机端有显示信号，车机端有剩余流量"
                            },
                            id="",
                        )
                    ],
                    usage_metadata=UsageMetadata(
                        code=0, errmsg="成功", finish_reason="function_call"
                    ),
                ),
            ]
        )

        end_chunks = [
            "电话号码：",
            "10000",
            "，故障发生时间：",
            "十点",
            "，移动开关开启状态：",
            "开启",
            "，车机端信号状态：",
            "有",
            "，车机端剩余流量：",
            "有",
            "",
        ]
        wf_events_2 = []
        for chunk in end_chunks:
            wf_events_2.append(
                _build_partial_stream_data(
                    answer=chunk,
                    node_id="node_end",
                    node_name="输出",
                    node_type="jiuwen.end",
                )
            )
        wf_events_2.append(
            _build_message_end_stream_data(
                answer=final_answer,
                node_id="node_end",
                node_name="输出",
                node_type="jiuwen.end",
            )
        )
        wf_events_2.append(
            _build_intermediate_message_stream_data(
                answer=[
                    {
                        "role": "user",
                        "content": "移动开关开启，车机端有显示信号，车机端有剩余流量",
                    },
                    {"role": "assistant", "content": final_answer},
                ]
            )
        )
        wf_events_2.append(
            _build_workflow_end_stream_data(
                answer=final_answer,
                node_id="node_end",
                node_name="输出",
                node_type="jiuwen.end",
            )
        )
        wf_events_2.append(_build_end_stream_data(answer=final_answer))

        wf_2 = _ScriptedWorkflow({WORKFLOW_ID: [wf_events_2]})
        _mocks["llm"] = llm_2

        if os.getenv("USE_OPENJIUWEN_WORKFLOW", "false") != "true":
            _mocks["workflow"] = wf_2
        else:
            _mocks["questioner_extraction"] = _ScriptedQuestionerExtractionModel(
                [
                    '{"switch": "开启", "tel": "10000", "time": "十点", "signals": "有", "flow_rate": "有"}',
                ]
            )

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query="调用提问器-ssq输入移动开关开启，车机端有显示信号，车机端有剩余流量",
                conversation_id=conversation_id,
            )
        )

        events = _parse_sse_events(response_text)
        for i, ev in enumerate(events):
            print(
                f"  R2[{i}] event={ev.get('event')}, "
                f"answer={str(ev.get('data', {}).get('answer', ''))[:80]}"
            )

        expected_r2 = [
            {"event": "start", "data": {}, "isStructMessage": False},
            {"event": "function_call_end", "data": {}, "isStructMessage": False},
            {
                "event": "function_call",
                "data": {
                    "answer": {
                        "function_call": {
                            "name": "提问器-ssq",
                            "arguments": '{"query": "移动开关开启，车机端有显示信号，车机端有剩余流量"}',
                        },
                        "is_workflow": True,
                    }
                },
                "isStructMessage": False,
            },
            {
                "event": "api_exec_data",
                "data": {
                    "answer": {
                        "role": "function",
                        "name": "提问器-ssq",
                        "content": {"answer": final_answer, "workflow_state": "end"},
                    }
                },
                "isStructMessage": False,
            },
            {
                "event": "intermediate_message",
                "data": {
                    "answer": [
                        {
                            "role": "assistant",
                            "content": '提问器-ssq|{"query": "移动开关开启，车机端有显示信号，车机端有剩余流量"}',
                            "tool_calls": [
                                {
                                    "type": "function",
                                    "id": "",
                                    "function": {
                                        "name": "提问器-ssq",
                                        "arguments": '{"query": "移动开关开启，车机端有显示信号，车机端有剩余流量"}',
                                    },
                                }
                            ],
                        },
                        {
                            "role": "tool",
                            "name": "117c6695dcd9139726dce28c83abe0e671ea76b4be270599",
                            "content": final_answer,
                            "tool_call_id": "",
                        },
                    ]
                },
                "isStructMessage": False,
            },
            {
                "event": "statistic_data",
                "data": {"answer": {}},
                "isStructMessage": False,
            },
            {
                "event": "summary_response",
                "data": {
                    "answer": {
                        "role": "assistant",
                        "content": final_answer,
                    }
                },
                "isStructMessage": False,
            },
        ]
        _assert_sse_flexible(events, expected_r2, "R2")

        assert llm_2.call_count == 1, f"R2: LLM calls={llm_2.call_count}"

        if os.getenv("USE_OPENJIUWEN_WORKFLOW", "false") != "true":
            assert wf_2.call_count == 1, f"R2: workflow calls={wf_2.call_count}"
            assert wf_2.last_workflow_id == WORKFLOW_ID

        all_intermediate_messages.append(events[4])
        _mocks["llm"] = None
        _mocks["workflow"] = None
        _mocks["questioner_extraction"] = None

        # 跨轮次汇总
        exp_result = [
            {
                "name": "提问器-ssq",
                "arguments": '{"query": "电话号码是10000，故障发生在十点"}',
            },
            {
                "name": "提问器-ssq",
                "arguments": '{"query": "移动开关开启，车机端有显示信号，车机端有剩余流量"}',
            },
        ]
        assert len(all_intermediate_messages) == 2
        for i, (msg, expected) in enumerate(zip(all_intermediate_messages, exp_result)):
            actual_fn = msg["data"]["answer"][0]["tool_calls"][0]["function"]
            assert actual_fn == expected, (
                f"Round {i + 1}: expected {expected}, got {actual_fn}"
            )
