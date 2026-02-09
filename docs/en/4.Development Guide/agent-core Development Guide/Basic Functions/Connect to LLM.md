Different models have their own strengths in reasoning ability, conversational fluency, and multi-turn interaction. Users can flexibly choose the most suitable model based on specific application scenarios—for example, selecting a model with stronger reasoning for complex logical tasks, or a model with more natural interaction for a smoother conversational experience.
openJiuwen provides the following three model integration methods:

- Vendor-series model integration: Fully supports SiliconFlow vendor models and models that follow the OpenAI interface. Users can flexibly choose models suited to their business scenarios based on model characteristics (e.g., reasoning ability, conversational fluency). A unified calling interface for large models is provided via `ModelFactory`.
- OpenAI-format model integration: Provides a wrapped interface `OpenAIChatModel` so that users can initialize and use it in the same way as the `OpenAI` interface. The model service must be wrapped and implemented in standard `OpenAI` format.
- Custom model integration: By implementing the extension interfaces provided by `ModelFactory`, users can seamlessly integrate their own or third-party models to enhance system flexibility and adaptability. Custom model integration will be introduced in the Advanced Usage section.

# Using the ModelFactory to Call Models

## Initialize the Model

Use the ModelFactory().get_model() method to obtain a model instance. Users only need to specify the following required parameters in the configuration:

- Model provider identifier `model_provider` (currently supports two providers: siliconflow and OpenAI);
- Model request URL `api_base`;
- Model authentication token `api_key`.

Additionally, you can optionally set the maximum number of retries on failure `max_retries` and the per-call timeout `timeout`.

Example of obtaining a model instance using siliconflow:

```python
from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory

model = ModelFactory().get_model(
    model_provider="siliconflow",
    api_base="your path to the model service",
    api_key="sk-****************************",
    max_retries=3,
    timeout=60
)
```

> **Note**
> Users need to register accounts on SiliconFlow or OpenAI websites to obtain an available model `api_key` and the model invocation URL `api_base` from the model marketplace.

## Prepare Model Input

The large model supports the following three main input parameters. If only `messages` is configured, the model will generate a reply directly based on the context; if both `messages` and `tools` are configured, the model will decide whether to call a tool by combining context and tool definitions to fulfill the user’s request.

- ​**model_name**​: Identifies the model name for the current request to specify the exact model to call. This is a required parameter.
- ​**messages**​: A list of messages arranged in conversational order. Each message includes the sender’s role (`role`) and the message content (`content`). This is a required parameter. Inputs support two common formats (List[BaseMessage], List[Dict]):

1. When the message type is List[BaseMessage], sample code:

```python
from openjiuwen.core.utils.llm.messages import SystemMessage, HumanMessage

messages = [
    SystemMessage(content='You are an AI assistant'),
    HumanMessage(content='Hello')
]
```

2. When the message type is List[Dict], sample code:

```python
messages = [
    {"role": "system", "content": "You are an AI assistant"},
    {"role": "user", "content": "Hello"}
]
```

- ​**tools**​: A list of tools available to the model, each defined using JSON Schema to describe required parameters, parameter types, and whether they are mandatory. This is optional and only used when a tool call is needed. Example:

```python
# Tool definition
tools = [{
     "type": "function",
     "function": {
         "name": "get_weather",
         "description": "Get current weather for a location",
         "parameters": {
             "type": "object",
             "properties": {
                 "location": {
                     "type": "string",
                     "description": "City and country e.g. Paris, France"
                 },
                 "units": {
                     "type": "string",
                     "enum": ["metric", "imperial"],
                     "description": "Temperature unit"
                 }
             },
             "required": ["location"]
         }
     }
 }]
```

messages is a multi-turn dialog context array built for LLM APIs, following the fixed role order `system → user → assistant → tool`. It carries system instructions, user input, model replies, and tool results, providing a complete, structured semantic context for each inference:

- `system`: Represents system or developer instructions used to set the model’s behavior, background knowledge, or global rules. The corresponding BaseMessage is `SystemMessage`.
- `user`: Represents the end user’s input, i.e., questions, commands, or conversation content. The corresponding BaseMessage is `HumanMessage`.
- `assistant`: Represents the LLM’s response generated from the user input and context. The corresponding BaseMessage is `AIMessage`.
- `tool`: Represents the results returned by external tools or functions, typically used in Function Calling scenarios. The corresponding BaseMessage is `ToolMessage`.

Additionally, you can optionally specify:

- temperature: A generative model hyperparameter that controls randomness and creativity in text generation. It adjusts the probability distribution in the model’s softmax output layer. Lower values yield more deterministic output; higher values increase randomness and creativity.
- top_p: A sampling strategy parameter used during decoding to dynamically truncate the probability distribution, thereby controlling randomness and diversity. Smaller values produce more focused results; larger values increase randomness and diversity.

## Call the Model

Model invocation supports four types: synchronous non-streaming `invoke`, asynchronous non-streaming `ainvoke`, synchronous streaming `stream`, and asynchronous streaming `astream`:

- Synchronous non-streaming `invoke`: Suitable for scenarios not sensitive to latency, where you need the complete result at once and the invocation chain is already synchronous and blocking.
- Asynchronous non-streaming `ainvoke`: Suitable when you need the complete result before further processing and real-time requirements are low.
- Synchronous streaming `stream`: Suitable for real-time, continuous one-way data pushing, where the entire processing pipeline must run in the same thread in order, with low latency.
- Asynchronous streaming `astream`: Suitable for high-concurrency real-time pushing with non-blocking output, or for generating and displaying results incrementally.

Using synchronous non-streaming invoke and asynchronous streaming astream as examples, we illustrate how to call the model and show the results. For other methods, see the API docs `openjiuwen.core.utils.llm`.

### Synchronous Non-Streaming `invoke`

Use `model.invoke` to obtain the model’s response in a single batch. Define a system prompt and user input to ask a weather-related question; a tool call is expected. Example:

```python
import os
from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
from openjiuwen.core.utils.llm.messages import SystemMessage, HumanMessage

os.environ["LLM_SSL_VERIFY"] = "false"

def invoke():
    # Get the ModelFactory instance
    factory = ModelFactory()

    # Get the model
    model = factory.get_model(
        model_provider="siliconflow",
        api_base="your path to the model service",
        api_key="sk-****************************"
    )

    # Prepare input: define a system prompt and user input, ask a weather-related question; expect a tool call
    messages = [
        SystemMessage(content="You are an AI assistant").model_dump(exclude_none=True),
        HumanMessage(content="Hangzhou weather").model_dump(exclude_none=True)
    ]
    # Weather tool schema definition
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City and country e.g. Paris, France"
                    },
                    "units": {
                        "type": "string",
                        "enum": ["metric", "imperial"],
                        "description": "Temperature unit"
                    }
                },
                "required": ["location"]
            }
        }
    }]

    # Call the model
    response = model.invoke(model_name="your_model", messages=messages, tools=tools, temperature=0.7, top_p=0.95)
    print(response)


if __name__ == "__main__":
    invoke()
```

Output:

```python
role='assistant' content='' name=None tool_calls=[ToolCall(id='019afe192ceee268d980f8acd98ccbc1', type='function', name='get_weather', arguments='{"location": "Hangzhou, China"}')] usage_metadata=UsageMetadata(code=0, errmsg='', prompt='', task_id='', model_name='Qwen/Qwen3-32B', finish_reason='tool_calls', total_latency=224.0, model_stats={}, first_token_time='', request_start_time='') raw_content=None reason_content=None
```

### Asynchronous Streaming `astream`

Use `model.astream` for streaming output of the model’s responses via asynchronous execution without blocking the current thread. Example:

```python
import os
import asyncio
from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
from openjiuwen.core.utils.llm.messages import SystemMessage, HumanMessage

os.environ["LLM_SSL_VERIFY"] = "false"

async def astream():
    try:
        # Get the ModelFactory instance
        factory = ModelFactory()

        # Get the model
        model = factory.get_model(
            model_provider="siliconflow",
            api_base="your path to the model service",
            api_key="sk-****************************"
        )

        # Prepare input: define a system prompt and user input; ask a question unrelated to weather; expect no tool call
        messages = [
            SystemMessage(content="You are an AI assistant").model_dump(exclude_none=True),
            HumanMessage(content="Hello").model_dump(exclude_none=True)
        ]

        # Weather tool schema definition
        tools = [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City and country e.g. Paris, France"
                        },
                        "units": {
                            "type": "string",
                            "enum": ["metric", "imperial"],
                            "description": "Temperature unit"
                        }
                    },
                    "required": ["location"]
                }
            }
        }]

        # Iterate over the async iterator using async for
        async for chunk in model.astream(model_name="your_model", messages=messages, tools=tools, temperature=0.7, top_p=0.95):
            print(chunk)

    except Exception as e:
        print(f"Error in async test: {str(e)}")
        raise
    finally:
        if model:
            await model.close()


# Define an async main function
async def main():
    # Call the async function and await completion
    await astream()


if __name__ == "__main__":
    asyncio.run(main())
```

Output:

```python
role='assistant' content='Hello' name=None tool_calls=[] usage_metadata=UsageMetadata(code=0, errmsg='', prompt='', task_id='', model_name='', finish_reason='', total_latency=0.0, model_stats={}, first_token_time='', request_start_time='') raw_content=None reason_content=''
role='assistant' content='!' name=None tool_calls=[] usage_metadata=UsageMetadata(code=0, errmsg='', prompt='', task_id='', model_name='', finish_reason='', total_latency=0.0, model_stats={}, first_token_time='', request_start_time='') raw_content=None reason_content=''
role='assistant' content='Is there anything' name=None tool_calls=[] usage_metadata=UsageMetadata(code=0, errmsg='', prompt='', task_id='', model_name='', finish_reason='', total_latency=0.0, model_stats={}, first_token_time='', request_start_time='') raw_content=None reason_content=''
role='assistant' content='I can' name=None tool_calls=[] usage_metadata=UsageMetadata(code=0, errmsg='', prompt='', task_id='', model_name='', finish_reason='', total_latency=0.0, model_stats={}, first_token_time='', request_start_time='') raw_content=None reason_content=''
role='assistant' content='help' name=None tool_calls=[] usage_metadata=UsageMetadata(code=0, errmsg='', prompt='', task_id='', model_name='', finish_reason='', total_latency=0.0, model_stats={}, first_token_time='', request_start_time='') raw_content=None reason_content=''
role='assistant' content='you' name=None tool_calls=[] usage_metadata=UsageMetadata(code=0, errmsg='', prompt='', task_id='', model_name='', finish_reason='', total_latency=0.0, model_stats={}, first_token_time='', request_start_time='') raw_content=None reason_content=''
role='assistant' content='with' name=None tool_calls=[] usage_metadata=UsageMetadata(code=0, errmsg='', prompt='', task_id='', model_name='', finish_reason='', total_latency=0.0, model_stats={}, first_token_time='', request_start_time='') raw_content=None reason_content=''
role='assistant' content='?' name=None tool_calls=[] usage_metadata=UsageMetadata(code=0, errmsg='', prompt='', task_id='', model_name='', finish_reason='', total_latency=0.0, model_stats={}, first_token_time='', request_start_time='') raw_content=None reason_content=''
role='assistant' content='' name=None tool_calls=[] usage_metadata=UsageMetadata(code=0, errmsg='', prompt='', task_id='', model_name='', finish_reason='stop', total_latency=0.0, model_stats={}, first_token_time='', request_start_time='') raw_content=None reason_content=''
```

# Integrate Models with OpenAIChatModel

## Initialize the Model

When integrating a model using OpenAIChatModel, configure the following parameters:
- Required parameters: Configure the two parameters below to successfully create a model instance.
  - **`api_key`**: Authentication token for identity verification.
  - **`api_base`**: URL endpoint for model requests.

- Optional parameters: Configure as needed during initialization.
  - **`max_retries`**: Maximum number of retries upon failure to improve robustness.
  - **`timeout`**: Timeout for a single model request to avoid long waits.

```python
from openjiuwen.core.utils.llm.model_utils.default_model import OpenAIChatModel

chat_model = OpenAIChatModel(
    api_key="your_api_key_here",  # Replace with your actual API key
    api_base="**********",  # API endpoint
    max_retries=3,
    timeout=60
)
```

> **Note**
> Users need to register with a model service provider compatible with the OpenAI format to obtain the api_key and the model invocation URL api_base.

## Prepare Model Input

For preparing model inputs, see this chapter’s section [Using the ModelFactory to Call Models - Prepare Model Input](#prepare-model-input).

## Call the Model

For calling the model, see this chapter’s section [Using the ModelFactory to Call Models - Call the Model](#call-the-model). The configured `model_name` should be a model name supported by the `api_base` service address.