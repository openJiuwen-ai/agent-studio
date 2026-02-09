# openjiuwen.core.utils.llm.base

## class openjiuwen.core.utils.llm.base.BaseChatModel

```python
openjiuwen.core.utils.llm.base.BaseChatModel()
```

The BaseChatModel class is a unified abstract base class for calling large language models. It provides four invocation modes: synchronous non-streaming, synchronous streaming, asynchronous non-streaming, and asynchronous streaming. Users can subclass this class to implement their own model adapters by implementing the methods `_invoke/_ainvoke/_stream/_astream` to integrate with the desired model service. Any unimplemented invocation mode will attempt to fall back to the equivalent semantic path (e.g., sync → async). If the fallback path is also unimplemented, an exception is raised.

**Parameters**:

- **api_key** (str): API key for authenticating and authorizing access to the OpenAI model service.
- **api_base** (str): The base URL of the model service API.
- **max_retries** (int, optional): Maximum number of retries when a call fails. Default: 3.
- **timeout** (int, optional): Timeout for a single model request, in seconds. Default: 60 seconds.
- **kwargs**: Additional parameters for other model-specific needs.

**Exceptions**:

- **requests.exceptions.Timeout**: Request timed out. Raised when the connection or read operation does not complete within the configured timeout.

**Example**:

```python
>>> import os
>>> import openai
>>> from typing import List, Dict, Any, Iterator, AsyncIterator, Optional
>>> from openjiuwen.core.utils.llm.base import BaseModelClient
>>> from openjiuwen.core.utils.llm.messages import AIMessage, UsageMetadata
>>> from openjiuwen.core.utils.llm.messages_chunk import AIMessageChunk
>>> from openjiuwen.core.utils.tool.schema import ToolCall
>>>
>>> class OpenAIChatModel(BaseModelClient):
...     """OpenAI-specific chat model implementation using the official openai library"""
... 
...     def __init__(self,
...                  api_key: str, api_base: str, max_retrie: int=3, timeout: int=60, **kwargs):
...         super().__init__(api_key=api_key, api_base=api_base, max_retrie=max_retrie, timeout=timeout)
...         self._init_clients()
... 
...     def _init_clients(self):
...         """init OpenAI client"""
... 
...         self._sync_client = openai.OpenAI(
...             api_key=self.api_key,
...             base_url=self.api_base
...         )
... 
...         self._async_client = openai.AsyncOpenAI(
...             api_key=self.api_key,
...             base_url=self.api_base
...         )
...  
...     def model_provider(self) -> str:
...         return "openai"
... 
...     def _invoke(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature:float = 0.1,
...                top_p:float = 0.1, **kwargs: Any) -> AIMessage:
...         try:
...             params = self._build_request_params(model_name=model_name, temperature=temperature, top_p=top_p,
...                                                 messages=messages, tools=tools, **kwargs)
...             response = self._sync_client.chat.completions.create(**params)
...             self._sync_client.close()
...             return self._parse_openai_response(model_name, response)
...         except Exception as e:
...             raise Exception(f"OpenAI API call failed: {str(e)}")
... 
...     async def _ainvoke(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature:float = 0.1,
...                top_p:float = 0.1, **kwargs: Any) -> AIMessage:
...         """Asynchronous call to the OpenAI API"""
...         try:
...             params = self._build_request_params(model_name=model_name, temperature=temperature, top_p=top_p,
...                                                 messages=messages, tools=tools, **kwargs)
...             response = await self._async_client.chat.completions.create(**params)
...             await self._async_client.close()
...             return self._parse_openai_response(model_name, response)
...         except Exception as e:
...             raise Exception(f"OpenAI API async call failed: {str(e)}")
... 
...     def _stream(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature:float = 0.1,
...                top_p:float = 0.1, **kwargs: Any) -> Iterator[AIMessageChunk]:
...         try:
...             params = self._build_request_params(model_name=model_name, temperature=temperature, top_p=top_p,
...                                                 messages=messages, tools=tools, stream=True, **kwargs)
...             stream = self._sync_client.chat.completions.create(**params)
...             for chunk in stream:
...                 parsed_chunk = self._parse_openai_stream_chunk(model_name, chunk)
...                 if parsed_chunk:
...                     yield parsed_chunk
...         except Exception as e:
...             raise Exception(f"OpenAI API streaming call failed: {str(e)}")
...         finally:
...             stream.close()
... 
...     async def _astream(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature:float = 0.1,
...                top_p:float = 0.1, **kwargs: Any) -> AsyncIterator[
...         AIMessageChunk]:
...         """Asynchronous streaming call to the OpenAI API"""
...         try:
...             params = self._build_request_params(model_name=model_name, temperature=temperature, top_p=top_p,
...                                                 messages=messages, tools=tools, stream=True, **kwargs)
...             stream = await self._async_client.chat.completions.create(**params)
...             self._async_client.close()
...             async for chunk in stream:
...                 parsed_chunk = self._parse_openai_stream_chunk(model_name, chunk)
...                 if parsed_chunk:
...                     yield parsed_chunk
...         except Exception as e:
...             raise Exception(f"OpenAI API async streaming call failed: {str(e)}")
... 
...     def _build_request_params(self, model_name:str, temperature: float, top_p:float, messages: List[Dict],
...                               tools: List[Dict] = None, stream: bool = False,
...                               **kwargs) -> Dict:
...         """Build OpenAI API request parameters"""
...         params = {
...             "model": model_name,
...             "messages": messages,
...             "temperature": temperature,
...             "top_p": top_p,
...             "stream": stream,
...             "timeout": self.timeout,
...             **kwargs
...         }
... 
...         if tools:
...             params["tools"] = tools
...             params["tool_choice"] = "auto"
... 
...         return params
... 
... 
...     def _parse_openai_response(self, model_name, response) -> AIMessage:
...         """Parse OpenAI API response"""
...         choice = response.choices[0]
...         message = choice.message
... 
...         # Parse tool calls
...         tool_calls = []
...         if hasattr(message, 'tool_calls') and message.tool_calls:
...             for tc in message.tool_calls:
...                 tool_call = ToolCall(
...                     id=tc.id,
...                     type="function",
...                     name=tc.function.name,
...                     arguments=tc.function.arguments if tc.function.arguments is not None else "{}"
...                 )
...                 tool_calls.append(tool_call)
... 
...         return AIMessage(
...             content=message.content or "",
...             tool_calls=tool_calls,
...             usage_metadata=UsageMetadata(
...                 model_name=model_name,
...                 finish_reason=choice.finish_reason or "",
...                 total_latency=response.usage.total_tokens if response.usage else 0
...             )
...         )
...  
...     def _parse_openai_stream_chunk(self, model_name, chunk) -> Optional[AIMessageChunk]:
...         """Parse a chunk from OpenAI streaming response"""
...         if not chunk.choices:
...             return None
... 
...         choice = chunk.choices[0]
...         delta = choice.delta
... 
...         content = getattr(delta, 'content', None) or ""
...         tool_calls = []
... 
...         # Handle incremental tool calls
...         if hasattr(delta, 'tool_calls') and delta.tool_calls:
...             for tc_delta in delta.tool_calls:
...                 if hasattr(tc_delta, 'function') and tc_delta.function:
...                     tool_call = ToolCall(
...                         id=getattr(tc_delta, 'id', ''),
...                         type="function",
...                         name=getattr(tc_delta.function, 'name', ''),
...                         arguments=getattr(tc_delta.function, 'arguments', '')
...                     )
...                     tool_calls.append(tool_call)
... 
...         usage_metadata = None
...         if hasattr(chunk, 'usage') and chunk.usage:
...             usage_metadata = UsageMetadata(
...                 model_name=model_name,
...                 finish_reason=choice.finish_reason or "",
...                 total_latency=chunk.usage.total_tokens if chunk.usage else 0
...             )
... 
...         return AIMessageChunk(
...             content=content,
...             tool_calls=tool_calls,
...             usage_metadata=usage_metadata
...         )
... 
>>> chat = OpenAIChatModel(
...     api_key=os.environ["OPENAI_API_KEY"],
...     api_base="your path to model service",
...     timeout=60,
... )
... 
>>> resp = chat.invoke(
...     model_name="your_model",
...     messages="Hello",
...     temperature=0.2,
...     top_p=0.9,
... )
... 
>>> print("content:", resp.content)
Hello, how can I help you?
```

### invoke

```python
invoke(self, model_name: str, messages: Union[List[BaseMessage], List[Dict], str], tools: Union[List[ToolInfo], List[Dict]] = None, temperature: float = 0.1, top_p: float = 0.1, **kwargs: Any) -> AIMessage
```

Synchronous non-streaming inference entry point. Automatically normalizes messages and tools into dictionary format, then calls the subclass-implemented `_invoke`.
If the subclass does not implement `_invoke`, it automatically falls back to calling the asynchronous `ainvoke` (internally executed via `asyncio.run`). If `ainvoke`’s backing `_ainvoke` is also not implemented, `ainvoke` will fall back to calling `_invoke`. If `_invoke` is still unimplemented, a `NotImplementedError` is raised.

**Parameters**:

- **model_name** (str): The name of the model to call.
- **messages** (List[Dict]): Input messages for the model. Each item represents a message with fields role and content (both strings). Valid roles: user, assistant, system, tool.
- **tools** (Union[List[ToolInfo], List[Dict]], optional): The list of tools available to the model. Default: None (no tools).
- **temperature** (float, optional): Controls output randomness, in [0, 1]. Higher for more diversity, lower for more deterministic output. Default: 0.1.
- **top_p** (float, optional): Controls output diversity via nucleus sampling, in [0, 1]. Lower biases toward higher-probability tokens. Default: 0.1.
- **kwargs**: Additional model-specific parameters.

**Returns**:

- **AIMessage**: The model’s response message generated from the specified prompt.

**Exceptions**:

- **NotImplementedError**: Both `_ainvoke` and `_invoke` are unimplemented.

**Example**:

```python
>>> import os
>>> 
>>> model = OpenAIChatModel(
...     api_key=os.environ["OPENAI_API_KEY"],
...     api_base="your path to model service",
...     timeout=60,
... )
...
>>> msg = model.invoke(
...     model_name="your_model",
...     messages=[{"role":"user","content":"Hello"}]
... )
... 
>>> print(msg.content)
Hello, how can I help you?
```

### async ainvoke

```python
async ainvoke(self, model_name: str, messages: Union[List[BaseMessage], List[Dict], str], tools: Union[List[ToolInfo], List[Dict]] = None, temperature: float = 0.1, top_p: float = 0.1, **kwargs: Any) -> Awaitable[AIMessage]
```

Asynchronous non-streaming inference entry point. It first normalizes messages and tools into a unified dictionary format, then calls the subclass-implemented `_ainvoke` to complete the request.
If `_ainvoke` is not implemented, it falls back to invoking the synchronous `_invoke` to fulfill the same semantic request. If `_invoke` is also unimplemented, a `NotImplementedError` is raised.

**Parameters**:

- **model_name** (str): The name of the model to call.
- **messages** (List[Dict]): Input messages for the model. Each item represents a message with fields role and content (both strings). Valid roles: user, assistant, system, tool.
- **tools** (Union[List[ToolInfo], List[Dict]], optional): The list of tools available to the model. Default: None (no tools).
- **temperature** (float, optional): Controls output randomness, in [0, 1]. Default: 0.1.
- **top_p** (float, optional): Controls output diversity via nucleus sampling, in [0, 1]. Default: 0.1.
- **kwargs**: Additional model-specific parameters.

**Returns**:

- **AIMessage**: The model’s response message generated from the specified prompt.

**Exceptions**:

- **NotImplementedError**: Both `_ainvoke` and `_invoke` are unimplemented.

Example:

```python
>>> import os
>>> import asyncio
>>> 
>>> model = OpenAIChatModel(
...     api_key=os.environ["OPENAI_API_KEY"],
...     api_base="your path to model service",
...     timeout=60,
... )
...
>>> async def async_invoke(model):
...     msg = await model.ainvoke(
...         model_name="your_model",
...         messages=[{"role":"user","content":"Hello"}]
...     )
...     print(msg.content)
... 
>>> asyncio.run(async_invoke(model))
Hello, how can I help you?
```

### stream

```python
stream(self, model_name:str, messages: Union[List[BaseMessage], List[Dict], str], tools: Union[List[ToolInfo], List[Dict]] = None, temperature:float = 0.1, top_p:float = 0.1, **kwargs: Any) -> Iterator[AIMessageChunk]
```

Synchronous streaming inference entry point. It first normalizes messages and tools into a unified dictionary format, then calls the subclass-implemented `_stream` to yield AIMessageChunk iteratively.
If the subclass does not implement `_stream`, it automatically falls back to consuming the asynchronous `_astream`. If `_astream` is also unimplemented, a `NotImplementedError` is raised.

Parameters:

- **model_name** (str): The name of the model to call.
- **messages** (List[Dict]): Input messages for the model. Each item represents a message with fields role and content (both strings). Valid roles: user, assistant, system, tool.
- **tools** (Union[List[ToolInfo], List[Dict]], optional): The list of tools available to the model. Default: None (no tools).
- **temperature** (float, optional): Controls output randomness, in [0, 1]. Default: 0.1.
- **top_p** (float, optional): Controls output diversity, in [0, 1]. Default: 0.1.
- **kwargs**: Additional model-specific parameters.

**Returns**:

- **Iterator[AIMessageChunk]**: An iterator that yields AIMessageChunk items, each representing a partial model output.

**Exceptions**:

- **NotImplementedError**: Both `_astream` and `_stream` are unimplemented.

**Usage**:

```python
>>> import os
>>> 
>>> model = OpenAIChatModel(
...     api_key=os.environ["OPENAI_API_KEY"],
...     api_base="your path to model service",
...     timeout=60,
... )
...
>>> for chunk in model.stream(
...     model_name="your_model",
...     messages=[{"role": "user", "content": "Step-by-step reasoning: 1+2+3"}],
... ):
...     if chunk.content:
...         print(chunk.content, end="", flush=True)
Step 1: 1+2=3
Step 2: 3+3=6
Conclusion: 6
```

### async astream

```python
async astream(self, model_name: str, messages: Union[List[BaseMessage], List[Dict], str], tools: Union[List[ToolInfo], List[Dict]] = None, temperature: float = 0.1, top_p: float = 0.1, **kwargs: Any) -> AsyncIterator[AIMessageChunk]
```

Asynchronous streaming inference entry point. Internally calls `_astream`.
If `_astream` is not implemented, it falls back to the synchronous streaming `_stream`. If `_stream` is also unimplemented, a `NotImplementedError` is raised.

Parameters:

- **model_name** (str): The name of the model to call.
- **messages** (List[Dict]): Input messages for the model. Each item represents a message with fields role and content (both strings). Valid roles: user, assistant, system, tool.
- **tools** (Union[List[ToolInfo], List[Dict]], optional): The list of tools available to the model. Default: None (no tools).
- **temperature** (float, optional): Controls output randomness, in [0, 1]. Default: 0.1.
- **top_p** (float, optional): Controls output diversity, in [0, 1]. Default: 0.1.
- **kwargs**: Additional model-specific parameters.

**Returns**:

- **AsyncIterator[AIMessageChunk]**: An async iterator that yields AIMessageChunk items, each representing a partial model output.

**Exceptions**:

- **NotImplementedError**: Both `_astream` and `_stream` are unimplemented.

**Example**:

```python
>>> import os
>>> import asyncio
>>> 
>>> model = OpenAIChatModel(
...     api_key=os.environ["OPENAI_API_KEY"],
...     api_base="your path to model service",
...     timeout=60,
... )
... 
>>> async def async_stream(model):
...     async for chunk in model.astream(
...         "your_model",
...         [{"role": "user", "content": "Step-by-step reasoning: 1+2+3"}],
...     ):
...         if chunk.content:
...             print(chunk.content, end="", flush=True)
... 
>>> asyncio.run(async_stream(model))
Step 1: 1+2=3
Step 2: 3+3=6
Conclusion: 6
```

## class openjiuwen.core.utils.llm.base.BaseModelInfo

```python
openjiuwen.core.utils.llm.base.BaseModelInfo()
```

BaseModelInfo is a data class used to standardize the configuration required for a single model invocation. It unifies the minimal set of configuration fields needed to call a model and provides capabilities such as field aliases, pre-validation, alias backfilling, and strict field control.

**Parameters**:

- **api_key** (str): API key for authenticating and authorizing access to the OpenAI model service. Required, minimum length 1.
- **api_base** (str): The base URL of the model service API. Required, minimum length 1.
- **model_name** (str): The name of the model to call. If model_name is not explicitly provided but the input includes the alias field model, its value will be used to populate model_name.
- **temperature** (float, optional): Controls output randomness, in [0, 1]. Default: 0.1.
- **top_p** (float, optional): Controls output diversity via nucleus sampling, in [0, 1]. Default: 0.1.
- **streaming** (bool): Whether to enable streaming output. Default: False. If streaming is not explicitly provided but the input includes the alias field stream, its value will be used to populate streaming.
- **timeout** (int, optional): Timeout for a single model request, in seconds. Default: 60 seconds.

**Exceptions**:

- **ValidationError**: The input data fails model field validation or does not meet the field configuration.

**Example**:

```python
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> 
>>> info = BaseModelInfo(
...     api_key="sk-xxx",
...     api_base="your path to model service",
...     model="qwen-max",
...     stream=False,
... )
... 
>>> print(info.model_name, info.streaming)
qwen-max False
```