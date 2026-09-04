import asyncio
import copy
import json
import os
import time
from pathlib import Path

import pytest
import yaml

os.environ.setdefault("TGF_ENABLE", "false")

from jiuwen.test.cases.controller_multi_agent.openjiuwen_workflow_case_runtime import (
    init_openjiuwen_workflow_runtime,
    run_local_ir_with_openjiuwen_workflow,
)


CASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CASE_DIR.parents[2]
RESOURCE_TEMPLATE_DIR = PACKAGE_DIR / "resource" / "templates" / "default"
CASE_ASSET_DIR = CASE_DIR / "test_case_controller_multi_agent_common_20"
AGENT_DIR = CASE_ASSET_DIR / "agent"
SUB_AGENT_DIR = CASE_ASSET_DIR / "sub_agent"
WORKFLOW_DIR = CASE_ASSET_DIR / "workflow"
CASE_FILE = CASE_ASSET_DIR / "test_case_controller_multi_agent_common_20.yaml"
CURRENT_CASE_ANSWERS: list[str] = []


TYPE_CASES = [
    (
        "integer",
        1,
        [
            ("阿发", 1),
            ("开始改", 2),
            ("阿财", 3),
            ("阿福", 4),
            ("业务改", 5),
            ("默认改", 6),
        ],
    ),
    (
        "number",
        1.23,
        [
            ("阿发", 1.23),
            ("开始改", 2.23),
            ("阿财", 3.23),
            ("阿福", 4.23),
            ("业务改", 5.23),
            ("默认改", 6.23),
        ],
    ),
    (
        "boolean",
        True,
        [
            ("阿发", True),
            ("开始改", False),
            ("阿财", True),
            ("阿福", False),
            ("业务改", True),
            ("默认改", False),
        ],
    ),
]

WORKFLOW_RESPONSE_MARKERS = (
    "默认工作流",
    "结束工作流",
    "开始工作流",
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


def _assert_workflow_terminal_contract(response_text: str) -> None:
    events = _extract_sse_events(response_text)
    names = [event.get("event", "") for event in events]

    assert "error" not in names, response_text
    if "workflow_blocked" in names:
        assert "message_end" in names, response_text
        assert "intermediate_message" in names, response_text
        assert '"should_interrupt":true' in response_text, response_text
        return

    if "workflow_end" not in names:
        return

    finish_events = [
        event
        for event in events
        if event.get("event") == "done"
        and event.get("data", {}).get("node_type") == "jiuwen.end"
    ]
    assert finish_events, response_text
    assert "message_end" in names, response_text
    assert any(
        event.get("data", {}).get("user_fields") is not None for event in finish_events
    ), response_text


def _assert_expected_or_workflow_response(response_text: str) -> None:
    if CURRENT_CASE_ANSWERS and any(
        expected in response_text for expected in CURRENT_CASE_ANSWERS
    ):
        return
    assert any(marker in response_text for marker in WORKFLOW_RESPONSE_MARKERS), (
        response_text
    )


def _init_local_runtime(monkeypatch: pytest.MonkeyPatch):
    init_openjiuwen_workflow_runtime(
        monkeypatch,
        resource_template_dir=RESOURCE_TEMPLATE_DIR,
        answer_provider=lambda: CURRENT_CASE_ANSWERS,
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


def _replace_placeholders(payload, replacements: list[tuple[str, object]]):
    if isinstance(payload, dict):
        return {
            key: _replace_placeholders(value, replacements)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [_replace_placeholders(item, replacements) for item in payload]
    if isinstance(payload, str):
        replaced = payload
        for old, new in replacements:
            replaced = replaced.replace(str(old), str(new))
        return replaced
    return payload


def _apply_type_variant(
    ir_bundle: dict,
    expect_type: str,
    expect_value,
    replacements: list[tuple[str, object]],
):
    root_ir = copy.deepcopy(ir_bundle["root_ir"])
    child_ir = copy.deepcopy(ir_bundle["child_ir"])
    workflows = {
        name: copy.deepcopy(data) for name, data in ir_bundle["workflows"].items()
    }

    for target_ir in (root_ir, child_ir):
        global_variables = target_ir.get("configs", {}).get("global_variables", [])
        if global_variables:
            global_variables[0]["type"] = expect_type
            global_variables[0]["default"] = expect_value

    updated_workflows = {}
    for workflow_name, workflow_ir in workflows.items():
        mutated = _replace_placeholders(workflow_ir, replacements)
        updated_workflows[workflow_name] = mutated

    return {
        "root_ir": root_ir,
        "child_ir": child_ir,
        "workflows": updated_workflows,
    }


def _copy_case_ir_bundle(
    tmp_path: Path, expect_type: str | None = None, expect_value=None, replacements=None
) -> Path:
    root_src = _find_single_json(AGENT_DIR)
    child_src = _find_single_json(SUB_AGENT_DIR)
    root_ir = _load_json(root_src)
    child_ir = _load_json(child_src)
    workflow_files = {
        path.name: _load_json(path) for path in sorted(WORKFLOW_DIR.glob("*.json"))
    }

    ir_bundle = {"root_ir": root_ir, "child_ir": child_ir, "workflows": workflow_files}
    if expect_type is not None and replacements is not None:
        ir_bundle = _apply_type_variant(
            ir_bundle, expect_type, expect_value, replacements
        )

    child_dst = tmp_path / child_src.name
    root_dst = tmp_path / root_src.name

    for workflow in ir_bundle["child_ir"].get("configs", {}).get("workflows", []):
        workflow_name = Path(workflow.get("ir_path", "")).name
        if workflow_name:
            workflow_dst = tmp_path / workflow_name
            workflow_dst.write_text(
                json.dumps(
                    ir_bundle["workflows"][workflow_name], ensure_ascii=False, indent=2
                ),
                encoding="utf-8",
            )
            workflow["ir_path"] = str(workflow_dst)

    for workflow in ir_bundle["root_ir"].get("configs", {}).get("workflows", []):
        workflow_name = Path(workflow.get("ir_path", "")).name
        if workflow_name:
            workflow_dst = tmp_path / workflow_name
            if not workflow_dst.exists():
                workflow_dst.write_text(
                    json.dumps(
                        ir_bundle["workflows"][workflow_name],
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            workflow["ir_path"] = str(workflow_dst)

    for agent in ir_bundle["root_ir"].get("configs", {}).get("agents", []):
        child_name = Path(agent.get("ir_path", "")).name
        if child_name:
            child_ref = _resolve_fixture_path(child_name, SUB_AGENT_DIR)
            if child_ref.name != child_src.name:
                raise AssertionError(
                    f"Root IR points to unexpected child IR: {child_ref}"
                )
            agent["ir_path"] = str(child_dst)

    child_dst.write_text(
        json.dumps(ir_bundle["child_ir"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    root_dst.write_text(
        json.dumps(ir_bundle["root_ir"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return root_dst


@pytest.fixture(autouse=True)
def _runtime(monkeypatch):
    _init_local_runtime(monkeypatch)


def test_run(tmp_path_factory):
    base_cases = _load_cases()
    base_ir_path = _copy_case_ir_bundle(
        tmp_path_factory.mktemp("controller_multi_agent_common20_base")
    )
    base_conversation_id = f"conversation_{int(time.time() * 1000)}"
    base_conversation_history: list[dict] = []

    for case_data in base_cases:
        CURRENT_CASE_ANSWERS.clear()
        CURRENT_CASE_ANSWERS.extend(case_data.get("answer") or [])
        response_text = asyncio.run(
            run_local_ir_with_openjiuwen_workflow(
                base_ir_path,
                case_data["query"],
                conversation_id=base_conversation_id,
                conversation_history=base_conversation_history,
            ),
        )
        events = _event_names(response_text)
        assert (
            ("task_end" in events)
            or ("workflow_blocked" in events)
            or ('"should_interrupt":true' in response_text)
        ), response_text
        assert '"event":"error"' not in response_text, response_text
        _assert_workflow_terminal_contract(response_text)
        if CURRENT_CASE_ANSWERS and "message_end" in response_text:
            _assert_expected_or_workflow_response(response_text)
        base_conversation_history.append(
            {"role": "user", "content": case_data["query"]}
        )
        if CURRENT_CASE_ANSWERS:
            base_conversation_history.append(
                {"role": "assistant", "content": CURRENT_CASE_ANSWERS[0]}
            )

    for expect_type, expect_value, values in TYPE_CASES:
        tmp_path = tmp_path_factory.mktemp(
            f"controller_multi_agent_common20_{expect_type}"
        )
        ir_path = _copy_case_ir_bundle(
            tmp_path,
            expect_type=expect_type,
            expect_value=expect_value,
            replacements=values,
        )
        expect_cases = copy.deepcopy(base_cases)
        for old, new in values:
            expect_cases = _replace_placeholders(expect_cases, [(old, new)])

        conversation_id = f"conversation_{expect_type}_{int(time.time() * 1000)}"
        conversation_history: list[dict] = []
        for case_data in expect_cases:
            CURRENT_CASE_ANSWERS.clear()
            CURRENT_CASE_ANSWERS.extend(case_data.get("answer") or [])
            response_text = asyncio.run(
                run_local_ir_with_openjiuwen_workflow(
                    ir_path,
                    case_data["query"],
                    conversation_id=conversation_id,
                    conversation_history=conversation_history,
                ),
            )
            events = _event_names(response_text)
            assert (
                ("task_end" in events)
                or ("workflow_blocked" in events)
                or ('"should_interrupt":true' in response_text)
            ), response_text
            assert '"event":"error"' not in response_text, response_text
            _assert_workflow_terminal_contract(response_text)
            if CURRENT_CASE_ANSWERS and "message_end" in response_text:
                _assert_expected_or_workflow_response(response_text)
            conversation_history.append({"role": "user", "content": case_data["query"]})
            if CURRENT_CASE_ANSWERS:
                conversation_history.append(
                    {"role": "assistant", "content": CURRENT_CASE_ANSWERS[0]}
                )
