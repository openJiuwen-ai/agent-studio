import asyncio
import json
import shutil
import time
from pathlib import Path

import pytest
from jiuwen.extension.wrapper.model_wrapper import ModelWrapper
from jiuwen.extension.wrapper.test.mock.contract_model_mock import (
    get_contract_model_calls,
    register_contract_mock_model,
    reset_contract_model_calls,
)
from jiuwen.integration.agent_core_model_new import AgentCoreModelLayer
from jiuwen.test.cases.controller_multi_agent.test_case_controller_multi_agent_27 import (
    CASE_DIR,
    _copy_case_ir_bundle,
)
from jiuwen.test.cases.controller_multi_agent.test_case_controller_multi_agent_27_southbound_contracts import (
    END_WORKFLOW_ID,
    SERVICE_WORKFLOW_ID,
    START_WORKFLOW_ID,
    _IntegrationRegistry,
    _LocalWorkflowAdapter,
    _RecordingWorkflowRuntime,
    _build_end_stream_data,
    _build_message_end_stream_data,
    _init_contract_runtime,
    _run_local_ir_request,
)
from openjiuwen.core.foundation.llm import Model, ModelClientConfig, ModelRequestConfig
from openjiuwen.core.runner import Runner


class ConcreteModelWrapper(ModelWrapper):
    """Concrete model wrapper used by controller model contract tests."""


class RecordingModelWrapper(ModelWrapper):
    """Model wrapper that records normalized layer calls."""

    def __init__(self):
        self.calls = []

    async def ainvoke(self, inputs, **kwargs):
        self.calls.append({"inputs": inputs, "kwargs": kwargs})
        return await super().ainvoke(inputs, **kwargs)


def _rewrite_child_global_intent_to_workflow(ir_path: Path) -> None:
    """Make the copied child IR use a workflow handler for its global intent."""
    root_ir = json.loads(ir_path.read_text(encoding="utf-8"))
    child_ref = root_ir["configs"]["agents"][0]["ir_path"]
    if ".." in child_ref:
        raise ValueError(f"Potential path traversal in child_ref: {child_ref}")
    child_ir_path = Path(child_ref)
    child_ir = json.loads(child_ir_path.read_text(encoding="utf-8"))
    global_intent = child_ir["configs"]["global_intents"][0]
    service_workflow = next(
        workflow
        for workflow in child_ir["configs"]["workflows"]
        if workflow.get("id") == SERVICE_WORKFLOW_ID
    )
    global_intent["handler_type"] = "Workflow"
    global_intent["handler"] = {
        "id": SERVICE_WORKFLOW_ID,
        "name": service_workflow["name"],
        "ir_path": service_workflow["ir_path"],
    }
    child_ir_path.write_text(
        json.dumps(child_ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _register_contract_model(model_id: str) -> None:
    register_contract_mock_model()
    client_config = ModelClientConfig(
        client_id=f"{model_id}_client",
        client_provider="ContractMock",
        api_key="mock_api_key",
        api_base="mock_api_base",
    )
    request_config = ModelRequestConfig(
        model="contract_mock_model",
        temperature=0.1,
        top_p=0.2,
    )

    def model_factory():
        return Model(model_client_config=client_config, model_config=request_config)

    Runner.resource_mgr.add_model(model_id=model_id, model=model_factory)


@pytest.fixture()
def local_ir_path(monkeypatch, request):
    _init_contract_runtime(monkeypatch)
    tmp_path = CASE_DIR / f".tmp_model_contract_27_{int(time.time() * 1000000)}"
    tmp_path.mkdir(parents=True, exist_ok=False)
    try:
        ir_path = _copy_case_ir_bundle(tmp_path)
        marker = request.node.get_closest_marker("global_intent_workflow")
        if marker:
            _rewrite_child_global_intent_to_workflow(ir_path)
        yield ir_path
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
        _IntegrationRegistry.clear()


def _build_workflow_runtime() -> _RecordingWorkflowRuntime:
    return _RecordingWorkflowRuntime(
        {
            START_WORKFLOW_ID: [
                [
                    _build_message_end_stream_data(
                        workflow_id=START_WORKFLOW_ID,
                        answer="start workflow answer from model contract",
                        node_id="node_start_message",
                        node_name="node_start_message",
                        node_type="jiuwen.message",
                    ),
                    _build_end_stream_data(
                        workflow_id=START_WORKFLOW_ID,
                        answer="start workflow answer from model contract",
                    ),
                ]
            ],
            SERVICE_WORKFLOW_ID: [
                [
                    _build_message_end_stream_data(
                        workflow_id=SERVICE_WORKFLOW_ID,
                        answer="service workflow answer from model contract",
                        node_id="node_service_message",
                        node_name="node_service_message",
                        node_type="jiuwen.message",
                    ),
                    _build_end_stream_data(
                        workflow_id=SERVICE_WORKFLOW_ID,
                        answer="service workflow answer from model contract",
                    ),
                ]
            ],
            END_WORKFLOW_ID: [
                [
                    _build_message_end_stream_data(
                        workflow_id=END_WORKFLOW_ID,
                        answer="end workflow answer from model contract",
                        node_id="node_end_message",
                        node_name="node_end_message",
                        node_type="jiuwen.message",
                    ),
                    _build_end_stream_data(
                        workflow_id=END_WORKFLOW_ID,
                        answer="end workflow answer from model contract",
                    ),
                ]
            ],
        }
    )


def _setup_contract_model(model_layer=None):
    reset_contract_model_calls()
    _register_contract_model("fake-qwen")
    _register_contract_model("Qwen/Qwen2.5-72B-Instruct")
    _IntegrationRegistry.set_model(
        model_layer or AgentCoreModelLayer(ConcreteModelWrapper())
    )


@pytest.mark.global_intent_workflow
def test_case27_contract_model_drives_global_intent_to_workflow(local_ir_path: Path):
    _setup_contract_model()
    workflow_runtime = _build_workflow_runtime()
    _IntegrationRegistry.set_workflow(_LocalWorkflowAdapter(runtime=workflow_runtime))

    response_text = asyncio.run(
        _run_local_ir_request(
            ir_path=local_ir_path,
            query="__MODEL_CONTRACT_ROUTE_CHILD_THEN_GLOBAL_WORKFLOW__",
            conversation_id=f"conversation_{int(time.time() * 1000)}",
        )
    )

    model_calls = get_contract_model_calls()
    assert len([call for call in model_calls if call["method"] == "invoke"]) >= 2
    assert any(
        "__MODEL_CONTRACT_ROUTE_CHILD_THEN_GLOBAL_WORKFLOW__"
        in str(call["messages"][-1]["content"])
        for call in model_calls
    )

    workflow_ids = [call["workflow_id"] for call in workflow_runtime.calls]
    assert SERVICE_WORKFLOW_ID in workflow_ids
    service_call = next(
        call
        for call in workflow_runtime.calls
        if call["workflow_id"] == SERVICE_WORKFLOW_ID
    )
    assert (
        service_call["query"] == "__MODEL_CONTRACT_ROUTE_CHILD_THEN_GLOBAL_WORKFLOW__"
    )
    assert "service workflow answer from model contract" in response_text
    assert "interrupt" in response_text
    assert '"event":"error"' not in response_text


def test_case27_contract_model_drives_normal_workflow(local_ir_path: Path):
    _setup_contract_model()
    workflow_runtime = _build_workflow_runtime()
    _IntegrationRegistry.set_workflow(_LocalWorkflowAdapter(runtime=workflow_runtime))

    response_text = asyncio.run(
        _run_local_ir_request(
            ir_path=local_ir_path,
            query="__MODEL_CONTRACT_ROUTE_CHILD_THEN_NORMAL_WORKFLOW__",
            conversation_id=f"conversation_{int(time.time() * 1000)}",
        )
    )

    model_calls = get_contract_model_calls()
    assert len([call for call in model_calls if call["method"] == "invoke"]) >= 2

    workflow_ids = [call["workflow_id"] for call in workflow_runtime.calls]
    assert START_WORKFLOW_ID in workflow_ids
    assert SERVICE_WORKFLOW_ID in workflow_ids
    service_call = next(
        call
        for call in workflow_runtime.calls
        if call["workflow_id"] == SERVICE_WORKFLOW_ID
    )
    assert (
        service_call["query"] == "__MODEL_CONTRACT_ROUTE_CHILD_THEN_NORMAL_WORKFLOW__"
    )
    assert "service workflow answer from model contract" in response_text
    assert '"event":"error"' not in response_text


def test_case27_contract_model_invalid_output_falls_back_safely(local_ir_path: Path):
    _setup_contract_model()
    workflow_runtime = _build_workflow_runtime()
    _IntegrationRegistry.set_workflow(_LocalWorkflowAdapter(runtime=workflow_runtime))

    response_text = asyncio.run(
        _run_local_ir_request(
            ir_path=local_ir_path,
            query="__MODEL_CONTRACT_INVALID_INTENTION__",
            conversation_id=f"conversation_{int(time.time() * 1000)}",
        )
    )

    model_calls = get_contract_model_calls()
    assert len([call for call in model_calls if call["method"] == "invoke"]) == 1
    assert workflow_runtime.calls == []
    assert "task_end" in response_text
    assert '"event":"error"' not in response_text


@pytest.mark.global_intent_workflow
def test_case27_agent_core_style_layer_keeps_controller_contract(local_ir_path: Path):
    wrapped_model = RecordingModelWrapper()
    layer = AgentCoreModelLayer(wrapped_model)
    _setup_contract_model(model_layer=layer)
    workflow_runtime = _build_workflow_runtime()
    _IntegrationRegistry.set_workflow(_LocalWorkflowAdapter(runtime=workflow_runtime))

    response_text = asyncio.run(
        _run_local_ir_request(
            ir_path=local_ir_path,
            query="__MODEL_CONTRACT_ROUTE_CHILD_THEN_GLOBAL_WORKFLOW__",
            conversation_id=f"conversation_{int(time.time() * 1000)}",
        )
    )

    assert len(wrapped_model.calls) >= 2
    assert any(
        call["kwargs"].get("model_id") == "fake-qwen" for call in wrapped_model.calls
    )
    assert SERVICE_WORKFLOW_ID in [
        call["workflow_id"] for call in workflow_runtime.calls
    ]
    assert "service workflow answer from model contract" in response_text
    assert '"event":"error"' not in response_text
