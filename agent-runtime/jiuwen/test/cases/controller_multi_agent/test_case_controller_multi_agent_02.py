import asyncio
import json
import os
from pathlib import Path

import pytest
import yaml

os.environ.setdefault("TGF_ENABLE", "false")

from jiuwen.test.cases.controller_multi_agent.openjiuwen_workflow_case_runtime import (
    init_openjiuwen_workflow_runtime,
    run_local_ir_with_openjiuwen_workflow,
)
from jiuwen.controller.task_planner.planning_modules.intention_detect_module import (
    DEFAULT_INTENT,
)


CASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CASE_DIR.parents[2]
RESOURCE_TEMPLATE_DIR = PACKAGE_DIR / "resource" / "templates" / "default"
CASE_ASSET_DIR = CASE_DIR / "test_case_controller_multi_agent_02"
AGENT_DIR = CASE_ASSET_DIR / "agent"
SUB_AGENT_DIR = CASE_ASSET_DIR / "sub_agent"
WORKFLOW_DIR = CASE_ASSET_DIR / "workflow"
CASE_FILE = CASE_ASSET_DIR / "test_case_controller_multi_agent_02.yaml"
CURRENT_CASE_ANSWERS: list[str] = []
WORKFLOW_RESPONSE_MARKERS = (
    "【开始工作流-结束节点】",
    "好的，赎回成功",
    "默认工作流",
    "## 流程结束",
    '"should_interrupt":true',
)


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


def _assert_expected_or_workflow_response(response_text: str) -> None:
    if CURRENT_CASE_ANSWERS and any(
        expected in response_text for expected in CURRENT_CASE_ANSWERS
    ):
        return
    assert any(marker in response_text for marker in WORKFLOW_RESPONSE_MARKERS), (
        response_text
    )


def _select_case_intent(
    detector, active_workflows, query: str, answers: list[str], kwargs: dict
):
    if detector.category_2_agent_name_map:
        return next(iter(detector.category_2_agent_name_map.values()))

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


@pytest.fixture()
def local_ir_path(tmp_path_factory, monkeypatch):
    _init_local_runtime(monkeypatch)
    tmp_path = tmp_path_factory.mktemp("controller_multi_agent_case02")
    return _copy_case_ir_bundle(tmp_path)


@pytest.mark.parametrize("case_data", _load_cases(), ids=lambda case: case["query"])
def test_run(local_ir_path, case_data):
    CURRENT_CASE_ANSWERS.clear()
    CURRENT_CASE_ANSWERS.extend(case_data.get("answer") or [])

    response_text = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(local_ir_path, case_data["query"])
    )
    events = _event_names(response_text)
    assert any(
        event in events
        for event in (
            "task_end",
            "workflow_blocked",
            "workflow_end",
            "done",
            "intermediate_message",
        )
    ), response_text
    assert '"event":"error"' not in response_text, response_text
    if CURRENT_CASE_ANSWERS and "message_end" in response_text:
        _assert_expected_or_workflow_response(response_text)


def test_multi_questioner_resume_contract(local_ir_path):
    cases = _load_cases()
    conversation_id = "conversation_controller_multi_agent_02_openjiuwen_contract"
    conversation_history: list[dict] = []

    for first_index, resume_index in ((1, 2),):
        first_turn = cases[first_index]
        CURRENT_CASE_ANSWERS.clear()
        CURRENT_CASE_ANSWERS.extend(first_turn.get("answer") or [])
        first_response = asyncio.run(
            run_local_ir_with_openjiuwen_workflow(
                local_ir_path,
                first_turn["query"],
                conversation_id=conversation_id,
                conversation_history=conversation_history,
            )
        )
        first_events = _event_names(first_response)

        assert '"event":"error"' not in first_response, first_response
        assert "workflow_start" in first_events, first_response
        first_turn_blocked_by_workflow = "workflow_blocked" in first_events
        assert first_turn_blocked_by_workflow or "task_end" not in first_events, (
            first_response
        )
        assert "intermediate_message" in first_events, first_response
        if first_turn_blocked_by_workflow:
            assert '"node_type":"jiuwen.questioner"' in first_response, first_response
            assert '"should_interrupt":true' in first_response, first_response
        _append_history(conversation_history, first_turn)

        resume_turn = cases[resume_index]
        CURRENT_CASE_ANSWERS.clear()
        CURRENT_CASE_ANSWERS.extend(resume_turn.get("answer") or [])
        resume_response = asyncio.run(
            run_local_ir_with_openjiuwen_workflow(
                local_ir_path,
                resume_turn["query"],
                conversation_id=conversation_id,
                conversation_history=conversation_history,
            )
        )
        resume_events = _event_names(resume_response)

        assert '"event":"error"' not in resume_response, resume_response
        if first_turn_blocked_by_workflow:
            assert "workflow_resume" in resume_events, resume_response
        else:
            assert "workflow_start" in resume_events, resume_response
            assert "workflow_end" in resume_events, resume_response
        assert "message_end" in resume_events, resume_response
        assert "intermediate_message" in resume_events, resume_response
        if "workflow_blocked" in resume_events:
            assert '"node_type":"jiuwen.questioner"' in resume_response, resume_response
            assert '"should_interrupt":true' in resume_response, resume_response
        _append_history(conversation_history, resume_turn)

    default_turn = cases[-1]
    CURRENT_CASE_ANSWERS.clear()
    CURRENT_CASE_ANSWERS.extend(default_turn.get("answer") or [])
    default_response = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(
            local_ir_path,
            default_turn["query"],
            conversation_id=conversation_id,
            conversation_history=conversation_history,
        )
    )
    default_events = _event_names(default_response)

    assert '"event":"error"' not in default_response, default_response
    assert "workflow_start" in default_events, default_response
    assert "workflow_end" in default_events, default_response
    assert "done" in default_events, default_response
