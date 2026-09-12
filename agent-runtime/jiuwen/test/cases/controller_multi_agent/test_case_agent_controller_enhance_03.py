import asyncio
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("TGF_ENABLE", "false")

from jiuwen.controller.task_executor.handler.workflow_handler import WorkflowHandler
from jiuwen.orchestration.flow.stream.base import StreamCode, StreamData
from jiuwen.test.cases.controller_multi_agent.openjiuwen_workflow_case_runtime import (
    init_openjiuwen_workflow_runtime,
    run_local_ir_with_openjiuwen_workflow,
)


CASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CASE_DIR.parents[2]
RESOURCE_TEMPLATE_DIR = PACKAGE_DIR / "resource" / "templates" / "default"
CASE_ASSET_DIR = CASE_DIR / "test_case_agent_controller_enhance_03"
AGENT_DIR = CASE_ASSET_DIR / "agent"
WORKFLOW_DIR = CASE_ASSET_DIR / "workflow"
CURRENT_CASE_ANSWERS: list[str] = []


def _load_cases() -> list[dict]:
    return [
        {
            "query": "双色球",
            "answer": [
                "推荐双色球-双色球基础玩法-FAQ",
                "命中双色球基础玩法FAQ",
            ],
        }
    ]


def _init_local_runtime(monkeypatch: pytest.MonkeyPatch):
    init_openjiuwen_workflow_runtime(
        monkeypatch,
        resource_template_dir=RESOURCE_TEMPLATE_DIR,
        answer_provider=lambda: CURRENT_CASE_ANSWERS,
    )

    async def _fake_stream_execute_workflow_for_intent_detection(
        self, workflow_input, workflow_context, conversation_id
    ):
        yield StreamData(
            code=StreamCode.MESSAGE_END.value,
            msg="",
            data={
                "answer": "",
                "node_type": "jiuwen.end",
                "node_id": "intent_workflow_end",
                "node_name": "intent_workflow_end",
                "user_fields": {
                    "intent_id": 1,
                    "intent_name": "ssq_双色球基础玩法-FAQ_1",
                    "candidate_intents": [],
                },
                "workflow_id": workflow_context.workflow_id,
            },
            execution_id=self.task_id,
        )
        yield StreamData(
            code=StreamCode.FINISH.value,
            msg="",
            data={},
            execution_id=self.task_id,
        )

    monkeypatch.setattr(
        WorkflowHandler,
        "stream_execute_workflow_for_intent_detection",
        _fake_stream_execute_workflow_for_intent_detection,
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
    root_ir = _load_json(root_src)
    root_dst = tmp_path / root_src.name

    for workflow in root_ir.get("configs", {}).get("workflows", []):
        workflow_name = Path(workflow.get("ir_path", "")).name
        if workflow_name:
            workflow_src = _resolve_fixture_path(workflow_name, WORKFLOW_DIR)
            workflow_dst = tmp_path / workflow_src.name
            workflow_dst.write_text(
                workflow_src.read_text(encoding="utf-8"), encoding="utf-8"
            )
            workflow["ir_path"] = str(workflow_dst)

    root_dst.write_text(
        json.dumps(root_ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return root_dst


@pytest.fixture()
def local_ir_path(tmp_path_factory, monkeypatch):
    _init_local_runtime(monkeypatch)
    tmp_path = tmp_path_factory.mktemp("controller_multi_agent_enhance_03")
    return _copy_case_ir_bundle(tmp_path)


@pytest.mark.parametrize("case_data", _load_cases(), ids=lambda case: case["query"])
def test_run(local_ir_path, case_data):
    CURRENT_CASE_ANSWERS.clear()
    CURRENT_CASE_ANSWERS.extend(case_data.get("answer") or [])

    response_text = asyncio.run(
        run_local_ir_with_openjiuwen_workflow(
            local_ir_path,
            case_data["query"],
        )
    )
    assert "task_end" in response_text, response_text
    assert '"event":"error"' not in response_text, response_text
    if CURRENT_CASE_ANSWERS and "message_end" in response_text:
        assert any(expected in response_text for expected in CURRENT_CASE_ANSWERS), (
            response_text
        )
