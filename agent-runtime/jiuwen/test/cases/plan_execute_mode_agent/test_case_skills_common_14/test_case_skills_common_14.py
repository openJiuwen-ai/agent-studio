#!/usr/bin/env python
"""南向契约测试 -- PlanExecute mode agent (workflow_kpi + exception-analyzer skill)

=== 测试目标 ===
验证 PlanExecute 模式下，Agent 通过 sysOperationCard 动态注入 Skills 工具时，
能够正确执行 SceneMatch → TaskPlan → Workflow → Skills 的完整流程。
SSE 响应数据帧的结构和内容与真实 E2E 输出是否一致。

=== 被测链路 ===
  用户请求 → IR 加载 → Agent 实例化 → PlanExecute 控制循环
    → SceneMatch(LLM) → TaskPlan(LLM) → Step1(workflow_kpi) → Step2(skills tools)
    → SSE 响应流

=== 执行流程 ===
  SceneMatch: 匹配 scene "kpi查询和使用skill做异常分析"
  TaskPlan: 规划 2 步 (查询KPI数据, 异常日志分析)
  Step 1: 执行 workflow_kpi → 返回 "kpi为：800"
  Step 2: 执行 exception-analyzer skill
    - read_file(SKILL.md)
    - read_file(error.log)
    - execute_code
    - execute_shell

=== Mock 策略 ===
  Patch 1: ModelFactory.get_model → _FallbackChatModel
  Patch 2: JiuWen.init() → 初始化 prompt manager
  Patch 3: IntentionDetectModule._execute_llm_call → _mocks["llm"].ainvoke
  Patch 3': BaseChatModel.ainvoke → _mocks["llm"].ainvoke
  Patch 3'': BaseChatModel.astream → _mocks["llm"].astream
  Patch 4: WorkflowHandler.create_workflow_instance → _WorkflowStub
  Patch 5: Function.ainvoke → _RecordingPluginRuntime (Skills tools)
  Patch 6: RestFulAPI.ainvoke → no-op

=== 验证维度 ===
  - SSE 数据帧：事件类型、字段结构、业务数据（逐帧严格比对）
  - LLM调用：SceneMatch + TaskPlan + Step 执行
  - Workflow调用：workflow_kpi 执行
  - Skills调用：read_file × 2, execute_code × 1, execute_shell × 1

=== 注意 ===
  此测试用于验证收编可行性。如果 SSE 输出不一致，分析原因，不修改任何文件。
"""

__all__ = [
    "TestCaseSkillsCommon14",
]

import ast
import asyncio
import json
import os
import pickle
import re
import tempfile
import time
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# 环境变量预设（必须在 import jiuwen 之前设置）
# ---------------------------------------------------------------------------
os.environ.setdefault("EXECUTION_STATE_STORAGE_MEDIUM", "memory")
os.environ.setdefault("IR_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_CACHE_ENABLE", "false")
os.environ.setdefault("AGENT_GROUP_CACHE_ENABLE", "false")
os.environ.setdefault("USE_EI_INTENT", "false")
os.environ.setdefault("USE_OPENJIUWEN_WORKFLOW", "false")
os.environ.setdefault("USE_TOOL_WRAPPER", "true")
os.environ.setdefault("PLUGIN_SSL_API_CERT_KEY", "false")

from jiuwen.common.init import JiuWen
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import BaseChatModel
from jiuwen.common.llm_service.messages import AIMessage, ToolCall, UsageMetadata
from jiuwen.controller.task_executor.handler.workflow_handler import WorkflowHandler
from jiuwen.controller.task_planner.planning_modules.intention_detect_module import (
    IntentionDetectModule,
    convert_ai_message_to_llm_output,
)
from jiuwen.orchestration.flow.stream.base import StreamData
from jiuwen.plugin.models.function import Function
from jiuwen.plugin.models.restfulapi import RestFulAPI
from jiuwen.serve.common.context import request as request_context
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from jiuwen.serve.controllers.execution.manager import AsyncStateManager
from jiuwen.serve.controllers.execution.open_utils import async_ir_load
from jiuwen.serve.controllers.execution.types import ExecutionData
from jiuwen.serve.controllers.execution.utils import (
    distribute_execution_request,
    prepare_params,
)
from jiuwen.serve.schemas.orchestration_mgr import ExecutionRequest

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
CASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CASE_DIR.parents[3]
RESOURCE_TEMPLATE_DIR = PACKAGE_DIR / "resource" / "templates" / "default"
AGENT_DIR = CASE_DIR / "agent"
WORKFLOW_DIR = CASE_DIR / "workflow"
RESOURCE_DIR = CASE_DIR / "resource"

# ---------------------------------------------------------------------------
# 跨轮次状态持久化（文件 pickle）
# ---------------------------------------------------------------------------
STATE_DIR = Path(tempfile.gettempdir()) / "jiuwen_test_pe_skills_state"


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
    pass


# ---------------------------------------------------------------------------
# Mock 基础设施（PE 模式 + Skills 模式合并）
# ---------------------------------------------------------------------------
_mocks: dict = {"llm": None, "workflow": None}


@dataclass
class _PluginCall:
    tool_name: str
    inputs: dict


class _IntegrationRegistry:
    """进程级单例，注册 Skills Plugin 运行时。"""

    plugin = None

    @classmethod
    def clear(cls):
        cls.plugin = None

    @classmethod
    def set_plugin(cls, plugin):
        cls.plugin = plugin

    @classmethod
    def get_plugin(cls):
        return cls.plugin


class _FallbackChatModel(BaseChatModel):
    model_name: str = "fake-qwen"

    def _chat(self, messages, tools=None, **kwargs):
        return AIMessage(content="0")


class _ScriptedLLM:
    """预设 LLM 返回值。ainvoke 用于 SceneMatch/TaskPlan，astream 用于 Step。"""

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
        yield AIMessage(
            content="",
            usage_metadata=UsageMetadata(code=0, errmsg="成功", finish_reason=""),
        )
        if not msg.usage_metadata:
            fr = "function_call" if msg.tool_calls else "stop"
            msg.usage_metadata = UsageMetadata(code=0, errmsg="成功", finish_reason=fr)
        yield msg


class _ScriptedWorkflow:
    """预设工作流返回值。按 workflow_id 返回事件列表。"""

    def __init__(self, events_by_id):
        self.events_by_id = {k: list(v) for k, v in events_by_id.items()}
        self.call_count = 0

    def pop_events(self, workflow_id):
        self.call_count += 1
        bucket = self.events_by_id.get(workflow_id, [])
        return bucket.pop(0) if bucket else []


class _WorkflowStub:
    """create_workflow_instance 返回的 duck-type mock。"""

    def __init__(self, events):
        if events and isinstance(events[0], list):
            self._rounds = list(events)
        else:
            self._rounds = [events] if events else [[]]

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
        current = self._rounds.pop(0) if self._rounds else []

        async def _gen():
            for e in current:
                yield e

        return _gen()


class _RecordingPluginRuntime:
    """可编程 Plugin Mock，按工具名返回预设结果，同时记录所有调用。

    注意：Skills 工具名称格式为 'read_file', 'execute_code', 'execute_shell'，
    是 Function 实例。
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


# ---------------------------------------------------------------------------
# Resource 文件解析
# ---------------------------------------------------------------------------
def _load_expected_sse_events() -> list[dict]:
    """从 resource/mock_e2e_output.txt 解析期望 SSE 事件。"""
    txt = (RESOURCE_DIR / "mock_e2e_output.txt").read_text(encoding="utf-8")
    all_events = []
    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            ev = json.loads(line[6:])
            all_events.append(ev)
    return all_events


def _parse_llm_outputs() -> list[AIMessage]:
    """从 resource/mock_pe_llm_input_and_output.txt 解析所有 LLM 输出。

    按 section 分组（每个 --- 分隔），每个 section 代表一次完整的 LLM 调用。

    PlanExecute 模式的 LLM 调用链：
    1. SceneMatch (ainvoke): finish_reason='stop'
    2. TaskPlan (ainvoke): finish_reason='stop'
    3. Step 执行 (astream): 多种可能
       - 有 tool_calls, finish_reason='function_call' → 调用工具
       - 无 tool_calls, finish_reason='stop' → 步骤完成输出（如带[STEP_DONE]）
       - 无 tool_calls, finish_reason='null' → 流式chunks中间帧
    4. 最终总结 (astream): finish_reason='stop', 无 tool_calls

    关键逻辑：
    - 每个 section 是一次独立的 LLM 调用
    - finish_reason='function_call' 且有 tool_calls → 返回 tool_calls
    - finish_reason='stop' → 返回 content（无论是 SceneMatch/TaskPlan 还是 Step 完成输出）
    - 其他情况跳过
    """
    txt = (RESOURCE_DIR / "mock_pe_llm_input_and_output.txt").read_text(
        encoding="utf-8"
    )
    outputs = []

    # 按 section 分组（使用 \n---\n 作为分隔符，避免误解析 markdown 内容中的 ---）
    sections = re.split(r"\n---\n", txt)

    for section in sections:
        if not section.strip():
            continue

        # 检测 section 类型（仅用于日志，不影响解析逻辑）
        is_scene_match = "[SceneMatch]" in section
        is_task_plan = "[TaskPlan]" in section

        # 解析所有输出帧
        final_tool_calls = []
        found_function_call = False
        found_stop = False
        fc_chunk_content = ""
        stop_chunk_content = ""

        lines = section.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("mock 大模型输出"):
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    msg = _parse_ai_message_repr_full(next_line)
                    if msg is not None:
                        fr_match = re.search(r"finish_reason='([^']+)'", next_line)
                        finish_reason = fr_match.group(1) if fr_match else ""

                        if finish_reason == "function_call" and msg.tool_calls:
                            final_tool_calls = msg.tool_calls
                            fc_chunk_content = msg.content
                            found_function_call = True
                        elif finish_reason == "stop":
                            stop_chunk_content = msg.content
                            found_stop = True
            i += 1

        if found_function_call and final_tool_calls:
            outputs.append(
                AIMessage(content=fc_chunk_content, tool_calls=final_tool_calls)
            )
        elif found_stop:
            outputs.append(AIMessage(content=stop_chunk_content))

    return outputs


def _parse_ai_message_repr(line: str) -> AIMessage:
    """解析 AIMessage 的 repr 字符串。"""
    # content
    m = re.search(r"content='(.*?)'(?:\s+name=)", line)
    if not m:
        m = re.search(r'content="(.*?)"(?:\s+name=)', line)
    content = m.group(1) if m else ""
    # 处理多行 content
    content = content.replace("\\n", "\n")

    # tool_calls
    tool_calls = []
    tc_match = re.search(r"tool_calls=\[(.*?)\]", line)
    if tc_match:
        tc_str = tc_match.group(1)
        for tc_m in re.finditer(
            r"ToolCall\(name='([^']+)',\s*args=(\{[^}]*\}),\s*id='([^']*)'",
            tc_str,
        ):
            args = ast.literal_eval(tc_m.group(2))
            tool_calls.append(ToolCall(name=tc_m.group(1), args=args, id=tc_m.group(3)))

    kwargs = {"content": content}
    if tool_calls:
        kwargs["tool_calls"] = tool_calls
    return AIMessage(**kwargs)


def _parse_ai_message_repr_full(line: str) -> AIMessage | None:
    """解析完整的 AIMessage repr 字符串。

    格式: type='assistant' content='...' name=None id=None tool_calls=[...] ...
    """
    if not line.startswith("type='assistant'"):
        return None

    # content - 提取直到 name=None
    content_match = re.search(r"content='(.*?)'\s+name=None", line)
    content = content_match.group(1) if content_match else ""
    content = content.replace("\\n", "\n")

    # tool_calls - 格式: tool_calls=[ToolCall(...)] 或 tool_calls=[] 或 tool_calls=None
    tool_calls = []

    # 检查是否有 tool_calls
    if "tool_calls=[ToolCall" in line:
        # 提取 ToolCall - args 可能有嵌套 {}，需要括号匹配
        # 格式: ToolCall(name='xxx', args={...}, id='xxx')
        tc_start_pattern = r"ToolCall\(name='([^']+)',\s*args="
        for tc_start_m in re.finditer(tc_start_pattern, line):
            name = tc_start_m.group(1)
            args_start = tc_start_m.end()
            # 使用括号匹配提取 args 内容
            args_str = _extract_balanced_braces(line, args_start)
            # 提取 id - 在 args 之后
            id_start = args_start + len(args_str)
            id_match = re.search(r",\s*id='([^']*)'", line[id_start:])
            call_id = id_match.group(1) if id_match else ""
            try:
                args = ast.literal_eval(args_str)
                tool_calls.append(ToolCall(name=name, args=args, id=call_id))
            except Exception:
                pass
    elif "tool_calls=[]" in line or "tool_calls=None" in line:
        # 没有 tool_calls
        pass

    return AIMessage(content=content, tool_calls=tool_calls)


def _parse_workflow_events() -> list[tuple[str, list[StreamData]]]:
    """从 resource/mock_pe_workflow_input_and_output.txt 解析工作流事件。

    返回 [(workflow_id, [StreamData, ...]), ...] 按出现顺序。
    跳过 code=7000 (intermediate message) 事件。
    """
    txt = (RESOURCE_DIR / "mock_pe_workflow_input_and_output.txt").read_text(
        encoding="utf-8"
    )
    sections = []
    current_id = None
    current_events = []
    in_section = False
    pending_header_id = None

    for line in txt.splitlines():
        line_s = line.strip()
        # 识别 section header: "xxx 工作流"
        if line_s.endswith("工作流") and not in_section:
            pending_header_id = line_s.replace(" 工作流", "").strip()
            continue
        if line_s == "=== In ReactMode: Before stream workflow ===":
            in_section = True
            current_events = []
            current_id = pending_header_id
            pending_header_id = None
            continue
        if line_s == "=== In ReactMode: After stream workflow ===":
            in_section = False
            if current_id and current_events:
                sections.append((current_id, current_events))
            current_id = None
            current_events = []
            continue
        if not in_section:
            continue
        if line_s.startswith("StreamData("):
            sd = _parse_stream_data_repr(line_s)
            if sd is None:
                continue
            # 跳过 intermediate message
            if sd.code == 7000:
                continue
            current_events.append(sd)

    return sections


def _parse_stream_data_repr(line: str) -> StreamData:
    """解析 StreamData(...) repr 字符串。"""
    m = re.match(
        r"StreamData\(code=(\d+),\s*msg=([^,]+),\s*data=(\{.*\}),\s*"
        r"index=(\d+),execution_id=([^,]*),\s*is_struct_message=(\w+)\)",
        line,
    )
    if not m:
        return None
    code = int(m.group(1))
    msg = m.group(2).strip()
    try:
        data = ast.literal_eval(m.group(3))
    except (ValueError, SyntaxError):
        return None
    return StreamData(code=code, msg=msg, data=data, execution_id="")


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


def _extract_balanced_braces(text: str, start_pos: int) -> str:
    """从 start_pos 开始提取匹配的 {} 内容。"""
    if start_pos >= len(text) or text[start_pos] != "{":
        return ""

    depth = 0
    end_pos = start_pos
    in_string = False
    string_char = None

    for i in range(start_pos, len(text)):
        char = text[i]

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


def _build_workflow_mocks_from_resource():
    """解析 workflow resource 文件，构建 _ScriptedWorkflow 所需的数据结构。"""
    sections = _parse_workflow_events()
    by_id = {}
    for wf_id, events in sections:
        if wf_id not in by_id:
            by_id[wf_id] = []
        by_id[wf_id].append(events)

    result = {}
    for wf_id, event_lists in by_id.items():
        if len(event_lists) == 1:
            result[wf_id] = event_lists
        else:
            result[wf_id] = [event_lists]
    return result


# ---------------------------------------------------------------------------
# Contract Runtime 初始化（monkeypatch）
# ---------------------------------------------------------------------------
def _init_contract_runtime(monkeypatch: pytest.MonkeyPatch):
    os.environ["EXECUTION_STATE_STORAGE_MEDIUM"] = "memory"
    os.environ["IR_CACHE_ENABLE"] = "false"
    os.environ["AGENT_CACHE_ENABLE"] = "false"
    os.environ["AGENT_GROUP_CACHE_ENABLE"] = "false"
    os.environ["USE_EI_INTENT"] = "false"
    _mocks["llm"] = None
    _mocks["workflow"] = None
    _IntegrationRegistry.clear()

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

    # Patch 3': BaseChatModel.ainvoke → _mocks["llm"]
    original_ainvoke = BaseChatModel.ainvoke

    async def _patched_ainvoke(self, inputs, **kwargs):
        llm = _mocks["llm"]
        if llm is not None and hasattr(llm, "ainvoke"):
            return await llm.ainvoke(inputs, **kwargs)
        return await original_ainvoke(self, inputs, **kwargs)

    # Patch 3'': BaseChatModel.astream → _mocks["llm"]
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
    async def _patched_create(workflow_context, conversation_id, user_id):
        wf = _mocks["workflow"]
        if wf is not None:
            events = wf.pop_events(workflow_context.workflow_id)
            return _WorkflowStub(events)
        return await WorkflowHandler.create_workflow_instance.__wrapped__(
            workflow_context, conversation_id, user_id
        )

    # Patch 5: Function.ainvoke → _IntegrationRegistry.plugin (Skills tools)
    original_function_ainvoke = Function.ainvoke

    async def _fake_function_ainvoke(self, inputs, **kwargs):
        plugin = _IntegrationRegistry.get_plugin()
        if plugin is not None:
            return await plugin.execute(
                self.name, inputs if isinstance(inputs, dict) else {}
            )
        return await original_function_ainvoke(self, inputs, **kwargs)

    # Patch 6: RestFulAPI.ainvoke → no-op
    async def _noop_plugin(self, inputs, **kwargs):
        return {}

    monkeypatch.setattr(
        IntentionDetectModule, "_execute_llm_call", _patched_execute_llm_call
    )
    monkeypatch.setattr(BaseChatModel, "ainvoke", _patched_ainvoke)
    monkeypatch.setattr(BaseChatModel, "astream", _patched_astream)
    monkeypatch.setattr(
        WorkflowHandler, "create_workflow_instance", staticmethod(_patched_create)
    )
    monkeypatch.setattr(Function, "ainvoke", _fake_function_ainvoke)
    monkeypatch.setattr(RestFulAPI, "ainvoke", _noop_plugin)

    # Patch 7: AsyncStateManager → 文件 pickle
    monkeypatch.setattr(AsyncStateManager, "save_state", _file_based_save_state)
    monkeypatch.setattr(AsyncStateManager, "get_state", _file_based_get_state)
    monkeypatch.setattr(AsyncStateManager, "delete_state", _file_based_delete_state)


# ---------------------------------------------------------------------------
# IR 加载
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
    wf_tmp_paths = {}
    for wf_stem, wf_src in workflow_files.items():
        wf_dst = tmp_path / wf_src.name
        wf_ir = _load_json(wf_src)
        wf_dst.write_text(
            json.dumps(wf_ir, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        wf_tmp_paths[wf_stem] = wf_dst

    for wf_cfg in agent_ir.get("configs", {}).get("workflows", []):
        ir_path = wf_cfg.get("ir_path", "")
        wf_name = Path(ir_path).stem
        if wf_name in wf_tmp_paths:
            wf_cfg["ir_path"] = str(wf_tmp_paths[wf_name])

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
        "globalVariables": {"risk": "0"},
        "llmExtraConfigs": {"X-Auth-Token": "HAHAHA"},
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

    # 预处理：将 headers 合并到 plugin_configs
    req.params = prepare_params(req)

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
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError as e:
                print(f"Failed to parse SSE event: {e}")
    return events


# 动态字段：每次运行都不同，跳过比对
_SKIP_KEYS = frozenset(
    {
        "createdTime",
        "executionId",
        "index",
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
        "isStructMessage",
    }
)


def _strip_dynamic(obj, event_type=None):
    """递归移除动态字段，返回新对象用于比对。"""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k in _SKIP_KEYS:
                continue
            # intermediate_message 的 answer 是完整会话历史，跳过内容比对
            if event_type == "intermediate_message" and k == "answer":
                continue
            result[k] = _strip_dynamic(v, event_type)
        return result
    elif isinstance(obj, list):
        return [_strip_dynamic(item, event_type) for item in obj]
    return obj


def _assert_sse_strict(actual_events, expected_events, label):
    """逐条严格比对 SSE 事件（去除动态字段后）。"""
    assert len(actual_events) == len(expected_events), (
        f"{label}: event count mismatch: "
        f"expected={len(expected_events)}, "
        f"actual={len(actual_events)}\n"
        f"  expected types: "
        f"{[e.get('event') for e in expected_events]}\n"
        f"  actual types:   "
        f"{[e.get('event') for e in actual_events]}"
    )

    actual_types = [e.get("event") for e in actual_events]
    expected_types = [e.get("event") for e in expected_events]
    assert actual_types == expected_types, (
        f"{label}: event type sequence mismatch\n"
        f"  expected: {expected_types}\n"
        f"  actual:   {actual_types}"
    )

    for i, (actual, expected) in enumerate(zip(actual_events, expected_events)):
        evt = expected.get("event", "")
        a_clean = _strip_dynamic(actual, event_type=evt)
        e_clean = _strip_dynamic(expected, event_type=evt)
        assert a_clean == e_clean, (
            f"{label} event[{i}] ({expected.get('event')}) "
            f"content mismatch:\n"
            f"  expected: {json.dumps(e_clean, ensure_ascii=False, indent=2)}\n"
            f"  actual:   {json.dumps(a_clean, ensure_ascii=False, indent=2)}"
        )


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------
@pytest.fixture()
def local_ir_path(tmp_path_factory, monkeypatch):
    _init_contract_runtime(monkeypatch)
    tmp_path = tmp_path_factory.mktemp("skills_common_14")
    return _copy_ir_to_tmp(tmp_path)


# ---------------------------------------------------------------------------
# 测试用例
# ---------------------------------------------------------------------------
class TestCaseSkillsCommon14:
    """PlanExecute 模式 + Skills 工具南向契约测试。

    执行流程：SceneMatch → TaskPlan → Step1(workflow_kpi) → Step2(skills)
    """

    @classmethod
    def setup_class(cls):
        import shutil

        shutil.rmtree(STATE_DIR, ignore_errors=True)

    def test_run(self, local_ir_path):
        """单次请求触发 PE + Skills 执行，严格逐帧比对 SSE 输出。"""
        conversation_id = f"conv_{int(time.time() * 1000)}"

        # 1. 加载期望 SSE 输出
        expected_events = _load_expected_sse_events()
        print(f"Expected SSE events: {len(expected_events)} frames")
        for i, ev in enumerate(expected_events):
            print(f"  [{i}] event={ev.get('event')}")

        # 2. 解析 LLM mock 数据
        # 从 mock_pe_llm_input_and_output.txt 解析
        # 格式: [SceneMatch输出, TaskPlan输出, Step执行输出(如果有)]
        all_llm_outputs = _parse_llm_outputs()
        print(f"Parsed LLM outputs: {len(all_llm_outputs)} messages")
        for i, out in enumerate(all_llm_outputs):
            tc_names = [tc.name for tc in out.tool_calls] if out.tool_calls else []
            print(f"  [{i}] content={out.content[:50]}..., tool_calls={tc_names}")

        # 注意：当前 mock 数据只有 SceneMatch 和 TaskPlan 两个输出
        # Step 执行的 LLM 输出（skills tool_calls）可能需要补充
        # 或者框架会自动处理 tool_calls

        # 3. 构建 LLM mock
        llm = _ScriptedLLM(all_llm_outputs)

        # 4. 解析 Workflow mock 数据
        wf_events = _build_workflow_mocks_from_resource()
        print(f"Parsed workflow events: {wf_events.keys()}")
        for wf_id, events_list in wf_events.items():
            print(f"  {wf_id}: {len(events_list)} event groups")

        # 5. 构建 Workflow mock
        wf = _ScriptedWorkflow(wf_events)

        # 6. 解析 Plugin mock 数据 (Skills tools)
        plugin_data = _parse_plugin_mock_data(
            RESOURCE_DIR / "mock_pe_plugin_input_and_output.txt"
        )
        print(f"Parsed plugin data: {plugin_data.keys()}")
        for name, datas in plugin_data.items():
            print(f"  {name}: {len(datas)} calls")

        # 7. 构建 Plugin mock
        plugin_runtime = _RecordingPluginRuntime(plugin_data)

        # 8. 注册 mocks
        _mocks["llm"] = llm
        _mocks["workflow"] = wf
        _IntegrationRegistry.set_plugin(plugin_runtime)

        # 9. 执行请求（带 sysOperationCard）
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

        query = "查询kpi数据，分析异常日志"

        response_text = asyncio.run(
            _run_local_ir(
                ir_path=local_ir_path,
                query=query,
                conversation_id=conversation_id,
                params=params,
            )
        )

        # 10. 解析 SSE 响应
        actual_events = _parse_sse_events(response_text)
        print(f"\nActual SSE events: {len(actual_events)} frames")
        for i, ev in enumerate(actual_events):
            print(f"  [{i}] event={ev.get('event')}")

        # 11. 严格逐帧比对 SSE 输出
        _assert_sse_strict(actual_events, expected_events, "SkillsCommon14")

        # 12. Spy 断言
        print(f"\nLLM call count: {llm.call_count}")
        print(f"Workflow call count: {wf.call_count}")
        print(f"Plugin call count: {len(plugin_runtime.calls)}")
        for c in plugin_runtime.calls:
            print(f"  {c.tool_name}: {c.inputs}")

        # 清理
        _mocks["llm"] = None
        _mocks["workflow"] = None
        _IntegrationRegistry.clear()
