# openjiuwen.core.utils.llm.base

## class openjiuwen.core.utils.llm.base.BaseChatModel

```python
openjiuwen.core.utils.llm.base.BaseChatModel()
```

`BaseChatModel`类是面向大模型调用的统一抽象基类，提供**同步流式、同步非流式、异步流式、异步非流式**四种调用方式。​**用户可继承该类实现自己的模型适配器**​：需要实现`_invoke/_ainvoke/_stream/_astream`方法，即可接入需要的模型服务。​未实现的调用形态将尝试回退到同语义路径（如同步→异步），若回退路径也未实现将抛出异常。

**参数**：

* ​**api_key**​(str)：访问OpenAI大模型服务接口的API密钥，用于身份验证和权限校验。
* ​**api_base**(str)​：大模型服务接口的URL。
* ​**max_retries**(int, 可选)​：表示接口调用失败时的最大重试次数。默认值：3。
* ​**timeout**(int, 可选)​：表示单次调用大模型请求的超时时间。单位：秒。默认值：60秒。
* ​**kwargs**​：可变参数，用于传递其他模型需要的参数。

​**异常**​：

* ​**requests.exceptions.Timeout**​：请求超时，当连接或读取操作在设定的 `timeout` 内未完成时，抛出该异常。

**样例**：

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
...     """OpenAI 专用聊天模型实现，使用官方 openai 库"""
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
...             raise Exception(f"OpenAI API 调用失败: {str(e)}")
... 
...     async def _ainvoke(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature:float = 0.1,
...                top_p:float = 0.1, **kwargs: Any) -> AIMessage:
...         """异步调用 OpenAI API"""
...         try:
...             params = self._build_request_params(model_name=model_name, temperature=temperature, top_p=top_p,
...                                                 messages=messages, tools=tools, **kwargs)
...             response = await self._async_client.chat.completions.create(**params)
...             await self._async_client.close()
...             return self._parse_openai_response(model_name, response)
...         except Exception as e:
...             raise Exception(f"OpenAI API 异步调用失败: {str(e)}")
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
...             raise Exception(f"OpenAI API 流式调用失败: {str(e)}")
...         finally:
...             stream.close()
... 
...     async def _astream(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature:float = 0.1,
...                top_p:float = 0.1, **kwargs: Any) -> AsyncIterator[
...         AIMessageChunk]:
...         """异步流式调用 OpenAI API"""
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
...             raise Exception(f"OpenAI API 异步流式调用失败: {str(e)}")
... 
...     def _build_request_params(self, model_name:str, temperature: float, top_p:float, messages: List[Dict],
...                               tools: List[Dict] = None, stream: bool = False,
...                               **kwargs) -> Dict:
...         """构建 OpenAI API 请求参数"""
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
...         """解析 OpenAI API 响应"""
...         choice = response.choices[0]
...         message = choice.message
... 
...         # 解析工具调用
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
...         """解析 OpenAI 流式响应块"""
...         if not chunk.choices:
...             return None
... 
...         choice = chunk.choices[0]
...         delta = choice.delta
... 
...         content = getattr(delta, 'content', None) or ""
...         tool_calls = []
... 
...         # 处理工具调用增量
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
...     messages="你好",
...     temperature=0.2,
...     top_p=0.9,
... )
... 
>>> print("content:", resp.content)
你好，有什么可以帮助你的吗？
```

### invoke

```python
invoke(self, model_name: str, messages: Union[List[BaseMessage], List[Dict], str], tools: Union[List[ToolInfo], List[Dict]] = None, temperature: float = 0.1, top_p: float = 0.1, **kwargs: Any) -> AIMessage
```

**同步**非流式推理入口。会自动将 `messages` 与 `tools` 归一化为字典格式后，调用子类实现的 `_invoke`。
若子类未实现 `_invoke`，则**自动降级**为调用异步的 `ainvoke`（内部用 `asyncio.run` 执行）。若 `ainvoke` 对应的 `_ainvoke` 也未实现，`ainvoke` 会回退去调用 `_invoke`；如果 `_invoke` 仍未实现，则直接抛出 `NotImplementedError`。
**参数**：

* **​model_name**​(str)​：要调用的大模型名称。
* ​​**messages**​(List[Dict])：调用大模型的输入消息。每个元素代表一条对话信息，每条消息包含`role`和`content`两个字符串格式字段，其中role的类型为`user`、`assistant`、`system`、`tool`。
* **tools**​(Union[List[[ToolInfo](../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)], List[Dict]], 可选)​：指定模型可调用的工具列表，默认值：`None`，表示没有可选工具。
* ​**temperature**​(float, 可选)：控制模型输出的随机性，取值范围为[0, 1]。值越高输出越多样，值越低输出越确定。默认值：0.1。
* **top_p**​(float, 可选)：控制模型输出的多样性，取值范围为[0, 1]。值越小，越倾向于选择高概率的候选词。默认值：0.1。
* ​**kwargs**​：可变参数，用于传递其他模型需要的参数。

**返回**：

**AIMessage**，表示AI模型返回的消息，是模型根据指定的提示生成的响应。

**异常**：

* ​**NotImplementedError**：`_ainvoke`和`_invoke` 均未实现。

**样例**：

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
...     messages=[{"role":"user","content":"你好"}]
... )
... 
>>> print(msg.content)
你好，什么可以帮助你的吗？
```

### async ainvoke

```python
async ainvoke(self, model_name: str, messages: Union[List[BaseMessage], List[Dict], str], tools: Union[List[ToolInfo], List[Dict]] = None, temperature: float = 0.1, top_p: float = 0.1, **kwargs: Any) -> Awaitable[AIMessage]
```

**异步**非流式推理入口。会先将 `messages` 与 `tools`​**归一化为统一的字典格式**​，再调用子类实现的 `_ainvoke` 完成一次完整推理。
若 `_ainvoke` 未实现，将**回退**调用**子类实现的**同步 `_invoke` 来完成同一语义的请求；若 `_invoke` 也未实现，则直接抛出 `NotImplementedError`。

**参数**：

* **​model_name**​(str)​：要调用的大模型名称。
* ​​**messages**​(List[Dict])：调用大模型的输入消息。每个元素代表一条对话信息，每条消息包含`role`和`content`两个字符串格式字段，其中role的类型为`user`、`assistant`、`system`、`tool`。
* ​​**tools**​(Union[List[[ToolInfo](../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)], List[Dict]], 可选)：指定模型可调用的工具列表。默认值：`None`，表示没有可选工具。
* ​**temperature**(float, 可选)​：控制模型输出的随机性，取值范围为[0, 1]。值越高输出越多样，值越低输出越确定。默认值：0.1。
* ​**top_p**(float, 可选)​：控制模型输出的多样性，取值范围为[0, 1]。值越小，越倾向于选择高概率的候选词。默认值：0.1。
* ​**kwargs**​：可变参数，用于传递其他模型需要的参数。

**返回**：

**AIMessage**，表示AI模型返回的消息，是模型根据指定的提示生成的响应。

**异常**：

* ​**NotImplementedError**：`_ainvoke`和`_invoke` 均未实现。

**样例**：

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
...         messages=[{"role":"user","content":"你好"}]
...     )
...     print(msg.content)
... 
>>> asyncio.run(async_invoke(model))
你好，什么可以帮助你的吗？
```

### stream

```python
stream(self, model_name:str, messages: Union[List[BaseMessage], List[Dict], str], tools: Union[List[ToolInfo], List[Dict]] = None, temperature:float = 0.1, top_p:float = 0.1, **kwargs: Any) -> Iterator[AIMessageChunk]
```

**同步**流式推理入口。会先把 `messages` 与 `tools`​**归一化为统一字典格式**​，再调用子类实现的 `_stream` 逐块产出 `AIMessageChunk`。
若子类未实现 `_stream`，则**自动回退**为消费异步的 `_astream`， 若`_astream`也未实现，则直接抛出`NotImplementedError`。

**参数**：

* **model_name**​(str)：要调用的大模型名称。
* ​​**messages**​(List[Dict])：调用大模型的输入消息。每个元素代表一条对话信息，每条消息包含`role`和`content`两个字符串格式字段，其中role的类型为`user`、`assistant`、`system`、`tool`。
* ​​**tools**(Union[List[[ToolInfo](../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)], List[Dict]], 可选)：指定模型可调用的工具列表。默认值：`None`，表示没有可选工具。
* ​**temperature**​(float, 可选)：控制模型输出的随机性，取值范围为[0, 1]。值越高输出越多样，值越低输出越确定。默认值：0.1。
* ​**top_p​**(float, 可选)：控制模型输出的多样性，取值范围为[0, 1]。值越小，越倾向于选择高概率的候选词。默认值：0.1。
* ​**kwargs**​：可变参数，用于传递其他模型需要的参数。

**返回**：

**Iterator[AIMessageChunk]**，一个迭代器，每次迭代返回的项是一个AIMessageChunk，表示一个AI消息片段，逐步将AI生成的内容以块Chunk为单位输出。

**异常**：

* ​**NotImplementedError​**：`_astream` 和`_stream`均未实现。

**用例**：

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
...     messages=[{"role": "user", "content": "分步推理：1+2+3"}],
... ):
...     if chunk.content:
...         print(chunk.content, end="", flush=True)
思考第1步：1+2=3
思考第2步：3+3=6
结论：6
```

### async  astream

```python
async astream(self, model_name: str, messages: Union[List[BaseMessage], List[Dict], str], tools: Union[List[ToolInfo], List[Dict]] = None, temperature: float = 0.1, top_p: float = 0.1, **kwargs: Any) -> AsyncIterator[AIMessageChunk]
```

**异步**流式推理入口。内部调用 `_astream`。
若 `_astream` 未实现，将**回退**到同步流式 `_stream`， 若`_stream`也未实现，则直接抛出`NotImplementedError`。
**参数**：

* **​model_name​**(str)​：要调用的大模型名称。
* ​​**messages**​(List[Dict])：调用大模型的输入消息。每个元素代表一条对话信息，每条消息包含`role`和`content`两个字符串格式字段，其中role的类型为`user`、`assistant`、`system`、`tool`。
* ​​**tools**(Union[List[[ToolInfo](../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)], List[Dict]], 可选)​：指定模型可调用的工具列表。默认值：`None`，表示没有可选工具。
* ​**temperature**​(float, 可选)：控制模型输出的随机性，取值范围为[0, 1]。值越高输出越多样，值越低输出越确定。默认值：0.1。
* ​**top_p**​(float, 可选)：控制模型输出的多样性，取值范围为[0, 1]。值越小，越倾向于选择高概率的候选词。默认值：0.1。
* ​**kwargs**​：可变参数，用于传递其他模型需要的参数。

**返回**：

**AsyncIterator[AIMessageChunk]**，一个异步迭代器，每次迭代返回的项是一个AIMessageChunk，表示一个AI消息片段，逐步将AI生成的内容以块Chunk为单位输出。

**异常**：

* ​**NotImplementedError**：`_astream` 和`_stream`均未实现。

**样例**：

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
...         [{"role": "user", "content": "分步推理：1+2+3"}],
...     ):
...         if chunk.content:
...             print(chunk.content, end="", flush=True)
... 
>>> asyncio.run(async_stream(model))
思考第1步：1+2=3
思考第2步：3+3=6
结论：6
```

## class openjiuwen.core.utils.llm.base.BaseModelInfo

```python
openjiuwen.core.utils.llm.base.BaseModelInfo()
```

`BaseModelInfo` 用于**标准化一次模型调用所需的配置信息**的数据类定义，统一描述模型调用所需的最小配置，并提供​**字段别名**​、​**前置校验**​、**别名回填**与**严格字段控制**等能力。

​**参数**​：

* ​**api_key**(str)​：访问OpenAI大模型服务接口的API密钥，用于身份验证和权限校验。必填，长度至少为 1。
* ​**api_base**(str)​：大模型服务接口的URL。必填，长度至少为 1。
* ​**model_name**​(str)：要调用的大模型名称，若未显式提供 `model_name`，但输入包含别名字段 `model`，则自动用其值填充 `model_name`。
* ​**temperature**​(float, 可选)：控制模型输出的随机性，取值范围为[0, 1]。值越高输出越多样，值越低输出越确定。默认值：0.1。
* ​**top_p​**(float, 可选)：控制模型输出的多样性，取值范围为[0, 1]。值越小，越倾向于选择高概率的候选词。默认值：0.1。
* **streaming**(bool): 是否启用流式输出。默认值：False。若未显式提供 `streaming`，但输入包含别名字段 `stream`，则自动用其值填充 `streaming`。
* ​**timeout**​(int, 可选)：表示单次调用大模型请求的超时时间。单位：秒。默认值：60秒。

**异常**：

* ​**ValidationError**：输入数据不满足模型字段配置，字段校验失败。

**样例**:

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
