# class openjiuwen.core.utils.llm.model_utils.default_model.RequestChatModel

```python
openjiuwen.core.utils.llm.model_utils.default_model.RequestChatModel(api_key:str, api_base:str, max_retries: int=3, timeout: int=60, **kwargs)
```

A general-purpose HTTP client implementation for the OpenAI Chat Completions protocol that sends user messages to a chat model and retrieves the generated response.

Parameters:

- api_key (str): API key for accessing the OpenAI model service, used for authentication and authorization.
- api_base (str): Base URL of the model service.
- max_retries (int, optional): Maximum number of retries when the API call fails. Default: 3.
- timeout (int, optional): Timeout for a single model request, in seconds. Default: 60 seconds.

## _invoke

```python
_invoke(self, model_name: str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs) -> AIMessage
```

Call the backend chat API synchronously and return one complete response.

**Parameters**:

- **model_name** (str): Name of the model to call.
- **messages** (List[Dict]): Input messages to the model. Each item represents a chat entry with two string fields: role and content. role must be one of user, assistant, system, tool.
- **tools** (List[Dict], optional): Tool definitions that the model can call. See [ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo) for the parameter structure. Default: None (no tools).
  - Example tools payload:
    ```python
    tools = [
         {
             "type": "function",
             "function": {
                 "name": "get_weather",
                 "description": "Query weather by city",
                 "parameters": {
                     "type": "object",
                     "properties": {
                         "city":  {"type": "string", "description": "City name"},
                         "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                     },
                     "required": ["city"]
                 }
             }
         }
     ]
    ```
- **temperature** (float, optional): Controls randomness in the output, range [0, 1]. Higher values yield more diverse outputs; lower values yield more deterministic outputs. Default: 0.1.
- **top_p** (float, optional): Controls output diversity via nucleus sampling, range [0, 1]. Smaller values bias towards higher-probability tokens. Default: 0.1.
- **kwargs**: Additional parameters.

**Returns**:
- **AIMessage**: The message returned by the AI model, generated from the provided prompt.

**Exceptions**:

- **requests.exceptions.HTTPError**: HTTP 4xx/5xx. 4xx indicates client errors; 5xx indicates server errors.
- **requests.exceptions.Timeout**: Raised when connect/read operations exceed the configured timeout.
- **requests.exceptions.RequestException**: Network/transport errors, such as DNS issues or network interruptions.
- **json.JSONDecodeError**: Response body is not valid JSON (empty, truncated, or not JSON).

**Example**:

```python
>>> import os
>>> from openjiuwen.core.utils.llm.model_utils.default_model import RequestChatModel
>>> 
>>> os.environ["LLM_SSL_VERIFY"] = "false"
>>> chat = RequestChatModel(api_key="sk-xxx", api_base="your path to model service")
>>> msg = chat._invoke(
...     model_name="your_model",
...     messages=[{"role":"user","content":"Hello"}],
...     temperature=0.2
... )
>>> print(msg.content)
Hello, how can I help you?
```

## async _ainvoke

```python
async _ainvoke(self, model_name: str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs: Any) -> AIMessage
```

Call the backend chat API asynchronously and return one complete response.

**Parameters**:

- **model_name** (str): Name of the model to call.
- **messages** (List[Dict]): Input messages to the model. Each item represents a chat entry with two string fields: role and content. role must be one of user, assistant, system, tool.
- **tools** (List[Dict], optional): Tool definitions that the model can call. See [ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo). Default: None (no tools).
  - Example tools payload:
    ```python
    tools = [
         {
             "type": "function",
             "function": {
                 "name": "get_weather",
                 "description": "Query weather by city",
                 "parameters": {
                     "type": "object",
                     "properties": {
                         "city":  {"type": "string", "description": "City name"},
                         "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                     },
                     "required": ["city"]
                 }
             }
         }
     ]
    ```
- **temperature** (float, optional): Controls randomness, range [0, 1]. Default: 0.1.
- **top_p** (float, optional): Controls diversity, range [0, 1]. Default: 0.1.
- **kwargs**: Additional parameters.

**Returns**:
- **AIMessage**: The message returned by the AI model, generated from the provided prompt.

**Exceptions**:

- aiohttp.ClientResponseError: HTTP 4xx/5xx.
- asyncio.TimeoutError: Request timed out (connect or read exceeded timeout).
- aiohttp.ClientConnectorError: Connection establishment failed.
- aiohttp.ClientOSError: Underlying socket I/O error.
- aiohttp.ServerDisconnectedError: Server disconnected prematurely during transfer.
- aiohttp.ContentTypeError: Response headers indicate a non-JSON content type.
- json.JSONDecodeError: Response body is not valid JSON.

**Example**:

```python
>>> import os
>>> import asyncio
>>> from openjiuwen.core.utils.llm.model_utils.default_model import RequestChatModel
>>> 
>>> os.environ["LLM_SSL_VERIFY"] = "false"
>>> chat = RequestChatModel(api_key="sk-xxx", api_base="your path to model service")
>>> 
>>> async def async_invoke(model):
...     msg = await model._ainvoke(
...         model_name="your_model",
...         messages=[{"role":"user","content":"Hello"}],
...         top_p=0.9
...     )
...     print(msg.content)
... 
>>> asyncio.run(async_invoke(chat))
Hello, how can I help you?
```

## _stream

```python
_stream(self, model_name: str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs: Any) -> Iterator[AIMessageChunk]
```

Send an inference request in synchronous streaming mode. Each line returned by the server is parsed immediately into an AIMessageChunk, without waiting for the entire result.

**Parameters**:

- **model_name** (str): Name of the model to call.
- **messages** (List[Dict]): Input messages to the model. Each item includes role and content as strings. role must be one of user, assistant, system, tool.
- **tools** (List[Dict], optional): Tool definitions that the model can call. See [ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo). Default: None (no tools).
  - Example tools payload:
    ```python
    tools = [
         {
             "type": "function",
             "function": {
                 "name": "get_weather",
                 "description": "Query weather by city",
                 "parameters": {
                     "type": "object",
                     "properties": {
                         "city":  {"type": "string", "description": "City name"},
                         "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                     },
                     "required": ["city"]
                 }
             }
         }
     ]
    ```
- **temperature** (float, optional): Controls randomness, range [0, 1]. Default: 0.1.
- **top_p** (float, optional): Controls diversity, range [0, 1]. Default: 0.1.
- **kwargs**: Additional parameters.

**Returns**:
- **Iterator[AIMessageChunk]**: An iterator that yields AIMessageChunk items, incrementally outputting the generated content in chunks.

**Exceptions**:

- **requests.exceptions.HTTPError**: HTTP 4xx/5xx.
- **requests.exceptions.Timeout**: Request timed out (connect or read exceeded timeout).
- **requests.exceptions.RequestException**: Network/transport errors.
- **json.JSONDecodeError**: Response body is not valid JSON.

**Example**:

```python
>>> import os
>>> from openjiuwen.core.utils.llm.model_utils.default_model import RequestChatModel
>>> 
>>> os.environ["LLM_SSL_VERIFY"] = "false"
>>> chat = RequestChatModel(
...     api_key="sk-xxx",
...     api_base="your path to model service"
... )
... 
>>> for chunk in chat._stream(
...     model_name="your_model",
...     messages=[{"role": "user", "content": "Step-by-step: 1+2+3"}],
... ):
...     if chunk.content:
...         print(chunk.content, end="", flush=True)
... 
Step 1: 1+2=3
Step 2: 3+3=6
Conclusion: 6
```

## async _astream

```python
async _astream(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs: Any) -> AsyncIterator[AIMessageChunk]
```

Send an inference request in asynchronous streaming mode. Each line returned by the server is parsed into an AIMessageChunk and yielded as it arrives.

Parameters:

- **model_name** (str): Name of the model to call.
- **messages** (List[Dict]): Input messages to the model. Each item includes role and content as strings. role must be one of user, assistant, system, tool.
- **tools** (List[Dict], optional): Tool definitions that the model can call. See [ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo). Default: None (no tools).
  - Example tools payload:
    ```python
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Query weather by city",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city":  {"type": "string", "description": "City name"},
                        "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                    },
                    "required": ["city"]
                }
            }
        }
    ]
    ```
- **temperature** (float, optional): Controls randomness, range [0, 1]. Default: 0.1.
- **top_p** (float, optional): Controls diversity, range [0, 1]. Default: 0.1.
- **kwargs**: Additional parameters.

**Returns**:
- **AsyncIterator[AIMessageChunk]**: An async iterator that yields AIMessageChunk items, incrementally outputting the generated content in chunks.

**Exceptions**:

- **aiohttp.ClientResponseError**: HTTP 4xx/5xx.
- **asyncio.TimeoutError**: Request timed out (connect or read exceeded timeout).
- **aiohttp.ClientConnectorError**: Connection establishment failed.
- **aiohttp.ClientOSError**: Underlying socket I/O error.
- **aiohttp.ServerDisconnectedError**: Server disconnected prematurely during transfer.
- **aiohttp.ContentTypeError**: Response headers indicate a non-JSON content type.
- **json.JSONDecodeError**: Response body is not valid JSON.

**Example**:

```python
>>> import os
>>> import asyncio
>>> from openjiuwen.core.utils.llm.model_utils.default_model import RequestChatModel
>>> 
>>> os.environ["LLM_SSL_VERIFY"] = "false"
>>> chat = RequestChatModel(
...     api_key="sk-xxx",
...     api_base="your path to model service"
... )
... 
>>> async def demo():
...     async for chunk in chat._astream(
...         model_name="your_model",
...         messages=[{"role": "user", "content": "Step-by-step: 1+2+3"}],
...         temperature=0.1,
...         top_p=0.1,
...     ):
...         if chunk.content:
...             print(chunk.content, end="", flush=True)
... 
>>> asyncio.run(demo())
Step 1: 1+2=3
Step 2: 3+3=6
Conclusion: 6
```

# class openjiuwen.core.utils.llm.model_utils.default_model.OpenAIChatModel

```python
openjiuwen.core.utils.llm.model_utils.default_model.OpenAIChatModel(api_key:str, api_base:str, max_retries: int=3, timeout: int=60, **kwargs)
```

An implementation compatible with the OpenAI standard for invoking large language models.

**Parameters**:

- **api_key** (str): API key for accessing the OpenAI model service, used for authentication and authorization.
- **api_base** (str): Base URL of the model service.
- **max_retries** (int, optional): Maximum number of retries upon failure. Default: 3.
- **timeout** (int, optional): Timeout for a single model request, in seconds. Default: 60 seconds.
- **kwargs**: Additional configuration parameters.

## _invoke

```python
_invoke(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs: Any) -> AIMessage
```

Synchronously call the OpenAI Chat Completions API and return a single complete response.

**Parameters**:

- **model_name** (str): Name of the model to call.
- **messages** (List[Dict]): Input messages to the model. Each item includes role and content as strings. role must be one of user, assistant, system, tool.
- **tools** (List[Dict], optional): Tool definitions that the model can call. See [ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo). Default: None (no tools).
  - Example tools payload:
    ```python
    tools = [
         {
             "type": "function",
             "function": {
                 "name": "get_weather",
                 "description": "Query weather by city",
                 "parameters": {
                     "type": "object",
                     "properties": {
                         "city":  {"type": "string", "description": "City name"},
                         "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                     },
                     "required": ["city"]
                 }
             }
         }
     ]
    ```
- **temperature** (float, optional): Controls randomness, range [0, 1]. Default: 0.1.
- **top_p** (float, optional): Controls diversity, range [0, 1]. Default: 0.1.
- **kwargs**: Additional parameters.

**Returns**:
- **AIMessage**: The message returned by the AI model, generated from the provided prompt.

**Example**:

```python
>>> import os
>>> from openjiuwen.core.utils.llm.model_utils.default_model import OpenAIChatModel
>>> from openjiuwen.core.utils.llm.messages import AIMessage, HumanMessage
>>> 
>>> os.environ["LLM_SSL_VERIFY"] = "false"
>>> 
>>> # 1. Create an OpenAIChatModel instance
>>> chat_model = OpenAIChatModel(
...     api_key="your_api_key_here",  # Replace with your actual API key
...     api_base="your path to model service",  # Base URL of the OpenAI model service
...     max_retries=3,
...     timeout=60
... )
... 
>>> # 2. Prepare input messages
>>> messages = [
...     HumanMessage(content="Hello, who are you?")
... ]
... 
>>> # 3. Call invoke
>>> response: AIMessage = chat_model.invoke(
...     model_name="your_model",
...     messages=messages,
...     temperature=0.7,
...     top_p=0.9
... )
... 
>>> print(response.content)
I am an AI assistant, and I can help answer your questions.
```

## async _ainvoke

```python
async _ainvoke(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs: Any) -> AIMessage
```

Asynchronously call the OpenAI Chat Completions API and return a single complete response.

Parameters:

- **model_name** (str): Name of the model to call.
- **messages** (List[Dict]): Input messages to the model. Each item includes role and content as strings. role must be one of user, assistant, system, tool.
- **tools** (List[Dict], optional): Tool definitions that the model can call. See [ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo). Default: None (no tools).
  - Example tools payload:
    ```python
    tools = [
         {
             "type": "function",
             "function": {
                 "name": "get_weather",
                 "description": "Query weather by city",
                 "parameters": {
                     "type": "object",
                     "properties": {
                         "city":  {"type": "string", "description": "City name"},
                         "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                     },
                     "required": ["city"]
                 }
             }
         }
     ]
    ```
- **temperature** (float, optional): Controls randomness, range [0, 1]. Default: 0.1.
- **top_p** (float, optional): Controls diversity, range [0, 1]. Default: 0.1.
- **kwargs**: Additional parameters.

**Returns**:
- **AIMessage**: The message returned by the AI model, generated from the provided prompt.

Example:

```python
>>> import os
>>> import asyncio
>>> from openjiuwen.core.utils.llm.model_utils.default_model import OpenAIChatModel
>>> from openjiuwen.core.utils.llm.messages import AIMessage, HumanMessage
>>> 
>>> os.environ["LLM_SSL_VERIFY"] = "false"
>>> 
>>> # 1. Create an OpenAIChatModel instance
>>> chat_model = OpenAIChatModel(
...     api_key="your_api_key_here",  # Replace with your actual API key
...     api_base="your path to model service",  # Base URL of the OpenAI model service
...     max_retries=3,
...     timeout=60
... )
... 
>>> # 2. Prepare input messages
>>> messages = [
...     HumanMessage(content="Hello, who are you?")
... ]
... 
>>> # 3. Call ainvoke
>>> async def async_invoke(model):
...     response: AIMessage = await model.ainvoke(
...         model_name="your_model",
...         messages=messages,
...         temperature=0.7,
...         top_p=0.9
...     )
...     print(response.content)
... 
>>> asyncio.run(async_invoke(chat_model))
I am an AI assistant, and I can help answer your questions.
```

## _stream

```python
_stream(self, model_name: str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs: Any) -> Iterator[AIMessageChunk]
```

Call the OpenAI Chat Completions API in synchronous streaming mode and return an incremental iterator of AIMessageChunk.

Parameters:

- **model_name** (str): Name of the model to call.
- **messages** (List[Dict]): Input messages to the model. Each item includes role and content as strings. role must be one of user, assistant, system, tool.
- **tools** (List[Dict], optional): Tool definitions that the model can call. See [ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo). Default: None (no tools).
  - Example tools payload:
    ```python
    tools = [
         {
             "type": "function",
             "function": {
                 "name": "get_weather",
                 "description": "Query weather by city",
                 "parameters": {
                     "type": "object",
                     "properties": {
                         "city":  {"type": "string", "description": "City name"},
                         "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                     },
                     "required": ["city"]
                 }
             }
         }
     ]
    ```
- **temperature** (float, optional): Controls randomness, range [0, 1]. Default: 0.1.
- **top_p** (float, optional): Controls diversity, range [0, 1]. Default: 0.1.
- **kwargs**: Additional parameters.

**Returns**:
- **Iterator[AIMessageChunk]**: An iterator that yields AIMessageChunk items, incrementally outputting the generated content in chunks.

**Example**:

```python
>>> import os
>>> from openjiuwen.core.utils.llm.model_utils.default_model import OpenAIChatModel
>>> from openjiuwen.core.utils.llm.messages import HumanMessage
>>> 
>>> os.environ["LLM_SSL_VERIFY"] = "false"
>>> 
>>> # 1. Create an OpenAIChatModel instance
>>> chat_model = OpenAIChatModel(
...     api_key="your_api_key_here",  # Replace with your actual API key
...     api_base="your path to model service",  # Base URL of the OpenAI model service
...     max_retries=3,
...     timeout=60
... )
... 
>>> # 2. Prepare input messages
>>> messages = [
...     HumanMessage(content="Please reason step by step: 1+2+3")
... ]
... 
>>> # 3. Call the stream method (synchronous streaming)
>>> for chunk in chat_model.stream(
...     model_name="your_model",
...     messages=messages,
...     temperature=0.7,
...     top_p=0.9
... ):
...      if chunk.content:
...         print(chunk.content, end="", flush=True)
... 
Step 1: 1+2=3
Step 2: 3+3=6
Conclusion: 6
```

## async _astream

```python
async _astream(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs: Any) -> AsyncIterator[AIMessageChunk]
```

Call the OpenAI Chat Completions API in asynchronous streaming mode and return an async incremental iterator of AIMessageChunk.

Parameters:

- **model_name** (str): Name of the model to call.
- **messages** (List[Dict]): Input messages to the model. Each item includes role and content as strings. role must be one of user, assistant, system, tool.
- **tools** (List[Dict], optional): Tool definitions that the model can call. See [ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo). Default: None (no tools).
  - Example tools payload:
    ```python
    tools = [
         {
             "type": "function",
             "function": {
                 "name": "get_weather",
                 "description": "Query weather by city",
                 "parameters": {
                     "type": "object",
                     "properties": {
                         "city":  {"type": "string", "description": "City name"},
                         "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                     },
                     "required": ["city"]
                 }
             }
         }
     ]
    ```
- **temperature** (float, optional): Controls randomness, range [0, 1]. Default: 0.1.
- **top_p** (float, optional): Controls diversity, range [0, 1]. Default: 0.1.
- **kwargs**: Additional parameters.

**Returns**:
- **AsyncIterator[AIMessageChunk]**: An async iterator that yields AIMessageChunk items, incrementally outputting the generated content in chunks.

**Example**:

```python
>>> import os
>>> import asyncio
>>> from openjiuwen.core.utils.llm.model_utils.default_model import OpenAIChatModel
>>> from openjiuwen.core.utils.llm.messages import HumanMessage
... 
>>> os.environ["LLM_SSL_VERIFY"] = "false"
... 
>>> # 1. Create an OpenAIChatModel instance
>>> chat_model = OpenAIChatModel(
    api_key="your_api_key_here",  # Replace with your actual API key
    api_base="your path to model service",  # Base URL of the OpenAI model service
    max_retries=3,
    timeout=60
>>> )
... 
>>> # 2. Prepare input messages
>>> messages = [
...     HumanMessage(content="Please reason step by step: 1+2+3")
... ]
... 
>>> # 3. Call the astream method (asynchronous streaming)
>>> async def async_stream(model):
...     async for chunk in model.astream(
...         model_name="your_model",
...         messages=messages,
...         temperature=0.7,
...         top_p=0.9
...     ):
...         if chunk.content:
...             print(chunk.content, end="", flush=True)
... 
>>> asyncio.run(async_stream(chat_model))
Step 1: 1+2=3
Step 2: 3+3=6
Conclusion: 6
```