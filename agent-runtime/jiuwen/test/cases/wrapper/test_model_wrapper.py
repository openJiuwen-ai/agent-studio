import os
from typing import Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from jiuwen.common.llm_service.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage as OldSystemMessage,
    Tool,
    ToolCall as OldToolCall,
    UsageMetadata as OldUsageMetadata,
)
from jiuwen.extension.wrapper.model_wrapper import ModelWrapper
from openjiuwen.core.common.logging import llm_logger
from openjiuwen.core.foundation.llm import Model, ModelClientConfig, ModelRequestConfig
from openjiuwen.core.foundation.llm.schema.message import (
    UserMessage,
    AssistantMessage,
    SystemMessage,
    UsageMetadata,
)
from openjiuwen.core.foundation.llm.schema.tool_call import ToolCall
from openjiuwen.core.foundation.tool.schema import ToolInfo
from openjiuwen.core.runner import Runner
from openjiuwen.core.session.agent import create_agent_session


# Create a concrete subclass of ModelWrapper for testing
class ConcreteModelWrapper(ModelWrapper):
    pass


# Load environment variables from memory_env file
def load_env_vars() -> Dict[str, str]:
    """Load configuration from environment variable file"""
    env_path = os.path.join(os.path.dirname(__file__), "memory_env")
    config = {}

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
    return config


# Load environment variables
env_vars = load_env_vars()

# Set model configuration
client_provider = env_vars.get("LLM_PROVIDER", "SiliconFlow")
api_key = env_vars.get("LLM_API_KEY", "")
api_base = env_vars.get(
    "LLM_API_BASE", "https://api.siliconflow.cn/v1/chat/completions"
)
model_name = env_vars.get("LLM_MODEL_NAME", "Qwen/Qwen3-32B")
TEMPERATURE = 0.7  # default temperature
TOP_P = 0.9  # default top_p
TIMEOUT = 120.0  # default timeout time (seconds)


def add_model(model_id: str):
    """Add model to resource manager"""
    model_client_config = ModelClientConfig(
        client_id=model_id,
        client_provider=client_provider,
        api_key=api_key,
        api_base=api_base,
        timeout=TIMEOUT,
        verify_ssl=False,
        ssl_cert=None,
    )
    model_request_config = ModelRequestConfig(
        model=model_name,
        temperature=TEMPERATURE,
        top_p=TOP_P,
    )

    def model_factory():
        return Model(
            model_client_config=model_client_config,
            model_config=model_request_config,
        )

    Runner.resource_mgr.add_model(model_id=model_id, model=model_factory)


# Test static method: _convert_tool_call
def test_convert_tool_call_dict_openai_format():
    """Test converting OpenAI format dictionary to new format ToolCall"""
    tool_call_dict = {
        "id": "call_123",
        "type": "function",
        "function": {"name": "get_weather", "arguments": '{"city":"Beijing"}'},
    }
    result = ModelWrapper._convert_tool_call(tool_call_dict)
    assert isinstance(result, ToolCall)
    assert result.id == "call_123"
    assert result.type == "function"
    assert result.name == "get_weather"
    assert result.arguments == '{"city":"Beijing"}'


def test_convert_tool_call_dict_flat_format():
    """Test converting flat format dictionary to new format ToolCall"""
    tool_call_dict = {
        "id": "call_456",
        "type": "function",
        "name": "get_time",
        "arguments": '{"timezone":"UTC+8"}',
    }
    result = ModelWrapper._convert_tool_call(tool_call_dict)
    assert isinstance(result, ToolCall)
    assert result.id == "call_456"
    assert result.type == "function"
    assert result.name == "get_time"
    assert result.arguments == '{"timezone":"UTC+8"}'


def test_convert_tool_call_old_tool_call_object():
    """Test converting old format OldToolCall object to new format ToolCall"""
    old_tool_call = OldToolCall(
        id="call_789", name="get_user_info", args={"user_id": 123}
    )
    result = ModelWrapper._convert_tool_call(old_tool_call)
    assert isinstance(result, ToolCall)
    assert result.id == "call_789"
    assert result.type == "function"
    assert result.name == "get_user_info"
    assert result.arguments == '{"user_id": 123}'


# Test static method: _convert_to_old_tool_call
def test_convert_to_old_tool_call():
    """Test converting new format ToolCall to old format OldToolCall"""
    new_tool_call = ToolCall(
        id="call_abc",
        type="function",
        name="get_product",
        arguments='{"product_id": 456}',
    )
    result = ModelWrapper._convert_to_old_tool_call(new_tool_call)
    assert isinstance(result, OldToolCall)
    assert result.id == "call_abc"
    assert result.name == "get_product"
    assert result.args == {"product_id": 456}


def test_convert_to_old_tool_call_invalid_json():
    """Test converting new format ToolCall with invalid JSON arguments"""
    new_tool_call = ToolCall(
        id="call_def",
        type="function",
        name="invalid_json",
        arguments="invalid json string",
    )
    result = ModelWrapper._convert_to_old_tool_call(new_tool_call)
    assert isinstance(result, OldToolCall)
    assert result.id == "call_def"
    assert result.name == "invalid_json"
    assert result.args == {}


# Test static method: _convert_input_to_model_format
def test_convert_input_string():
    """Test converting string input to new format message list"""
    input_str = "Hello, world!"
    result, tools = ModelWrapper._convert_input_to_model_format(input_str)
    assert len(result) == 1
    assert isinstance(result[0], UserMessage)
    assert result[0].content == input_str
    assert len(tools) == 0


def test_convert_input_dict_list():
    """Test converting dictionary list input to new format message list"""
    input_list = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather today?"},
    ]
    result, tools = ModelWrapper._convert_input_to_model_format(input_list)
    assert len(result) == 2
    assert isinstance(result[0], SystemMessage)
    assert isinstance(result[1], UserMessage)
    assert result[0].content == "You are a helpful assistant."
    assert result[1].content == "What is the weather today?"
    assert len(tools) == 0


def test_convert_input_old_message_list():
    """Test converting old format message list to new format message list"""
    input_list = [
        OldSystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="What is the time?"),
    ]
    result, tools = ModelWrapper._convert_input_to_model_format(input_list)
    assert len(result) == 2
    assert isinstance(result[0], SystemMessage)
    assert isinstance(result[1], UserMessage)
    assert result[0].content == "You are a helpful assistant."
    assert result[1].content == "What is the time?"
    assert len(tools) == 0


def test_convert_input_language_model_input():
    """Test converting LanguageModelInput format to new format message list"""
    input_dict = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is your name?"},
        ],
        "tools": [
            Tool(
                name="get_weather",
                description="Get the current weather",
                parameters={
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "The city to get the weather for",
                        }
                    },
                    "required": ["city"],
                },
                principle="Only use the functions you have been provided with.",
                results="The function call results will be provided in the assistant message.",
            )
        ],
    }
    result, tools = ModelWrapper._convert_input_to_model_format(input_dict)
    assert len(result) == 2
    assert isinstance(result[0], SystemMessage)
    assert isinstance(result[1], UserMessage)
    assert result[0].content == "You are a helpful assistant."
    assert result[1].content == "What is your name?"
    assert len(tools) == 1
    assert isinstance(tools[0], ToolInfo)
    assert tools[0].name == "get_weather"
    assert tools[0].description == "Get the current weather"


def test_convert_input_with_tool_calls():
    """Test converting input containing tool calls"""
    input_list = [
        {
            "role": "assistant",
            "content": "Let me check the weather.",
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"city":"Beijing"}',
                    },
                }
            ],
        }
    ]
    result, tools = ModelWrapper._convert_input_to_model_format(input_list)
    assert len(result) == 1
    assert isinstance(result[0], AssistantMessage)
    assert result[0].content == "Let me check the weather."
    assert len(result[0].tool_calls) == 1
    assert isinstance(result[0].tool_calls[0], ToolCall)
    assert result[0].tool_calls[0].id == "call_123"
    assert result[0].tool_calls[0].type == "function"
    assert result[0].tool_calls[0].name == "get_weather"
    assert result[0].tool_calls[0].arguments == '{"city":"Beijing"}'
    assert len(tools) == 0


# Test static method: _post_stream_message
def test_post_stream_message_basic():
    """Test converting basic model response to AIMessage"""
    mock_usage_metadata = UsageMetadata(
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        err_msg="Success",
        request_start_time="2023-01-01T00:00:00Z",
        cache_tokens=5,
    )

    assistant_message = AssistantMessage(
        content="The weather is sunny.",
        usage_metadata=mock_usage_metadata,
        name="assistant",
    )

    result, tool_calls = ModelWrapper._post_stream_message(assistant_message)
    assert isinstance(result, AIMessage)
    assert result.content == "The weather is sunny."
    assert result.name == "assistant"
    assert isinstance(result.usage_metadata, OldUsageMetadata)
    assert result.usage_metadata.input_tokens == 10
    assert result.usage_metadata.output_tokens == 20
    assert result.usage_metadata.total_tokens == 30
    assert result.usage_metadata.errmsg == "Success"
    assert not hasattr(result.usage_metadata, "cache_tokens")  # Should be removed
    assert not tool_calls  # Should be empty


def test_post_stream_message_with_tool_calls():
    """Test converting model response containing tool calls"""
    tool_call = ToolCall(
        id="call_123",
        type="function",
        name="get_weather",
        arguments='{"city":"Beijing"}',
    )

    assistant_message = AssistantMessage(content="", tool_calls=[tool_call])

    result, tool_calls = ModelWrapper._post_stream_message(assistant_message)
    assert isinstance(result, AIMessage)
    assert tool_calls == [tool_call]  # Should be the same ToolCall object


# Test ainvoke method (using mock)
@pytest.mark.asyncio
async def test_ainvoke_with_mock():
    """Test ainvoke method using mock"""
    # Create test input
    input_data = [{"role": "user", "content": "What is the weather today?"}]
    model_id = "test-model-123"

    # Create mock session
    mock_session_id = "test-session-123"
    # Create a single agent session instance
    mock_agent_session = create_agent_session(session_id=mock_session_id)

    # Create mock model response
    mock_usage_metadata = UsageMetadata(
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        err_msg="Success",
        request_start_time="2023-01-01T00:00:00Z",
        cache_tokens=5,
    )

    mock_model_response = AssistantMessage(
        content="The weather is sunny today.", usage_metadata=mock_usage_metadata
    )

    # Create mock model
    mock_model = Mock()
    mock_model.invoke = AsyncMock(return_value=mock_model_response)

    # Patch Runner.resource_mgr.get_model and create_agent_session
    with (
        patch.object(Runner.resource_mgr, "get_model", return_value=mock_model),
        patch(
            "jiuwen.extension.wrapper.model_wrapper.create_agent_session",
            return_value=mock_agent_session,
        ),
    ):
        model_wrapper = ConcreteModelWrapper()
        result = await model_wrapper.ainvoke(
            inputs=input_data,
            model_id=model_id,
            session_id=mock_session_id,
            temperature=0.7,
            max_tokens=100,
        )

        # Verify calls
        Runner.resource_mgr.get_model.assert_called_once_with(
            model_id=model_id, session=mock_agent_session
        )
        mock_model.invoke.assert_called_once()

        # Verify results
        assert isinstance(result, AIMessage)
        assert result.content == "The weather is sunny today."


# Test astream method (using mock)
@pytest.mark.asyncio
async def test_astream_with_mock():
    """Test astream method using mock"""
    # Create test input
    input_data = [{"role": "user", "content": "Tell me a story."}]
    model_id = "test-model-456"

    # Create mock session
    mock_session_id = "test-session-456"

    # Create a single agent session instance
    mock_agent_session = create_agent_session(session_id=mock_session_id)

    # Create mock streaming response chunks
    async def mock_stream_response(*args, **kwargs):
        yield AssistantMessage(content="Once upon a")
        yield AssistantMessage(content=" time in a")
        yield AssistantMessage(content=" faraway land.")

    # Create mock model
    mock_model = Mock()
    mock_model.stream.side_effect = mock_stream_response

    # Patch Runner.resource_mgr.get_model and create_agent_session
    with (
        patch.object(Runner.resource_mgr, "get_model", return_value=mock_model),
        patch(
            "jiuwen.extension.wrapper.model_wrapper.create_agent_session",
            return_value=mock_agent_session,
        ),
    ):
        model_wrapper = ConcreteModelWrapper()
        stream_results = []
        async for chunk in model_wrapper.astream(
            inputs=input_data, model_id=model_id, session_id=mock_session_id
        ):
            stream_results.append(chunk)

        # Verify calls
        Runner.resource_mgr.get_model.assert_called_once_with(
            model_id=model_id, session=mock_agent_session
        )
        mock_model.stream.assert_called_once()

        # Verify results
        assert len(stream_results) == 4
        for result in stream_results:
            assert isinstance(result, AIMessage)
        assert stream_results[0].content == "Once upon a"
        assert stream_results[1].content == " time in a"
        assert stream_results[2].content == " faraway land."
        assert stream_results[3].content == "Once upon a time in a faraway land."


# Test with real model (integration test)
@pytest.mark.skip("Skipping real model test")
@pytest.mark.asyncio
async def test_ainvoke_with_real_model():
    """Test ainvoke method using real model"""
    # Create test input
    input_data = {
        "messages": [
            OldSystemMessage(
                content='## 人设\n我将扮演一个知识问答助手的角色。\n\n## 输出格式\n输出答案时，应遵循以下格式要求：\n- 使用"您好您好"开头\n 今天日期：2026-04-03 14:51:54，星期五。\n'
            ),
            HumanMessage(content="调用calculator_tool输入9+9"),
        ],
        "tools": [
            Tool(
                name="mock_plugin_add",
                description="mock_plugin_add，加上啦啦啦",
                parameters={
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "query"}},
                    "required": ["query"],
                },
                principle="Only use the functions you have been provided with.",
                results="The function call results will be provided in the assistant message.",
            ),
            Tool(
                name="calculator_tool",
                description="calculator_tool",
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "expression"}
                    },
                    "required": ["expression"],
                },
                principle="Only use the functions you have been provided with.",
                results="The function call results will be provided in the assistant message.",
            ),
            Tool(
                name="workflow_react_tools",
                description="react模式多工具调用场景测试无需提供properties以外的参数信息",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "用户输入"}
                    },
                    "required": ["query"],
                },
                principle="Only use the functions you have been provided with.",
                results="The function call results will be provided in the assistant message.",
            ),
        ],
    }

    # Use real model ID
    model_id = "test-real-model"

    # Add model to resource manager
    add_model(model_id)

    # Create real session
    session_id = "test-real-session"

    # Invoke the model
    model_wrapper = ConcreteModelWrapper()
    result = await model_wrapper.ainvoke(
        inputs=input_data, model_id=model_id, session_id=session_id
    )

    # Verify results
    assert isinstance(result, AIMessage)
    assert len(result.content) > 0
    llm_logger.info(f"Real model ainvoke response: {result}")

    # Cleanup: Remove model from resource manager
    if hasattr(Runner.resource_mgr, "remove_model"):
        Runner.resource_mgr.remove_model(model_id=model_id)


@pytest.mark.skip("Skipping real model test")
@pytest.mark.asyncio
async def test_astream_with_real_model():
    """Test astream method using real model"""
    # Create test input
    input_data = {
        "messages": [
            OldSystemMessage(
                content='## 人设\n我将扮演一个知识问答助手的角色。\n\n## 输出格式\n输出答案时，应遵循以下格式要求：\n- 使用"您好您好"开头\n 今天日期：2026-04-03 14:51:54，星期五。\n'
            ),
            HumanMessage(content="调用calculator_tool输入9+9"),
        ],
        "tools": [
            Tool(
                name="mock_plugin_add",
                description="mock_plugin_add，加上啦啦啦",
                parameters={
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "query"}},
                    "required": ["query"],
                },
                principle="Only use the functions you have been provided with.",
                results="The function call results will be provided in the assistant message.",
            ),
            Tool(
                name="calculator_tool",
                description="calculator_tool",
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "expression"}
                    },
                    "required": ["expression"],
                },
                principle="Only use the functions you have been provided with.",
                results="The function call results will be provided in the assistant message.",
            ),
            Tool(
                name="workflow_react_tools",
                description="react模式多工具调用场景测试无需提供properties以外的参数信息",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "用户输入"}
                    },
                    "required": ["query"],
                },
                principle="Only use the functions you have been provided with.",
                results="The function call results will be provided in the assistant message.",
            ),
        ],
    }

    # Use real model ID
    model_id = "test-real-model-stream"

    # Add model to resource manager
    add_model(model_id)

    # Create real session
    session_id = "test-real-session-stream"

    # Invoke the model (streaming)
    model_wrapper = ConcreteModelWrapper()
    stream_results = []
    async for chunk in model_wrapper.astream(
        inputs=input_data, model_id=model_id, session_id=session_id
    ):
        stream_results.append(chunk)

    # Verify results
    assert len(stream_results) > 0
    for result in stream_results:
        assert isinstance(result, AIMessage)
        llm_logger.info(f"Real model astream chunk: {result}")
    # Print full response
    full_content = "".join([result.content for result in stream_results])
    llm_logger.info(f"Real model astream response: {full_content}")

    # Cleanup: Remove model from resource manager
    if hasattr(Runner.resource_mgr, "remove_model"):
        Runner.resource_mgr.remove_model(model_id=model_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
