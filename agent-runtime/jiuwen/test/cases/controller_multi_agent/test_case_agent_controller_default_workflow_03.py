import asyncio
import json
import os
import time
from pathlib import Path

import pytest

os.environ.setdefault("TGF_ENABLE", "false")

from jiuwen.test.cases.controller_multi_agent.openjiuwen_workflow_case_runtime import (
    init_openjiuwen_workflow_runtime,
    run_local_ir_with_openjiuwen_workflow,
)


CASE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = CASE_DIR.parents[2]
RESOURCE_TEMPLATE_DIR = PACKAGE_DIR / "resource" / "templates" / "default"
CASE_ASSET_DIR = CASE_DIR / "test_case_agent_controller_default_workflow_03"
AGENT_DIR = CASE_ASSET_DIR / "agent"
WORKFLOW_DIR = CASE_ASSET_DIR / "workflow"
CURRENT_CASE_ANSWERS: list[str] = []

TALKS = [
    {"query": "镜像问题", "answer": ["default workflow answer"]},
    {"query": "执行异常", "answer": ["default workflow answer"]},
    {"query": "默认流程兜底", "answer": ["default workflow answer"]},
    {"query": "结束流程", "answer": ["default workflow answer"]},
]


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
    tmp_path = tmp_path_factory.mktemp("agent_controller_default_workflow_03")
    return _copy_case_ir_bundle(tmp_path)


def test_run(local_ir_path):
    conversation_id = f"conversation_{int(time.time() * 1000)}"
    conversation_history: list[dict] = []

    for talk in TALKS:
        CURRENT_CASE_ANSWERS.clear()
        CURRENT_CASE_ANSWERS.extend(talk.get("answer") or [])

        response_text = asyncio.run(
            run_local_ir_with_openjiuwen_workflow(
                local_ir_path,
                talk["query"],
                conversation_id=conversation_id,
                conversation_history=conversation_history,
                global_variables={"name": "tom"},
                llm_extra_configs={"X-Auth-Token": "HAHAHA"},
                headers={
                    "Content-Type": "application/json",
                    "X-Invoke-Mode": "debug",
                },
            ),
        )

        assert "task_end" in response_text, response_text
        assert '"event":"error"' not in response_text, response_text
        if CURRENT_CASE_ANSWERS and "message_end" in response_text:
            assert any(
                expected in response_text for expected in CURRENT_CASE_ANSWERS
            ), response_text

        conversation_history.append({"role": "user", "content": talk["query"]})
        if CURRENT_CASE_ANSWERS:
            conversation_history.append(
                {"role": "assistant", "content": CURRENT_CASE_ANSWERS[0]}
            )
