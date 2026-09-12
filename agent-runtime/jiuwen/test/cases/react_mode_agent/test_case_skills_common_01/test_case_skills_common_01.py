#!/usr/bin/env python
"""
南向契约测试 -- ReAct mode agent (Skills 工具调用 case)

=== 测试目标 ===
验证 ReAct 模式下，Agent 通过 sysOperationCard 动态注入 Skills 工具时，
LLM 能按照 SKILL.md 定义的 Workflow 顺序执行工具调用，
SSE 响应数据帧的结构和内容与真实 E2E 输出是否一致。

=== 被测链路 ===
  用户请求 → IR 加载 → Agent 实例化 → ReactMode 控制循环
    → LLM 调用 → Skills 工具路由（read_file / execute_code / execute_shell）
    → 工具执行 → SSE 响应流

=== 单次请求执行流程 ===
  Round 1: read_file(SKILL.md) → LLM tool_call → plugin × 1
  Round 2: read_file(error.log) → LLM tool_call → plugin × 1
  Round 3: execute_code → LLM tool_call → plugin × 1
  Round 4: execute_shell → LLM tool_call → plugin × 1
  Round 5: final content response → stop

=== E2E 输出 ===
  21 帧 SSE 事件 (5轮×4帧 + 5帧结束序列)

=== 核心设计 ===
  - 南向打桩：在框架即将发出外部调用的位置替换
  - LLM mock 在 BaseChatModel.astream 级别
  - Skills Plugin mock 在 Function.ainvoke 级别（不同于普通插件）
  - 契约参考：resource/ 下的 txt 文件是从真实环境录制的 mock 数据

=== 验证维度 ===
  - SSE 数据帧：事件类型、字段结构、业务数据（逐帧严格比对）
  - 调用计数：LLM × 5 / Plugin × 4
  - 参数透传：tool_call 参数是否正确传递到工具执行层

用法：
  pytest -v test_case_skills_common_01.py
"""

__all__ = [
    "TestCaseSkillsCommon01",
]

import ast
import asyncio
import json
import os
import re
import time
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# 环境变量预设（必须在 import jiuwen 之前设置）
# ---------------------------------------------------------------------------
os.environ.setdefault("EXECUTION_STATE_STORAGE_MEDIUM", "memory")
os.environ.setdefault("IR_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_GROUP_CACHE_ENABLE", "false")
os.environ.setdefault("USE_EI_INTENT", "false")
os.environ.setdefault("PLUGIN_SSL_API_CERT_KEY", "false")
os.environ["USE_TOOL_WRAPPER"] = "true"
os.environ.setdefault("USE_OPENJIUWEN_WORKFLOW", "true")
os.environ.setdefault("WORKFLOW_EXECUTE_TIMEOUT", "1200")

from jiuwen.common.init import JiuWen
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import BaseChatModel
from jiuwen.common.llm_service.messages import AIMessage, ToolCall, UsageMetadata
from jiuwen.controller.task_planner.planning_modules.intention_detect_module import (
    IntentionDetectModule,
    convert_ai_message_to_llm_output,
)
from jiuwen.plugin.models.function import Function
from jiuwen.serve.common.context import request as request_context
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
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
RESOURCE_DIR = CASE_DIR / "resource"


# ===================================================================
# Mock 基础设施（共享层）
# ===================================================================
class _IntegrationRegistry:
    """进程级单例，注册 Mock Model / Plugin 运行时。"""

    model = None
    plugin = None

    @classmethod
    def clear(cls):
        cls.model = None
        cls.plugin = None

    @classmethod
    def set_model(cls, model):
        cls.model = model

    @classmethod
    def get_model(cls):
        return cls.model

    @classmethod
    def set_plugin(cls, plugin):
        cls.plugin = plugin

    @classmethod
    def get_plugin(cls):
        return cls.plugin


@dataclass
class _ModelCall:
    inputs: Any
    model_id: str
    session_id: str
    kwargs: dict


@dataclass
class _PluginCall:
    tool_name: str
    inputs: dict


class _FallbackChatModel(BaseChatModel):
    """Deterministic fallback when no scripted output is configured."""

    model_name: str = "fake-qwen"

    def _chat(self, messages, tools=None, **kwargs):
        return AIMessage(content="0")


class _LocalModelAdapter:
    """将 _RecordingModelRuntime 适配为 _IntegrationRegistry.model 接口。"""

    def __init__(self, runtime):
        self.runtime = runtime

    async def ainvoke(self, inputs, **kwargs):
        if hasattr(self.runtime, "ainvoke"):
            return await self.runtime.ainvoke(inputs, **kwargs)
        return await self.runtime.invoke(inputs, **kwargs)

    async def astream(self, inputs, **kwargs):
        """async generator，yield AIMessage 对象。"""
        if hasattr(self.runtime, "astream"):
            async for item in self.runtime.astream(inputs, **kwargs):
                yield item


class _RecordingModelRuntime:
    """可编程 LLM Mock，通过 astream 返回 AIMessage 流。"""

    def __repr__(self):
        return f"_RecordingModelRuntime(outputs_left={len(self.scripted_outputs)})"

    def __init__(self, scripted_outputs):
        self.scripted_outputs = list(scripted_outputs)
        self.calls = []

    async def ainvoke(self, inputs, session_id=None, **kwargs):
        """兼容 IntentionDetectModule._execute_llm_call 的 ainvoke 调用。"""
        self.calls.append(
            _ModelCall(
                inputs=inputs,
                model_id=kwargs.pop("model_id", ""),
                session_id=session_id or "",
                kwargs=kwargs,
            )
        )
        if self.scripted_outputs:
            return self.scripted_outputs.pop(0)
        return AIMessage(content="0")

    async def astream(self, inputs, **kwargs):
        """async generator，yield AIMessage 对象。"""
        self.calls.append(
            _ModelCall(
                inputs=inputs,
                model_id=kwargs.pop("model_id", ""),
                session_id=kwargs.pop("session_id", ""),
                kwargs=kwargs,
            )
        )
        if self.scripted_outputs:
            final_msg = self.scripted_outputs.pop(0)
        else:
            final_msg = AIMessage(content="0")

        # 中间 chunk
        yield AIMessage(
            content="",
            usage_metadata=UsageMetadata(code=0, errmsg="成功", finish_reason=""),
        )
        # 最终 chunk
        if not final_msg.usage_metadata:
            fr = "function_call" if final_msg.tool_calls else "stop"
            final_msg.usage_metadata = UsageMetadata(
                code=0,
                errmsg="成功",
                finish_reason=fr,
            )
        yield final_msg


class _RecordingPluginRuntime:
    """可编程 Plugin Mock，按插件名返回预设结果，同时记录所有调用。

    注意：Skills 工具名称格式为 'read_file', 'execute_code', 'execute_shell'，
    不是 AgentCoreRestfulLayer 子类，而是 Function 实例。
    """

    def __init__(self, scripted_by_name):
        self.scripted_by_name = {k: list(v) for k, v in scripted_by_name.items()}
        self.calls = []

    async def execute(self, tool_name, inputs):
        self.calls.append(_PluginCall(tool_name=tool_name, inputs=inputs))
        results = self.scripted_by_name.get(tool_name, [])
        if results:
            data = results.pop(0)
        else:
            data = {"result": "mock_result"}
        return {"errCode": 0, "errMessage": "success", "data": data}


# ===================================================================
# Mock 数据解析器（使用 ast.literal_eval 解析复杂 dict）
# ===================================================================
def _parse_llm_mock_data(filepath: Path) -> list[AIMessage]:
    """解析 LLM mock 文件，提取每轮输出的 AIMessage。

    输入格式（每轮）:
        mock 大模型输入
        {...}
        mock 大模型输出
        type='assistant' content='...' ... tool_calls=ToolCall(name='xxx', args={...}, id='') ...

    返回: [AIMessage1, AIMessage2, ...] (5 轮)
    """
    txt = filepath.read_text(encoding="utf-8")
    outputs = []

    # 分割每个 "mock 大模型输出" 块
    # 使用非贪婪匹配，允许跨行内容
    output_pattern = re.compile(
        r"mock 大模型输出\s*\n"
        r"type='assistant'\s+content='([^']*)'\s+name=None\s+id=None\s+"
        r"tool_calls=ToolCall\((.*?)\)\s+"  # 非贪婪匹配 ToolCall 内容
        r"usage_metadata=UsageMetadata\((.*?)\)",
        re.MULTILINE | re.DOTALL,
    )

    for match in output_pattern.finditer(txt):
        content = match.group(1) or ""
        # 将 Python repr 中的转义序列转换为真实字符
        # 文件中 \n 是两个字符，需要变成真正的换行符
        content = content.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
        tool_calls_str = match.group(2)
        usage_str = match.group(3)

        # 解析 ToolCall
        tool_call = None
        if tool_calls_str and "name=" in tool_calls_str:
            # ToolCall 格式: name='xxx', args={...}, id=''
            tc_name_match = re.search(r"name='([^']*)'", tool_calls_str)
            # args 匹配：需要处理嵌套 dict 和多行字符串
            # 使用更宽松的匹配：从 args= 开始到下一个逗号或结束
            tc_args_match = re.search(
                r"args=(\{.*?\})(?:,\s*id=|$)", tool_calls_str, re.DOTALL
            )

            if tc_name_match:
                tc_name = tc_name_match.group(1)
                tc_args = {}
                if tc_args_match:
                    tc_args_str = tc_args_match.group(1)
                    try:
                        # 使用 ast.literal_eval 安全解析 Python dict
                        tc_args = ast.literal_eval(tc_args_str)
                    except Exception:
                        tc_args = {}

                tool_call = ToolCall(name=tc_name, args=tc_args)

        # 解析 UsageMetadata
        finish_reason = "stop"
        if "finish_reason='function_call'" in usage_str:
            finish_reason = "function_call"

        usage_metadata = UsageMetadata(
            code=0,
            errmsg="成功",
            finish_reason=finish_reason,
        )

        ai_msg = AIMessage(
            content=content,
            tool_calls=[tool_call] if tool_call else [],
            usage_metadata=usage_metadata,
        )
        outputs.append(ai_msg)

    return outputs


def _extract_balanced_braces(text: str, start_pos: int) -> str:
    """从 start_pos 开始提取匹配的 {} 内容。

    处理嵌套括号，返回完整的 dict 字符串。
    """
    if start_pos >= len(text) or text[start_pos] != "{":
        return ""

    depth = 0
    end_pos = start_pos
    in_string = False
    string_char = None

    for i in range(start_pos, len(text)):
        char = text[i]

        # 处理字符串内的内容（跳过括号计数）
        if in_string:
            if char == string_char and (i == start_pos or text[i - 1] != "\\"):
                in_string = False
            continue

        if char in ('"', "'"):
            in_string = True
            string_char = char
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end_pos = i + 1
                break

    return text[start_pos:end_pos]


def _parse_plugin_mock_data(filepath: Path) -> dict[str, list[dict]]:
    """解析 Plugin mock 文件，提取每个工具的返回数据。

    输入格式（每次调用）:
        mock 插件输入 tool_name=xxx
        args={...}
        ...
        mock 插件输出 tool_name=xxx
        {'errCode': 0, 'errMessage': '...', 'data': {...}}
        --- 分隔符

    返回: {"read_file": [data1, data2], "execute_code": [data1], "execute_shell": [data1]}
    """
    txt = filepath.read_text(encoding="utf-8")
    result = {}

    # 分割每个 "---" 块
    blocks = txt.split("---")

    for block in blocks:
        if not block.strip():
            continue

        # 提取 tool_name
        tool_name_match = re.search(r"mock 插件输出 tool_name=(\w+)", block)
        if not tool_name_match:
            continue
        tool_name = tool_name_match.group(1)

        # 提取输出 data - 使用括号匹配算法
        # 找到 "mock 插件输出 tool_name=xxx" 后的第一个 { 位置
        output_start_match = re.search(r"mock 插件输出 tool_name=\w+\s*\n\{", block)
        if not output_start_match:
            continue

        # 从匹配的位置开始，找到第一个 { 的位置
        brace_start = output_start_match.end() - 1
        output_str = _extract_balanced_braces(block, brace_start)

        try:
            output_data = ast.literal_eval(output_str)
        except Exception:
            output_data = {"errCode": 0, "errMessage": "success", "data": {}}

        # 只取 data 字段
        data = output_data.get("data", output_data)

        if tool_name not in result:
            result[tool_name] = []
        result[tool_name].append(data)

    return result


# ===================================================================
# Contract Runtime 初始化（monkeypatch）
# ===================================================================
def _init_contract_runtime(monkeypatch: pytest.MonkeyPatch):
    """初始化 Contract Runtime，替换 Model / Plugin 为 Mock。"""
    os.environ["EXECUTION_STATE_STORAGE_MEDIUM"] = "memory"
    os.environ["IR_CACHE_ENABLE"] = "false"
    os.environ["AGENT_CACHE_ENABLE"] = "false"
    os.environ["AGENT_GROUP_CACHE_ENABLE"] = "false"
    os.environ["USE_AGENT_CORE_MODEL"] = "false"
    os.environ["USE_EI_INTENT"] = "true"
    os.environ["USE_TOOL_WRAPPER"] = "true"
    os.environ["PLUGIN_SSL_API_CERT_KEY"] = "false"
    _IntegrationRegistry.clear()

    # --- Patch 1: ModelFactory.get_model → FallbackChatModel ---
    monkeypatch.setattr(
        ModelFactory,
        "get_model",
        lambda self, model_type, model_name, *args, **kwargs: _FallbackChatModel(),
    )

    # --- Patch 2: 初始化 JiuWen prompt manager ---
    if not RESOURCE_TEMPLATE_DIR.exists():
        raise FileNotFoundError(
            f"Prompt template directory not found: {RESOURCE_TEMPLATE_DIR}"
        )
    JiuWen.init(prompt_dir=str(RESOURCE_TEMPLATE_DIR), plugin_dir=None, cfg_file=None)

    # --- Patch 3: IntentionDetectModule._execute_llm_call → Registry.model ---
    async def _patched_execute_llm_call(self, llm_input):
        start_time = time.time()
        model = _IntegrationRegistry.get_model()
        if model is not None:
            llm_message = await model.ainvoke(
                llm_input,
                model_id=getattr(self.llm, "model_name", ""),
                session_id=getattr(self.plan_config, "task_id", "") or "",
            )
        else:
            llm_message = await self.llm.ainvoke(llm_input)
        converted_output = convert_ai_message_to_llm_output(llm_message)
        total_time = time.time() - start_time
        model_stat, model_usage = self._extract_usage_metadata(llm_message)
        ResultTuple = namedtuple(
            "ResultTuple",
            [
                "converted_output",
                "total_time",
                "model_stat",
                "model_usage",
                "llm_message",
            ],
        )
        return ResultTuple(
            converted_output=converted_output,
            total_time=round(total_time, 2),
            model_stat=model_stat,
            model_usage=model_usage,
            llm_message=llm_message,
        )

    # --- Patch 5: Function.ainvoke → Registry.plugin ---
    # Skills 工具通过 Function.ainvoke -> callable_function 调用
    # 这与普通插件（AgentCoreRestfulLayer.ainvoke）不同
    original_function_ainvoke = Function.ainvoke

    async def _fake_function_ainvoke(self, inputs, **kwargs):
        plugin = _IntegrationRegistry.get_plugin()
        if plugin is not None:
            return await plugin.execute(
                self.name, inputs if isinstance(inputs, dict) else {}
            )
        return await original_function_ainvoke(self, inputs, **kwargs)

    # --- Patch 3': BaseChatModel.astream → Registry.model.astream ---
    original_astream = BaseChatModel.astream

    async def _patched_astream(self, inputs, **kwargs):
        model = _IntegrationRegistry.get_model()
        if model is not None and hasattr(model, "astream"):
            async for item in model.astream(inputs, **kwargs):
                yield item
            return
        async for item in original_astream(self, inputs, **kwargs):
            yield item

    monkeypatch.setattr(
        IntentionDetectModule,
        "_execute_llm_call",
        _patched_execute_llm_call,
    )
    monkeypatch.setattr(
        BaseChatModel,
        "astream",
        _patched_astream,
    )
    # Skills 工具打桩点：Function.ainvoke
    monkeypatch.setattr(
        Function,
        "ainvoke",
        _fake_function_ainvoke,
    )


# ===================================================================
# IR 加载与执行
# ===================================================================
def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_ir_to_tmp(tmp_path: Path) -> Path:
    """将 Agent IR 复制到临时目录。"""
    agent_files = list(AGENT_DIR.glob("*.json"))
    if len(agent_files) != 1:
        raise AssertionError(
            f"Expected exactly one agent json in {AGENT_DIR}, found {len(agent_files)}"
        )
    agent_ir = _load_json(agent_files[0])

    agent_dst = tmp_path / agent_files[0].name
    agent_dst.write_text(
        json.dumps(agent_ir, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return agent_dst


async def _run_local_ir(
    *,
    ir_path: Path,
    query: str,
    conversation_id: str,
    conversation_history=None,
    params=None,
):
    """执行 IR 加载 + 分发请求，返回 SSE 响应文本。"""
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
            ir_data,
            conversation_id=req.conversation_id,
            cust_headers={},
        )
    elif ir_type.name == "Agent":
        instance = await IRConverter.ir_to_agent(
            ir_data,
            conversation_id=req.conversation_id,
            cust_headers={},
        )
        if hasattr(instance, "context_manager"):
            instance.context_manager.agent_config.agent_id = ir_data.get("agentId", "")
    else:
        instance = await IRConverter.async_ir_to_workflow(ir_data)

    execution_data = ExecutionData(
        instance=instance,
        instance_type=ir_type,
        updated_time=int(time.time() * 1000),
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


# ===================================================================
# SSE 解析辅助函数
# ===================================================================
def _parse_sse_events(response_text: str):
    """解析 SSE 文本，返回 data payload 列表。"""
    events = []
    for raw_line in response_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("data: "):
            continue
        payload = line[len("data: ") :]
        events.append(json.loads(payload))
    return events


def _load_expected_sse_events(filepath: Path) -> list:
    """从 mock_e2e_output.txt 解析期望的 SSE 事件列表。"""
    txt = filepath.read_text(encoding="utf-8")
    events = []
    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


# 动态字段：每次运行都不同，跳过比对
_SKIP_KEYS = frozenset(
    {
        "createdTime",
        "executionId",
        "index",
        "isStructMessage",
        "time_consumption",
        "overall_latency",
        "total_latency",
        "model_latency",
        "wait_latency",
        "plugin_latency",
        "time",
        "execution_id",
        "task_id",
        "plan_id",
        "tool_call_id",
        "id",
        "latency",
    }
)


def _strip_dynamic(obj):
    """递归移除动态字段，返回新对象用于比对。"""
    if isinstance(obj, dict):
        return {k: _strip_dynamic(v) for k, v in obj.items() if k not in _SKIP_KEYS}
    elif isinstance(obj, list):
        return [_strip_dynamic(item) for item in obj]
    return obj


def _assert_sse_strict(actual_events, expected_events, label=""):
    """逐条严格比对 SSE 事件（去除动态字段后）。"""
    prefix = f"[{label}] " if label else ""

    # 先比对事件数量
    assert len(actual_events) == len(expected_events), (
        f"{prefix}SSE event count mismatch: "
        f"expected={len(expected_events)}, actual={len(actual_events)}\n"
        f"  expected types: {[e.get('event') for e in expected_events]}\n"
        f"  actual types:   {[e.get('event') for e in actual_events]}"
    )

    # 再比对事件类型序列
    actual_types = [e.get("event") for e in actual_events]
    expected_types = [e.get("event") for e in expected_events]
    assert actual_types == expected_types, (
        f"{prefix}SSE event type sequence mismatch:\n"
        f"  expected: {expected_types}\n"
        f"  actual:   {actual_types}"
    )

    # 逐条比对内容（去除动态字段）
    for i, (actual, expected) in enumerate(zip(actual_events, expected_events)):
        actual_clean = _strip_dynamic(actual)
        expected_clean = _strip_dynamic(expected)
        assert actual_clean == expected_clean, (
            f"{prefix}SSE event[{i}] ({expected.get('event')}) content mismatch:\n"
            f"  expected: {json.dumps(expected_clean, ensure_ascii=False, indent=2)}\n"
            f"  actual:   {json.dumps(actual_clean, ensure_ascii=False, indent=2)}"
        )


# ===================================================================
# pytest fixture
# ===================================================================
@pytest.fixture()
def local_ir_path(tmp_path_factory, monkeypatch):
    _init_contract_runtime(monkeypatch)
    tmp_path = tmp_path_factory.mktemp("skills_common_01")
    return _copy_ir_to_tmp(tmp_path)


# ===================================================================
# 测试用例：ReAct Mode Skills 工具调用南向契约测试
# ===================================================================
class TestCaseSkillsCommon01:
    """Skills 南向契约测试 - exception-analyzer skill execution."""

    def test_run(self, local_ir_path):
        """单次请求触发 skill workflow 执行，严格逐帧比对 SSE 输出。

        - LLM: 5 轮 (read_file → read_file → execute_code → execute_shell → final)
        - Plugin: 4 次 (read_file×2, execute_code×1, execute_shell×1)
        - SSE: 21 帧 (严格逐帧比对)
        """
        # 1. 解析 mock 数据
        llm_outputs = _parse_llm_mock_data(
            RESOURCE_DIR / "mock_react_llm_input_and_output.txt"
        )
        plugin_data = _parse_plugin_mock_data(
            RESOURCE_DIR / "mock_react_plugin_input_and_output.txt"
        )

        print(f"Parsed LLM outputs: {len(llm_outputs)} rounds")
        for i, out in enumerate(llm_outputs):
            tc_names = [tc.name for tc in out.tool_calls] if out.tool_calls else []
            print(
                f"  Round {i + 1}: tool_calls={tc_names}, finish_reason={out.usage_metadata.finish_reason if out.usage_metadata else 'N/A'}"
            )

        print(f"Parsed Plugin data: {sum(len(v) for v in plugin_data.values())} calls")
        for name, datas in plugin_data.items():
            print(f"  {name}: {len(datas)} calls")

        # 2. 构建 RecordingRuntime
        model_runtime = _RecordingModelRuntime(llm_outputs)
        plugin_runtime = _RecordingPluginRuntime(plugin_data)

        # 3. 注册 mock
        _IntegrationRegistry.clear()
        _IntegrationRegistry.set_model(_LocalModelAdapter(runtime=model_runtime))
        _IntegrationRegistry.set_plugin(plugin_runtime)

        # 4. 执行请求（带 sysOperationCard）
        conversation_id = f"conv_{int(time.time() * 1000)}"

        # sysOperationCard 配置 - Skills 工具通过此参数动态注入
        params = {
            "sysOperationCard": {
                "id": "sys_op_skill_test",
                "mode": "local",
                "workConfig": {
                    "workDir": str(RESOURCE_DIR.parent),
                    "shellAllowlist": [
                        "ls",
                        "dir",
                        "cat",
                        "type",
                        "python",
                        "node",
                        "pwd",
                        "echo",
                    ],
                },
            }
        }

        query = "使用技能exception-analyzer分析error.log的异常，首先请调用read_file来读取SKILL.md文件，然后按照skill的每一个step往下走：先执行read_file，再执行execute_code，最后执行execute_shell"

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query=query,
                conversation_id=conversation_id,
                params=params,
            )
        )

        # 5. 解析 SSE 响应
        actual_events = _parse_sse_events(response_text)
        print(f"Actual SSE events: {len(actual_events)} frames")
        for i, ev in enumerate(actual_events):
            print(f"  [{i}] event={ev.get('event')}")

        # 6. 加载期望 E2E 输出
        expected_events = _load_expected_sse_events(
            RESOURCE_DIR / "mock_e2e_output.txt"
        )
        print(f"Expected SSE events: {len(expected_events)} frames")

        # 7. 严格逐帧比对 SSE 输出
        _assert_sse_strict(actual_events, expected_events, "SkillsTest")

        # 8. Spy 断言
        assert len(model_runtime.calls) == 5, (
            f"Expected 5 LLM calls, got: {len(model_runtime.calls)}\n"
            f"  calls: {[str(c.inputs)[:50] for c in model_runtime.calls]}"
        )
        assert len(plugin_runtime.calls) == 4, (
            f"Expected 4 plugin calls, got: {len(plugin_runtime.calls)}\n"
            f"  calls: {[c.tool_name for c in plugin_runtime.calls]}"
        )

        # 验证工具调用顺序
        expected_tool_sequence = [
            "read_file",
            "read_file",
            "execute_code",
            "execute_shell",
        ]
        actual_tool_sequence = [c.tool_name for c in plugin_runtime.calls]
        assert actual_tool_sequence == expected_tool_sequence, (
            f"Tool call sequence mismatch:\n"
            f"  expected: {expected_tool_sequence}\n"
            f"  actual:   {actual_tool_sequence}"
        )

        _IntegrationRegistry.clear()
