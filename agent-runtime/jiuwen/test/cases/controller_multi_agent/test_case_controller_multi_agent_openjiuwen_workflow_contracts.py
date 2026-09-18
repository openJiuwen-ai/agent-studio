import json
import os
import uuid
from pathlib import Path

import pytest
import pytest_asyncio

os.environ.setdefault("TGF_ENABLE", "false")

from openjiuwen.core.runner import Runner

from jiuwen.controller.context_manager.workflow_context import WorkflowContext
from jiuwen.controller.task_executor.handler.workflow_handler import WorkflowHandler
from jiuwen.extension.wrapper.workflow_instance_layer import (
    OpenJiuWenWorkflowInstanceLayer,
)
from jiuwen.orchestration.flow.constant import REQUEST_VARIABLES
from jiuwen.orchestration.flow.stream.base import StreamCode


CASE_DIR = Path(__file__).resolve().parent


@pytest_asyncio.fixture
async def openjiuwen_runner(monkeypatch):
    monkeypatch.setenv("USE_OPENJIUWEN_WORKFLOW", "true")
    monkeypatch.setenv("LLM_VERIFY_SSL", "false")
    await Runner.start()
    yield
    await Runner.stop()


def _load_workflow_ir(case_name: str, workflow_id: str) -> dict:
    workflow_dir = CASE_DIR / case_name / "workflow"
    for path in workflow_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("workflowId") == workflow_id:
            return data
    raise FileNotFoundError(f"workflow_id={workflow_id} not found in {workflow_dir}")


async def _create_openjiuwen_instance(
    workflow_ir: dict,
) -> OpenJiuWenWorkflowInstanceLayer:
    tag = f"pytest-openjiuwen-workflow-{uuid.uuid4().hex}"
    workflow_context = WorkflowContext(
        workflow_id=workflow_ir["workflowId"],
        workflow_name=workflow_ir.get("workflowName", ""),
        description=workflow_ir.get("description", ""),
        workflow_ir=workflow_ir,
        workflow_parameters={},
        config_name=tag,
    )
    instance = await WorkflowHandler.create_workflow_instance(
        workflow_context,
        conversation_id=f"conversation-{uuid.uuid4().hex}",
        user_id="pytest-user",
    )
    assert isinstance(instance, OpenJiuWenWorkflowInstanceLayer)
    return instance


async def _collect_stream(instance, query: str, params: dict) -> list:
    items = []
    stream_result = await instance.astream(inputs=query, params=params)
    async for item in stream_result:
        items.append(item)
    return items


def _base_params(**global_variables) -> dict:
    return {
        "global_variables": {
            "conversationId": "conversation-openjiuwen-workflow-contract",
            "userId": "pytest-user",
            "query": global_variables.pop("query", "hello"),
            "sys": {"conversationHistory": []},
            **global_variables,
        }
    }


@pytest.mark.asyncio
async def test_case01_real_openjiuwen_workflow_outputs_legacy_terminal_frames(
    openjiuwen_runner,
):  # noqa: redefined-outer-name
    workflow_ir = _load_workflow_ir(
        "test_case_controller_multi_agent_01",
        "32964224-6644-4483-94ae-40d1c8532c52",
    )
    instance = await _create_openjiuwen_instance(workflow_ir)

    items = await _collect_stream(instance, "hello", _base_params(query="hello"))
    codes = [item.code for item in items]

    assert StreamCode.PARTIAL_CONTENT.value in codes
    assert StreamCode.WORKFLOW_END.value in codes
    assert StreamCode.FINISH.value in codes
    finish = next(
        item for item in reversed(items) if item.code == StreamCode.FINISH.value
    )
    assert finish.data["node_type"] == "jiuwen.end"
    assert finish.data["user_fields"]["query"] == "hello"


@pytest.mark.asyncio
async def test_case20_real_openjiuwen_workflow_carries_user_fields_to_finish(
    openjiuwen_runner,
):  # noqa: redefined-outer-name
    workflow_ir = _load_workflow_ir(
        "test_case_controller_multi_agent_common_20",
        "01dc4906-e5f1-4a5d-9a0d-61edbc39ff7e",
    )
    instance = await _create_openjiuwen_instance(workflow_ir)

    items = await _collect_stream(
        instance,
        "default workflow",
        _base_params(query="default workflow", user_name="Alice"),
    )
    finish = next(
        item for item in reversed(items) if item.code == StreamCode.FINISH.value
    )

    assert finish.data["node_type"] == "jiuwen.end"
    assert finish.data["user_fields"]["user_name"] == "Alice"
    assert instance.get_runtime_context()[REQUEST_VARIABLES]["user_name"] == "Alice"


@pytest.mark.asyncio
async def test_case20_real_openjiuwen_workflow_missing_optional_field_still_finishes(
    openjiuwen_runner,
):  # noqa: redefined-outer-name
    workflow_ir = _load_workflow_ir(
        "test_case_controller_multi_agent_common_20",
        "01dc4906-e5f1-4a5d-9a0d-61edbc39ff7e",
    )
    instance = await _create_openjiuwen_instance(workflow_ir)

    items = await _collect_stream(
        instance, "default workflow", _base_params(query="default workflow")
    )

    assert items[-1].code == StreamCode.FINISH.value
    assert items[-1].data["node_type"] == "jiuwen.end"
    assert "user_fields" in items[-1].data
