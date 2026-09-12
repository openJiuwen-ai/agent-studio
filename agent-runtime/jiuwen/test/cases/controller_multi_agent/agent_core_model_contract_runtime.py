import json
import uuid
from dataclasses import dataclass
from typing import Any

from jiuwen.extension.wrapper.model_wrapper import ModelWrapper
from jiuwen.extension.wrapper.test.mock.contract_model_mock import (
    register_contract_mock_model,
    reset_contract_model_calls,
    set_contract_model_responses,
    set_contract_model_stream_responses,
)
from openjiuwen.core.foundation.llm import Model, ModelClientConfig, ModelRequestConfig
from openjiuwen.core.foundation.llm.schema.message_chunk import AssistantMessageChunk
from openjiuwen.core.foundation.llm.schema.tool_call import ToolCall
from openjiuwen.core.runner import Runner


@dataclass
class AgentCoreModelCall:
    inputs: Any
    session_id: str
    kwargs: dict[str, Any]


@dataclass
class AgentCoreFunctionCallRecord:
    messages: Any
    functions: Any
    runtime_data: dict[str, Any]


class ConcreteAgentCoreModelWrapper(ModelWrapper):
    """Concrete openjiuwen model wrapper for controller contract tests."""


class AgentCoreModelWrapperRuntime:
    """Run controller model calls through the real ModelWrapper and a fake provider."""

    def __init__(
        self,
        responses: list[Any],
        *,
        model_id: str | None = None,
        session_id: str = "controller_multi_agent_contract_session",
    ):
        self.calls: list[AgentCoreModelCall] = []
        self.model_id = model_id or f"contract_model_{uuid.uuid4().hex}"
        self.session_id = session_id
        self.wrapper = ConcreteAgentCoreModelWrapper()
        _register_contract_model(self.model_id)
        reset_contract_model_calls()
        set_contract_model_responses(_normalize_responses(responses))

    async def ainvoke(
        self,
        inputs,
        model_id: str = "",
        session_id: str = "",
        **kwargs,
    ):
        effective_model_id = self.model_id
        effective_session_id = session_id or self.session_id
        self.calls.append(
            AgentCoreModelCall(
                inputs=inputs,
                session_id=effective_session_id,
                kwargs={"model_id": effective_model_id, **kwargs},
            )
        )
        return await self.wrapper.ainvoke(
            inputs=inputs,
            model_id=effective_model_id,
            session_id=effective_session_id,
            **kwargs,
        )


class AgentCoreFunctionCallModelRuntime:
    """Register a fake provider and record function-call streaming inputs."""

    def __init__(
        self,
        *,
        model_id: str | None = None,
        session_id: str = "controller_multi_agent_function_call_session",
    ):
        self.calls: list[AgentCoreFunctionCallRecord] = []
        self.model_id = model_id or f"contract_tool_model_{uuid.uuid4().hex}"
        self.session_id = session_id
        self.wrapper = ConcreteAgentCoreModelWrapper()
        _register_contract_model(self.model_id)
        reset_contract_model_calls()

    async def astream(
        self,
        inputs,
        model_id: str = "",
        session_id: str = "",
        **kwargs,
    ):
        messages = inputs.get("messages", []) if isinstance(inputs, dict) else []
        functions = inputs.get("tools", []) if isinstance(inputs, dict) else []
        runtime_data = kwargs.get("runtime_data") or {}
        self.calls.append(
            AgentCoreFunctionCallRecord(
                messages=messages,
                functions=functions,
                runtime_data=runtime_data,
            )
        )
        if len(self.calls) == 1:
            stream_response = self._build_tool_call_stream_response(messages)
        else:
            stream_response = [AssistantMessageChunk(content="done")]
        set_contract_model_stream_responses([stream_response])
        async for item in self.wrapper.astream(
            inputs=inputs,
            model_id=self.model_id,
            session_id=session_id or self._resolve_session_id(runtime_data),
            **kwargs,
        ):
            yield item

    @staticmethod
    def _build_tool_call_stream_response(messages) -> list[AssistantMessageChunk]:
        latest_user = ""
        if messages:
            latest_user = messages[-1].get("content", "")
        return [
            AssistantMessageChunk(
                content="",
                tool_calls=[
                    ToolCall(
                        id="tool_mcp_1",
                        type="function",
                        name="McpTimeout",
                        arguments=json.dumps(
                            {"input": latest_user}, ensure_ascii=False
                        ),
                    )
                ],
            )
        ]

    def _resolve_session_id(self, runtime_data: dict[str, Any]) -> str:
        return (
            runtime_data.get("session_id")
            or runtime_data.get("conversation_id")
            or runtime_data.get("task_id")
            or self.session_id
        )


def _normalize_responses(responses: list[Any]) -> list[Any]:
    normalized = []
    for response in responses:
        content = getattr(response, "content", response)
        normalized.append(content)
    return normalized


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
        temperature=0.2,
        top_p=0.9,
    )

    def model_factory():
        return Model(model_client_config=client_config, model_config=request_config)

    Runner.resource_mgr.add_model(model_id=model_id, model=model_factory)
