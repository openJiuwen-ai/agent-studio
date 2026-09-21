import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Iterator

from jiuwen.common.init import JiuWen
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import BaseChatModel
from jiuwen.common.llm_service.messages import AIMessage
from jiuwen.controller.task_planner.planning_modules.intention_detect_module import (
    DEFAULT_INTENT,
    IntentionDetectModule,
)
from jiuwen.extension.workflow_node.llm_chain import LLMChain
from jiuwen.extension.workflow_node.questioner import (
    JIUWEN_QUESTIONER_TYPE,
    MESSAGE_NODE_END,
    PARTIAL_CONTENT,
    WORKFLOW_FINAL,
    ExecutionStatus,
    Questioner,
    QuestionerState,
)
from jiuwen.extension.wrapper.workflow_wrapper import WorkflowWrapper
from jiuwen.serve.common.context import request as request_context
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from jiuwen.serve.controllers.execution.open_utils import async_ir_load
from jiuwen.serve.controllers.execution.types import ExecutionData
from jiuwen.serve.controllers.execution.utils import distribute_execution_request
from jiuwen.serve.schemas.orchestration_mgr import ExecutionRequest
from openjiuwen.core.runner import Runner
from openjiuwen.core.session import (
    END_COMP_TEMPLATE_BATCH_READER_TIMEOUT_KEY,
    END_COMP_TEMPLATE_RENDER_POSITION_TIMEOUT_KEY,
)
from openjiuwen.core.session.stream.base import CustomSchema


class FakeChatModel(BaseChatModel):
    """Deterministic controller model used to avoid online dependencies."""

    model_name: str = "fake-qwen"
    call_count: int = 0

    def _chat(self, messages, tools=None, **kwargs):
        type(self).call_count += 1
        if type(self).call_count == 1:
            return AIMessage(content=json.dumps({"result": 2}, ensure_ascii=False))
        if type(self).call_count == 2:
            return AIMessage(content=json.dumps({"result": 1}, ensure_ascii=False))
        return AIMessage(content="0")

    def _stream(self, messages, tools=None, **kwargs) -> Iterator[AIMessage]:
        yield self._chat(messages, tools, **kwargs)


class _FakeWorkflowModel:
    """Minimal openjiuwen model stub for adapted workflow components."""

    def __init__(self, answer_provider: Callable[[], list[str]]):
        self._answer_provider = answer_provider

    def _answer_text(self) -> str:
        answers = [str(item) for item in (self._answer_provider() or []) if str(item)]
        return "\n".join(answers) if answers else "local workflow executed"

    async def invoke(self, messages=None, **kwargs):
        return type(
            "FakeInvokeResult",
            (),
            {"content": self._answer_text(), "usage_metadata": None},
        )()

    async def stream(self, messages=None, **kwargs):
        for chunk in self._answer_text().splitlines() or [self._answer_text()]:
            yield type("FakeChunk", (), {"content": chunk})()


def _should_interrupt(answer_provider: Callable[[], list[str]]) -> bool:
    answers = [str(item) for item in (answer_provider() or [])]
    return any(marker in answer for answer in answers for marker in ("1.xxx", "2.xxx"))


def _is_redemption_question(inputs: Any) -> bool:
    query = ""
    if isinstance(inputs, dict):
        query = str(inputs.get("query", ""))
    else:
        query = str(inputs)
    return "赎回" in query and "第一笔" not in query


def init_openjiuwen_workflow_runtime(
    monkeypatch,
    *,
    resource_template_dir: Path,
    answer_provider: Callable[[], list[str]],
    intent_selector: Callable[
        [Any, list[Any], str, list[str], dict[str, Any]], str | None
    ]
    | None = None,
    should_interrupt: Callable[[], bool] | None = None,
    template_render_timeout: float = 0.05,
    template_batch_reader_timeout: float = 0.05,
) -> None:
    """Configure controller tests to run real openjiuwen workflow instances."""

    FakeChatModel.call_count = 0
    os.environ["EXECUTION_STATE_STORAGE_MEDIUM"] = "memory"
    os.environ["IR_CACHE_ENABLE"] = "false"
    os.environ["AGENT_CACHE_ENABLE"] = "false"
    os.environ["AGENT_GROUP_CACHE_ENABLE"] = "false"
    os.environ["USE_EI_INTENT"] = "false"
    os.environ["USE_AGENT_CORE_MODEL"] = "false"
    os.environ["USE_OPENJIUWEN_WORKFLOW"] = "true"
    os.environ["LLM_VERIFY_SSL"] = "false"
    os.environ["OPENJIUWEN_TEST_TEMPLATE_RENDER_TIMEOUT"] = str(template_render_timeout)
    os.environ["OPENJIUWEN_TEST_TEMPLATE_BATCH_READER_TIMEOUT"] = str(
        template_batch_reader_timeout
    )

    monkeypatch.setattr(
        ModelFactory,
        "get_model",
        lambda self, model_type, model_name, *args, **kwargs: FakeChatModel(),
    )

    if intent_selector is not None:

        async def _patched_detect_intent_with_llm(
            self, active_workflows, task_id, **kwargs
        ):
            self.get_function_category_info(
                active_workflows, kwargs.get("global_only", False)
            )
            query = self.context_manager.get_latest_user_content() or ""
            answers = [str(item) for item in (answer_provider() or [])]
            selected_intent = intent_selector(
                self, active_workflows, query, answers, kwargs
            )
            if selected_intent is not None:
                return selected_intent
            if self.category_2_agent_name_map:
                return next(iter(self.category_2_agent_name_map.values()))
            if self.intent_function_2_category_map:
                return next(iter(self.intent_function_2_category_map))
            return DEFAULT_INTENT

        monkeypatch.setattr(
            IntentionDetectModule,
            "_detect_intent_with_llm",
            _patched_detect_intent_with_llm,
        )

    fake_workflow_model = _FakeWorkflowModel(answer_provider)

    async def _fake_create_llm_instance(self):
        return fake_workflow_model

    monkeypatch.setattr(LLMChain, "_create_llm_instance", _fake_create_llm_instance)

    async def _fake_questioner_invoke(self, inputs, session, context):
        interrupt = (
            should_interrupt()
            if should_interrupt is not None
            else _should_interrupt(answer_provider) or _is_redemption_question(inputs)
        )
        if interrupt:
            question = fake_workflow_model._answer_text()
            node_id = session.get_component_id()
            node_name = getattr(self._config, "node_name", "") or node_id
            state = QuestionerState(
                response_num=1,
                question=question,
                status=ExecutionStatus.USER_INTERACT,
                inputs=inputs if isinstance(inputs, dict) else {},
            )
            self._node_state = state
            Questioner._store_state_to_session(state, session)
            custom_data = {
                "answer": question,
                "result": question,
                "node_id": node_id,
                "node_name": node_name,
                "node_type": JIUWEN_QUESTIONER_TYPE,
                "should_interrupt": True,
            }
            await session.write_custom_stream(
                CustomSchema(type=PARTIAL_CONTENT, index=0, data=custom_data)
            )
            await session.write_custom_stream(
                CustomSchema(type=MESSAGE_NODE_END, index=0, data=custom_data)
            )
            await session.write_custom_stream(
                CustomSchema(type=WORKFLOW_FINAL, index=0, data=custom_data)
            )
            await session.interact(question)

        outputs = {}
        for field_info in self._config.key_fields:
            outputs[field_info.field_name] = field_info.default_value or "mock"
        self._node_state = QuestionerState(
            status=ExecutionStatus.END,
            inputs=inputs if isinstance(inputs, dict) else {},
            extracted_key_fields=outputs,
        )
        Questioner._store_state_to_session(QuestionerState(), session)
        return outputs

    monkeypatch.setattr(Questioner, "invoke", _fake_questioner_invoke)

    async def _fake_questioner_stream(self, inputs, session, context):
        result = await _fake_questioner_invoke(self, inputs, session, context)
        yield result

    monkeypatch.setattr(Questioner, "stream", _fake_questioner_stream)

    original_build_envs = WorkflowWrapper._build_envs

    def _patched_build_envs(self, params):
        envs = original_build_envs(self, params)
        envs[END_COMP_TEMPLATE_RENDER_POSITION_TIMEOUT_KEY] = template_render_timeout
        envs[END_COMP_TEMPLATE_BATCH_READER_TIMEOUT_KEY] = template_batch_reader_timeout
        return envs

    monkeypatch.setattr(WorkflowWrapper, "_build_envs", _patched_build_envs)

    if not resource_template_dir.exists():
        raise FileNotFoundError(
            f"Prompt template directory not found: {resource_template_dir}"
        )
    JiuWen.init(prompt_dir=str(resource_template_dir), plugin_dir=None, cfg_file=None)


async def run_local_ir_with_openjiuwen_workflow(
    ir_path: Path,
    query: str,
    *,
    conversation_id: str | None = None,
    conversation_history: list[dict] | None = None,
    llm_extra_configs: dict[str, Any] | None = None,
    global_variables: dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
    user_id: str = "123",
) -> str:
    """Execute local IR through distribute_execution_request with openjiuwen workflow enabled."""

    req = ExecutionRequest.model_validate(
        {
            "conversationId": conversation_id
            or f"conversation_{int(time.time() * 1000)}",
            "query": query,
            "irPath": str(ir_path),
            "responseMode": "streaming",
            "executionMode": "sync",
            "params": {
                "conversationHistory": conversation_history or [],
                "pluginConfigs": [],
                "globalVariables": global_variables or {},
                "llmExtraConfigs": llm_extra_configs or {},
                "workflowSequence": [],
                "activeWorkflows": [],
            },
            "headers": headers
            or {
                "Content-Type": "application/json",
                "x-code": "123",
                "name": "Tom",
                "userid": "1212",
                "status": "123.1",
            },
            "userId": user_id,
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
    else:
        instance = await IRConverter.async_ir_to_workflow(ir_data)

    execution_data = ExecutionData(
        instance=instance,
        instance_type=ir_type,
        updated_time=int(time.time() * 1000),
    )
    fake_request = type("LocalRequest", (), {"headers": req.headers})()

    await Runner.start()
    token = request_context.set(fake_request)
    try:
        response = await distribute_execution_request(req, execution_data)
        body = []
        async for chunk in response.body_iterator:
            body.append(
                chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
            )
        return "".join(body)
    finally:
        request_context.reset(token)
        await Runner.stop()
