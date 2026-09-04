import asyncio
import json

from jiuwen.common.llm_service.messages import Tool
from jiuwen.controller.task_planner.planning_modules.task_understanding_module import (
    TaskUnderstandingModule,
)
from jiuwen.extension.wrapper.model_wrapper import ModelWrapper
from jiuwen.extension.wrapper.test.mock.contract_model_mock import (
    get_contract_model_calls,
    register_contract_mock_model,
    reset_contract_model_calls,
)
from jiuwen.integration.agent_core_legacy_chat_model import AgentCoreLegacyChatModel
from jiuwen.integration.agent_core_model_new import AgentCoreModelLayer
from jiuwen.planner.common.stream_post_utils import _format_yield_result
from jiuwen.serve.controllers.execution.ir_converter import IRConverter
from openjiuwen.core.foundation.llm import Model, ModelClientConfig, ModelRequestConfig
from openjiuwen.core.runner import Runner


class ConcreteModelWrapper(ModelWrapper):
    """Concrete model wrapper used by contract tests."""


class BoundModelWrapper:
    """Bind ModelWrapper's southbound parameters for planner modules."""

    def __init__(self, wrapper: ModelWrapper, model_id: str, session_id: str):
        self.wrapper = wrapper
        self.model_id = model_id
        self.session_id = session_id

    async def ainvoke(self, inputs):
        return await self.wrapper.ainvoke(
            inputs=inputs,
            model_id=self.model_id,
            session_id=self.session_id,
        )


def _register_model(model_id: str) -> None:
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


def test_model_wrapper_ainvoke_records_intention_inputs():
    reset_contract_model_calls()
    model_id = "contract_mock_intention"
    _register_model(model_id)

    result = asyncio.run(
        ConcreteModelWrapper().ainvoke(
            inputs={
                "messages": [
                    {"role": "system", "content": "intention classifier"},
                    {"role": "user", "content": "__MODEL_CONTRACT_INTENTION__"},
                ]
            },
            model_id=model_id,
            session_id="session_intention",
            temperature=0.3,
        )
    )

    assert result.content == '{"result": "7", "reason": "mock intention"}'
    calls = get_contract_model_calls()
    assert len(calls) == 1
    assert calls[0]["method"] == "invoke"
    assert calls[0]["messages"][-1]["content"] == "__MODEL_CONTRACT_INTENTION__"
    assert calls[0]["kwargs"]["temperature"] == 0.3


def test_agent_core_model_layer_accepts_changed_input_envelope():
    reset_contract_model_calls()
    model_id = "contract_mock_layer_envelope"
    _register_model(model_id)

    result = asyncio.run(
        AgentCoreModelLayer(ConcreteModelWrapper()).ainvoke(
            {
                "inputs": {
                    "messages": [
                        {"role": "system", "content": "intention classifier"},
                        {"role": "user", "content": "__MODEL_CONTRACT_INTENTION__"},
                    ]
                },
                "model_id": model_id,
                "session_id": "session_layer_envelope",
                "agent_id": "agent_layer_envelope",
                "temperature": 0.4,
            }
        )
    )

    assert result.content == '{"result": "7", "reason": "mock intention"}'
    calls = get_contract_model_calls()
    assert len(calls) == 1
    assert calls[0]["messages"][-1]["content"] == "__MODEL_CONTRACT_INTENTION__"
    assert calls[0]["kwargs"]["temperature"] == 0.4


def test_agent_core_model_layer_resolves_default_identifiers():
    reset_contract_model_calls()
    model_id = "contract_mock_layer_default_ids"
    _register_model(model_id)

    result = asyncio.run(
        AgentCoreModelLayer(
            ConcreteModelWrapper(),
            default_model_id=model_id,
            default_session_id="session_layer_default",
            default_agent_id="agent_layer_default",
        ).ainvoke(
            {
                "messages": [
                    {"role": "system", "content": "intention classifier"},
                    {"role": "user", "content": "__MODEL_CONTRACT_INTENTION__"},
                ]
            }
        )
    )

    assert result.content == '{"result": "7", "reason": "mock intention"}'
    calls = get_contract_model_calls()
    assert len(calls) == 1
    assert calls[0]["method"] == "invoke"


def test_ir_converter_registers_agent_core_model_from_ir_config():
    reset_contract_model_calls()
    register_contract_mock_model()
    model_id = "contract_mock_ir_converter_registration"

    layer = IRConverter._create_agent_core_llm_model(
        {
            "modelName": "contract_mock_model",
            "modelType": "qwen",
            "hyperParameters": {"temperature": 0.3, "top_p": 0.8},
            "extension": {
                "agentCoreModelId": model_id,
                "client_provider": "ContractMock",
                "api_key": "mock_api_key",
                "api_base": "mock_api_base",
            },
        },
        task_id="task_ir_converter_registration",
        agent_id="agent_ir_converter_registration",
        conversation_id="conversation_ir_converter_registration",
    )

    result = asyncio.run(
        layer.ainvoke(
            {
                "messages": [
                    {"role": "system", "content": "intention classifier"},
                    {"role": "user", "content": "__MODEL_CONTRACT_INTENTION__"},
                ]
            }
        )
    )

    assert layer.default_model_id == model_id
    assert layer.default_session_id == "conversation_ir_converter_registration"
    assert result.content == '{"result": "7", "reason": "mock intention"}'
    calls = get_contract_model_calls()
    assert len(calls) == 1
    assert calls[0]["method"] == "invoke"
    assert calls[0]["messages"][-1]["content"] == "__MODEL_CONTRACT_INTENTION__"
    assert calls[0]["kwargs"]["temperature"] is None


def test_ir_converter_agent_core_model_registration_is_idempotent():
    reset_contract_model_calls()
    register_contract_mock_model()
    model_id = "contract_mock_ir_converter_idempotent"
    model_config = {
        "modelName": "contract_mock_model",
        "modelType": "qwen",
        "hyperParameters": {"temperature": 0.3, "top_p": 0.8},
        "extension": {
            "agentCoreModelId": model_id,
            "client_provider": "ContractMock",
            "api_key": "mock_api_key",
            "api_base": "mock_api_base",
        },
    }

    first_layer = IRConverter._create_agent_core_llm_model(
        model_config,
        task_id="task_ir_converter_idempotent_1",
        agent_id="agent_ir_converter_idempotent_1",
        conversation_id="conversation_ir_converter_idempotent",
    )
    second_layer = IRConverter._create_agent_core_llm_model(
        model_config,
        task_id="task_ir_converter_idempotent_2",
        agent_id="agent_ir_converter_idempotent_2",
        conversation_id="conversation_ir_converter_idempotent",
    )

    assert first_layer.default_model_id == model_id
    assert second_layer.default_model_id == model_id


def test_ir_converter_registers_agent_core_model_with_legacy_config_aliases():
    reset_contract_model_calls()
    register_contract_mock_model()
    model_id = "contract_mock_ir_converter_legacy_aliases"

    layer = IRConverter._create_agent_core_llm_model(
        {
            "modelName": "contract_mock_model",
            "modelType": "qwen",
            "hyperParameters": {"temperature": 0.3, "top_p": 0.8},
            "extension": {
                "agentCoreModelId": model_id,
                "client_provider": "ContractMock",
                "apiKey": "mock_api_key",
                "baseUrl": "mock_api_base",
            },
        },
        task_id="task_ir_converter_legacy_aliases",
        agent_id="agent_ir_converter_legacy_aliases",
        conversation_id="conversation_ir_converter_legacy_aliases",
    )

    assert layer.default_model_id == model_id


def test_ir_converter_disables_ssl_for_http_agent_core_model_endpoint():
    ssl_values = IRConverter._resolve_agent_core_ssl_values(
        "http://127.0.0.1:6001/v1/chat/completions/qwen_mock",
        extension={},
        resolved_config={},
    )

    assert ssl_values["verify_ssl"] is False
    assert ssl_values["ssl_cert"] is None


def test_ir_converter_uses_direct_model_for_legacy_full_chat_endpoint():
    assert IRConverter._use_legacy_direct_model(
        "OpenAI",
        "http://127.0.0.1:6001/v1/chat/completions/qwen_mock",
    )


def test_ir_converter_keeps_standard_openai_base_url_on_model_wrapper():
    assert not IRConverter._use_legacy_direct_model(
        "OpenAI", "http://127.0.0.1:6001/v1"
    )
    assert not IRConverter._use_legacy_direct_model(
        "ContractMock",
        "http://127.0.0.1:6001/v1/chat/completions/qwen_mock",
    )


def test_legacy_chat_direct_model_preserves_jiuwen_endpoint_contract():
    model = AgentCoreLegacyChatModel(
        api_base="http://127.0.0.1:6001/v1/chat/completions/qwen_mock",
        api_key="mock_api_key",
        model_name="Qwen/Qwen2.5-72B-Instruct",
        temperature=0.1,
        top_p=0.2,
        verify_ssl=False,
    )

    payload = model._build_payload(
        [{"role": "user", "content": "我要赎回理财"}],
        tools=None,
        temperature=None,
        top_p=None,
        max_tokens=None,
        stop=None,
        model=None,
        stream=False,
        extra_params={"trace_callback": lambda: None},
    )
    response = model._parse_assistant_message(
        {
            "choices": [
                {
                    "message": {"content": '{"class": "分类2"}'},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
        }
    )
    chunk = model._parse_stream_line(
        'data: {"choices": [{"delta": {"content": "理财"}, "finish_reason": null}], '
        '"usage": {"total_tokens": 1}}'
    )

    assert payload["model"] == "Qwen/Qwen2.5-72B-Instruct"
    assert payload["messages"][-1]["content"] == "我要赎回理财"
    assert payload["temperature"] == 0.1
    assert payload["top_p"] == 0.2
    assert "trace_callback" not in payload
    assert response.content == '{"class": "分类2"}'
    assert response.usage_metadata.total_tokens == 7
    assert chunk.content == "理财"


def test_legacy_chat_direct_model_filters_non_json_values_from_payload():
    model = AgentCoreLegacyChatModel(
        api_base="http://127.0.0.1:6001/v1/chat/completions/deepseek_mock",
        api_key="mock_api_key",
        model_name="deepseek-chat",
    )

    payload = model._build_payload(
        [{"role": "user", "content": "hello", "metadata": {"on_event": lambda: None}}],
        tools=[
            {
                "name": "mock_tool",
                "parameters": {"callback": lambda: None, "type": "object"},
            }
        ],
        temperature=None,
        top_p=None,
        max_tokens=None,
        stop=None,
        model=None,
        stream=False,
        extra_params={"runtime_hook": lambda: None},
    )

    json.dumps(payload, ensure_ascii=False)
    assert "runtime_hook" not in payload
    assert "on_event" not in payload["messages"][0]["metadata"]
    assert "callback" not in payload["tools"][0]["function"]["parameters"]


def test_ir_converter_normalizes_legacy_model_type_to_agent_core_provider():
    assert IRConverter._normalize_agent_core_client_provider("qwen") == "OpenAI"
    assert IRConverter._normalize_agent_core_client_provider("deepseek") == "OpenAI"
    assert IRConverter._normalize_agent_core_client_provider("openai") == "OpenAI"
    assert (
        IRConverter._normalize_agent_core_client_provider("SiliconFlow")
        == "SiliconFlow"
    )


def test_ir_converter_keeps_legacy_customer_chat_llm_on_model_factory_by_default():
    assert not IRConverter._use_agent_core_model(
        {
            "modelName": "mock_model_name",
            "modelType": "customer_chat_llm",
            "hyperParameters": {},
            "extension": {},
        }
    )


def test_ir_converter_allows_explicit_agent_core_model_for_custom_provider():
    assert IRConverter._use_agent_core_model(
        {
            "modelName": "mock_model_name",
            "modelType": "customer_chat_llm",
            "extension": {"useAgentCoreModel": "true"},
        }
    )


def test_agent_core_model_layer_exposes_legacy_model_name():
    layer = AgentCoreModelLayer(
        ConcreteModelWrapper(),
        default_model_id="legacy-compatible-model",
    )

    assert layer.model_name == "legacy-compatible-model"

    layer.model_name = "updated-model"
    assert layer.default_model_id == "updated-model"
    assert layer.model_name == "updated-model"


def test_agent_core_model_layer_resolves_runtime_data_identifiers():
    reset_contract_model_calls()
    model_id = "contract_mock_layer_runtime_data_ids"
    _register_model(model_id)

    result = asyncio.run(
        AgentCoreModelLayer(ConcreteModelWrapper()).ainvoke(
            {
                "messages": [
                    {"role": "system", "content": "intention classifier"},
                    {"role": "user", "content": "__MODEL_CONTRACT_INTENTION__"},
                ]
            },
            runtime_data={
                "model_id": model_id,
                "conversation_id": "session_layer_runtime_data",
                "agent_id": "agent_layer_runtime_data",
            },
        )
    )

    assert result.content == '{"result": "7", "reason": "mock intention"}'
    calls = get_contract_model_calls()
    assert len(calls) == 1
    assert calls[0]["method"] == "invoke"


def test_agent_core_model_layer_sync_invoke_uses_async_contract():
    reset_contract_model_calls()
    model_id = "contract_mock_layer_sync_invoke"
    _register_model(model_id)

    result = AgentCoreModelLayer(
        ConcreteModelWrapper(),
        default_model_id=model_id,
        default_session_id="session_layer_sync_invoke",
    ).invoke(
        {
            "messages": [
                {"role": "system", "content": "intention classifier"},
                {"role": "user", "content": "__MODEL_CONTRACT_INTENTION__"},
            ]
        }
    )

    assert result.content == '{"result": "7", "reason": "mock intention"}'
    calls = get_contract_model_calls()
    assert len(calls) == 1
    assert calls[0]["method"] == "invoke"


def test_agent_core_model_layer_sync_stream_uses_async_contract():
    reset_contract_model_calls()
    model_id = "contract_mock_layer_sync_stream"
    _register_model(model_id)

    outputs = list(
        AgentCoreModelLayer(
            ConcreteModelWrapper(),
            default_model_id=model_id,
            default_session_id="session_layer_sync_stream",
        ).stream([{"role": "user", "content": "__MODEL_CONTRACT_STREAM_TEXT__"}])
    )

    assert [item.content for item in outputs] == ["mock ", "stream", "mock stream"]
    assert outputs[-1].usage_metadata.finish_reason == "stop"
    calls = get_contract_model_calls()
    assert len(calls) == 1
    assert calls[0]["method"] == "stream"


def test_agent_core_model_layer_stream_function_call_text_frames_contract():
    reset_contract_model_calls()
    model_id = "contract_mock_layer_stream_function_text"
    _register_model(model_id)

    async def collect():
        outputs = []
        async for item in AgentCoreModelLayer(
            ConcreteModelWrapper(),
            default_model_id=model_id,
            default_session_id="session_layer_stream_function_text",
        ).stream_function_call(
            messages=[{"role": "user", "content": "__MODEL_CONTRACT_STREAM_TEXT__"}],
            functions=[],
            runtime_data={},
        ):
            outputs.append(item)
        return outputs

    outputs = asyncio.run(collect())

    assert outputs[0] == {"role": "assistant", "content": "mock "}
    assert outputs[1] == {"role": "assistant", "content": "stream"}
    assert outputs[2]["llm_output"]["content"] == "mock stream"
    assert outputs[2]["llm_output"]["role"] == "assistant"
    assert outputs[3]["time_consumption"]["total_latency"] == 0.0
    calls = get_contract_model_calls()
    assert len(calls) == 1
    assert calls[0]["method"] == "stream"


def test_model_wrapper_usage_metadata_is_consumed_by_legacy_stream_formatter():
    reset_contract_model_calls()
    model_id = "contract_mock_stream_usage"
    _register_model(model_id)

    async def collect():
        raw_stream = ConcreteModelWrapper().astream(
            inputs=[{"role": "user", "content": "__MODEL_CONTRACT_STREAM_USAGE__"}],
            model_id=model_id,
            session_id="session_stream_usage",
        )
        llm_output = {}
        time_dict = {}
        model_stat = {}
        model_usage = {}
        frames = []
        async for item in _format_yield_result(
            raw_stream,
            llm_output,
            time_dict,
            model_stat,
            model_usage,
        ):
            frames.append(item)
        return frames, llm_output, time_dict, model_stat, model_usage

    frames, llm_output, time_dict, model_stat, model_usage = asyncio.run(collect())

    assert frames[0] == {"role": "assistant", "content": "usage "}
    assert frames[1] == {"role": "assistant", "content": "stream"}
    assert frames[2]["llm_output"]["content"] == "usage stream"
    assert llm_output["content"] == "usage stream"
    assert time_dict["total_latency"] >= 0
    assert model_usage == {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18}
    assert model_stat == {}


def test_task_understanding_module_uses_model_wrapper():
    reset_contract_model_calls()
    model_id = "contract_mock_task_understanding"
    _register_model(model_id)

    bound_llm = BoundModelWrapper(
        ConcreteModelWrapper(),
        model_id=model_id,
        session_id="session_task_understanding",
    )
    module = TaskUnderstandingModule(llm=bound_llm, context_manager=None)
    module._build_system_prompt = lambda: "task understanding"
    module._build_user_prompt = lambda query, chat_history, available_intents: (
        f"query={query}; history={chat_history}; intents={available_intents}"
    )

    result = asyncio.run(
        module.invoke(
            query="__MODEL_CONTRACT_TASK_COMPLEX__",
            chat_history=[{"role": "user", "content": "previous turn"}],
            available_intents=["redeem", "complaint"],
            task_id="task_contract",
        )
    )

    assert result.is_complex is True
    calls = get_contract_model_calls()
    assert len(calls) == 1
    assert calls[0]["method"] == "invoke"
    assert "__MODEL_CONTRACT_TASK_COMPLEX__" in calls[0]["messages"][-1]["content"]


def test_model_wrapper_astream_text_contract():
    reset_contract_model_calls()
    model_id = "contract_mock_stream_text"
    _register_model(model_id)

    async def collect():
        outputs = []
        async for item in ConcreteModelWrapper().astream(
            inputs=[{"role": "user", "content": "__MODEL_CONTRACT_STREAM_TEXT__"}],
            model_id=model_id,
            session_id="session_stream_text",
        ):
            outputs.append(item)
        return outputs

    outputs = asyncio.run(collect())

    assert [item.content for item in outputs] == ["mock ", "stream", "mock stream"]
    assert outputs[-1].usage_metadata.finish_reason == "stop"
    calls = get_contract_model_calls()
    assert len(calls) == 1
    assert calls[0]["method"] == "stream"


def test_model_wrapper_astream_tool_call_contract():
    reset_contract_model_calls()
    model_id = "contract_mock_stream_tool"
    _register_model(model_id)

    async def collect():
        outputs = []
        async for item in ConcreteModelWrapper().astream(
            inputs={
                "messages": [
                    {"role": "user", "content": "__MODEL_CONTRACT_STREAM_TOOL_CALL__"}
                ],
                "tools": [
                    Tool(
                        name="mock_contract_tool",
                        description="contract tool",
                        parameters={
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                        principle="Use this tool only when requested.",
                        results="Return contract data.",
                    )
                ],
            },
            model_id=model_id,
            session_id="session_stream_tool",
        ):
            outputs.append(item)
        return outputs

    outputs = asyncio.run(collect())

    assert len(outputs) == 1
    assert outputs[0].tool_calls[0].name == "mock_contract_tool"
    assert outputs[0].tool_calls[0].args == {"query": "stream"}
    assert outputs[0].usage_metadata.finish_reason == "function_call"
    calls = get_contract_model_calls()
    assert len(calls) == 1
    assert calls[0]["method"] == "stream"
    assert calls[0]["tools"][0].name == "mock_contract_tool"


def test_model_wrapper_ainvoke_tool_call_contract():
    reset_contract_model_calls()
    model_id = "contract_mock_invoke_tool"
    _register_model(model_id)

    result = asyncio.run(
        ConcreteModelWrapper().ainvoke(
            inputs=[{"role": "user", "content": "__MODEL_CONTRACT_TOOL_CALL__"}],
            model_id=model_id,
            session_id="session_invoke_tool",
        )
    )

    assert result.tool_calls[0].name == "mock_contract_tool"
    assert result.tool_calls[0].args == {"query": "contract"}
    calls = get_contract_model_calls()
    assert len(calls) == 1
    assert calls[0]["method"] == "invoke"
