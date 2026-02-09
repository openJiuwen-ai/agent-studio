# class openjiuwen.core.utils.llm.model_utils.default_model.RequestChatModel

```python
openjiuwen.core.utils.llm.model_utils.default_model.RequestChatModel(api_key:str, api_base:str, max_retries: int=3, timeout: int=60, **kwargs)
```

面向 OpenAI Chat Completions协议的​通用 HTTP 客户端实现​，能够向聊天模型发送用户输入的消息并获取模型生成的响应。

**参数**：

* ​**​api_key​**(str)​：访问OpenAI大模型服务接口的API密钥，用于身份验证和权限校验。
* ​**​api_base​**(str)​​：大模型服务接口的URL。
* ​**​max_retries​**(int, 可选)​​：表示接口调用失败时的最大重试次数。默认值：3。
* ​**​timeout​**(int, 可选)​​：表示单次调用大模型请求的超时时间。单位：秒。默认值：60秒。

## _invoke

```python
_invoke(self, model_name: str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs) -> AIMessage
```

以同步方式调用后端聊天接口，返回完整的一次回答。

**参数**：

* **​model_name​**(str)：要调用的大模型名称。
* ​​**messages**​(List[Dict])：调用大模型的输入消息。每个元素代表一条对话信息，每条消息包含`role`和`content`两个字符串格式字段，其中role的类型为`user`、`assistant`、`system`、`tool`。
* ​​**tools**​(List[Dict], 可选)​：指定模型可调用的工具列表，参数构造可参考[ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)。默认值：`None`，表示没有可选工具。
  
  * tools构造样例：
  
  ```python
  tools = [
       {
           "type": "function",
           "function": {
               "name": "get_weather",              
               "description": "按城市查询天气",       
               "parameters": {                       
                   "type": "object",
                   "properties": {
                       "city":  {"type": "string", "description": "城市名"},
                       "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                   },
                   "required": ["city"]
               }
           }
       }
   ]
  ```

* ​**​temperature​**(float, 可选)​​：控制模型输出的随机性，取值范围为[0, 1]。值越高输出越多样，值越低输出越确定。默认值：0.1。
* ​​**top_p​**​(float, 可选)：控制模型输出的多样性，取值范围为[0, 1]。值越小，越倾向于选择高概率的候选词。默认值：0.1。
* ​**kwargs**​：可变参数，用于传递其他参数。

**返回**：
​**AIMessage**​，表示AI模型返回的消息，是模型根据指定的提示生成的响应。

**异常**：

* ​**requests.exceptions.HTTPError**​：HTTP状态码为4xx/5xx，4xx 表示客户端请求错误，5xx表示服务器端故障或无法完成请求。
* **​requests.exceptions.Timeout**​：当连接或读取操作在设定的 `timeout` 内未完成时，抛出该异常。
* **​requests.exceptions.RequestException​**：网络/传输类错误，通常在域名错误、网络中断等问题时抛出。
* **​json.JSONDecodeError**：响应体非合法 JSON，响应为空、截断或非 JSON 格式时抛出。

**样例**：

```python
>>> import os
>>> from openjiuwen.core.utils.llm.model_utils.default_model import RequestChatModel
>>> 
>>> os.environ["LLM_SSL_VERIFY"] = "false"
>>> chat = RequestChatModel(api_key="sk-xxx", api_base="your path to model service")
>>> msg = chat._invoke(
...     model_name="your_model",
...     messages=[{"role":"user","content":"你好"}],
...     temperature=0.2
... )
>>> print(msg.content)
你好，有什么可以帮助你的吗？
```

## async _ainvoke

```python
async _ainvoke(self, model_name: str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs: Any) -> AIMessage
```

以**异步**方式调用后端聊天接口，返回一次完整回答。

**参数**：

* **​model_name​**(str)​​：要调用的大模型名称。
* ​​**messages**​(List[Dict])：调用大模型的输入消息。每个元素代表一条对话信息，每条消息包含`role`和`content`两个字符串格式字段，其中role的类型为`user`、`assistant`、`system`、`tool`。
* ​​**tools**​(List[Dict], 可选)​：指定模型可调用的工具列表，参数构造可参考[ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)。默认值：`None`，表示没有可选工具。
  
  * tools构造样例：
  
  ```python
  tools = [
       {
           "type": "function",
           "function": {
               "name": "get_weather",              
               "description": "按城市查询天气",       
               "parameters": {                       
                   "type": "object",
                   "properties": {
                       "city":  {"type": "string", "description": "城市名"},
                       "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                   },
                   "required": ["city"]
               }
           }
       }
   ]
  ```

* ​**​temperature​**(float, 可选)​：控制模型输出的随机性，取值范围为[0, 1]。值越高输出越多样，值越低输出越确定。默认值：0.1。
* ​​**top_p​**​(float, 可选)：控制模型输出的多样性，取值范围为[0, 1]。值越小，越倾向于选择高概率的候选词。默认值：0.1。
* ​**kwargs**​：可变参数，用于传递其他参数。

**返回**：
​**AIMessage**​，表示AI模型返回的消息，是模型根据指定的提示生成的响应。

​**异常**​：

* ​**aiohttp.ClientResponseError**​：HTTP状态码为4xx/5xx，4xx 表示客户端请求错误，5xx表示服务器端故障或无法完成请求。
* **​asyncio.TimeoutError​**：请求超时，连接或读取在设定的 `timeout` 内未完成即抛出。
* **​aiohttp.ClientConnectorError​**：网络连接类错误，连接建立失败时抛出。
* **​aiohttp.ClientOSError​**：网络连接类错误，底层套接字 I/O 异常时抛出。
* **aiohttp.ServerDisconnectedError​**：网络连接类错误，服务器在传输过程中提前断开时抛出。
* ​**aiohttp.ContentTypeError**：响应头非JSON格式时抛出。
* **json.JSONDecodeError**：响应体非合法JSON，响应为空、截断或非JSON 格式时抛出。

**样例**：

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
...         messages=[{"role":"user","content":"你好"}],
...         top_p=0.9
...     )
...     print(msg.content)
... 
>>> asyncio.run(async_invoke(chat))
你好，有什么可以帮助你的吗？
```

## _stream

```python
_stream(self, model_name: str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs: Any) -> Iterator[AIMessageChunk]
```

以**同步流式**方式向后端发起推理请求，接口返回的每一行都会被即时解析成一个 `AIMessageChunk`，无需等待整段结果完成。

**参数**：

* **​model_name​**​(str)：要调用的大模型名称。
* ​​**messages**​(List[Dict])：调用大模型的输入消息。每个元素代表一条对话信息，每条消息包含`role`和`content`两个字符串格式字段，其中role的类型为`user`、`assistant`、`system`、`tool`。
* ​​**tools**​(List[Dict], 可选)​：指定模型可调用的工具列表，参数构造可参考[ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)。默认值：`None`，表示没有可选工具。
  
  * tools构造样例：
  
  ```python
  tools = [
       {
           "type": "function",
           "function": {
               "name": "get_weather",              
               "description": "按城市查询天气",       
               "parameters": {                       
                   "type": "object",
                   "properties": {
                       "city":  {"type": "string", "description": "城市名"},
                       "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                   },
                   "required": ["city"]
               }
           }
       }
   ]
  ```

* ​**​temperature​**​(float, 可选)​：控制模型输出的随机性，取值范围为[0, 1]。值越高输出越多样，值越低输出越确定。默认值：0.1。
* ​​**top_p​**​​(float, 可选)：控制模型输出的多样性，取值范围为[0, 1]。值越小，越倾向于选择高概率的候选词。默认值：0.1。
* ​**kwargs**​：可变参数，用于传递其他参数。

**返回**：
​**Iterator[AIMessageChunk]**​，一个迭代器，每次迭代返回的项是一个AIMessageChunk，表示一个AI 消息片段，逐步将AI生成的内容以块Chunk为单位输出。

**异常**：

* **​requests.exceptions.HTTPError**：HTTP状态码为4xx/5xx，4xx 表示客户端请求错误，5xx表示服务器端故障或无法完成请求。
* **​requests.exceptions.Timeout**​：请求超时，连接或读取在设定的 `timeout` 内未完成即抛出。
* ​**requests.exceptions.RequestException**​：网络/传输类错误，通常在域名错误、网络中断等问题时抛出。
* **json.JSONDecodeError**：响应体非合法JSON，响应为空、截断或非JSON 格式时抛出。

**样例**：

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
...     messages=[{"role": "user", "content": "分步推理：1+2+3"}],
... ):
...     if chunk.content:
...         print(chunk.content, end="", flush=True)
... 
思考第1步：1+2=3
思考第2步：3+3=6
结论：6
```

## async _astream

```python
async _astream(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs: Any) -> AsyncIterator[AIMessageChunk]
```

以**异步流式**方式发起推理请求，服务端返回的每一行会被即时解析为 `AIMessageChunk` 并**按到达顺序异步产出**。

**参数**：

* **​model_name**(str)​​：要调用的大模型名称。
* ​​**messages**​(List[Dict])：调用大模型的输入消息。每个元素代表一条对话信息，每条消息包含`role`和`content`两个字符串格式字段，其中role的类型为`user`、`assistant`、`system`、`tool`。
* **tools**​(List[Dict], 可选)​：指定模型可调用的工具列表，参数构造可参考[ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)。默认值：`None`，表示没有可选工具。
  * tools构造样例：

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",              
            "description": "按城市查询天气",       
            "parameters": {                       
                "type": "object",
                "properties": {
                    "city":  {"type": "string", "description": "城市名"},
                    "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                },
                "required": ["city"]
            }
        }
    }
]
```

* ​**​temperature**(float, 可选)​​：控制模型输出的随机性，取值范围为[0, 1]。值越高输出越多样，值越低输出越确定。默认值：0.1。
* ​​**top_p**​(float, 可选)​：控制模型输出的多样性，取值范围为[0, 1]。值越小，越倾向于选择高概率的候选词。默认值：0.1。
* ​**kwargs**​：可变参数，用于传递其他参数。

**返回**
​**AsyncIterator[AIMessageChunk]**​，一个异步迭代器，每次迭代返回的项是一个AIMessageChunk，表示一个AI 消息片段，逐步将AI生成的内容以块Chunk为单位输出。

**异常**：

* ​**aiohttp.ClientResponseError​**：HTTP状态码为4xx/5xx，4xx 表示客户端请求错误，5xx表示服务器端故障或无法完成请求。
* **​asyncio.TimeoutError​**：请求超时，连接或读取在设定的 `timeout` 内未完成即抛出。
* **​aiohttp.ClientConnectorError​**：网络连接类错误，连接建立失败时抛出。
* **​aiohttp.ClientOSError​**：网络连接类错误，底层套接字 I/O 异常时抛出。
* **aiohttp.ServerDisconnectedError​**：网络连接类错误，服务器在传输过程中提前断开时抛出。
* ​**aiohttp.ContentTypeError**：响应头非JSON格式时抛出。
* **json.JSONDecodeError**：响应体非合法JSON，响应为空、截断或非JSON 格式时抛出。

**样例**：

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
...         messages=[{"role": "user", "content": "分步推理：1+2+3"}],
...         temperature=0.1,
...         top_p=0.1,
...     ):
...         if chunk.content:
...             print(chunk.content, end="", flush=True)
... 
>>> asyncio.run(demo())
思考第1步：1+2=3
思考第2步：3+3=6
结论：6
```

# class openjiuwen.core.utils.llm.model_utils.default_model.OpenAIChatModel

```python
openjiuwen.core.utils.llm.model_utils.default_model.OpenAIChatModel(api_key:str, api_base:str, max_retries: int=3, timeout: int=60, **kwargs)
```

兼容OpenAI定义标准的调用大模型的实现。

**参数**：

* ​**api_key**(str)​：访问OpenAI大模型服务接口的API密钥，用于身份验证和权限校验。
* ​**api_base**(str)​：大模型服务接口的URL。
* ​**max_retries**(int, 可选)​：表示接口调用失败时的最大重试次数。默认值：3。
* ​**timeout**(int, 可选)​：表示单次调用大模型请求的超时时间。单位：秒。默认值：60秒。
* ​**kwargs**​：可变参数，用于传递其他额外的配置参数。

## _invoke

```python
_invoke(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs: Any) -> AIMessage
```

以**同步**方式调用 OpenAI Chat Completions 接口，返回一次**完整**回答。

**参数**：

* ​**model_name**(str)​：要调用的大模型名称。
* ​**messages**(List[Dict])：调用大模型的输入消息。每个元素代表一条对话信息，每条消息包含`role`和`content`两个字符串格式字段，其中role的类型为`user`、`assistant`、`system`、`tool`。
* ​​**tools**​(List[Dict], 可选)​：指定模型可调用的工具列表，参数构造可参考[ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)。默认值：`None`，表示没有可选工具。
  
  * tools构造样例：
  
  ```python
  tools = [
       {
           "type": "function",
           "function": {
               "name": "get_weather",              
               "description": "按城市查询天气",       
               "parameters": {                       
                   "type": "object",
                   "properties": {
                       "city":  {"type": "string", "description": "城市名"},
                       "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                   },
                   "required": ["city"]
               }
           }
       }
   ]
  ```

* ​**temperature**(float, 可选)​：控制模型输出的随机性，取值范围为[0, 1]。值越高输出越多样，值越低输出越确定。默认值：0.1。
* ​​**top_p​**(float, 可选)：控制模型输出的多样性，取值范围为[0, 1]。值越小，越倾向于选择高概率的候选词。默认值：0.1。
* ​**kwargs**​：可变参数，用于传递其他参数。

**返回：**
**AIMessage**，表示AI模型返回的消息，是模型根据指定的提示生成的响应。

**样例：**

```python
>>> import os
>>> from openjiuwen.core.utils.llm.model_utils.default_model import OpenAIChatModel
>>> from openjiuwen.core.utils.llm.messages import AIMessage, HumanMessage
>>> 
>>> os.environ["LLM_SSL_VERIFY"] = "false"
>>> 
>>> # 1. 创建OpenAIChatModel对象
>>> chat_model = OpenAIChatModel(
...     api_key="your_api_key_here",  # 替换为实际的API密钥
...     api_base="your path to model service",  # OpenAI大模型服务的API地址
...     max_retries=3,
...     timeout=60
... )
... 
>>> # 2. 准备输入消息
>>> messages = [
...     HumanMessage(content="你好，请问你是谁？")
... ]
... 
>>> # 3. 调用invoke方法
>>> response: AIMessage = chat_model.invoke(
...     model_name="your_model",
...     messages=messages,
...     temperature=0.7,
...     top_p=0.9
... )
... 
>>> print(response.content)
我是一个AI助手，我可以帮助你解答问题。
```

## async _ainvoke

```python
async _ainvoke(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs: Any) -> AIMessage
```

以**异步**方式调用 OpenAI Chat Completions 接口，返回一次**完整**回答。

**参数**：

* ​**model_name**(str)​：要调用的大模型名称。
* ​**messages**(List[Dict])：调用大模型的输入消息。每个元素代表一条对话信息，每条消息包含`role`和`content`两个字符串格式字段，其中role的类型为`user`、`assistant`、`system`、`tool`。
* ​​**tools**​(List[Dict], 可选)​：指定模型可调用的工具列表，参数构造可参考[ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)。默认值：`None`，表示没有可选工具。
  
  * tools构造样例：
  
  ```python
  tools = [
       {
           "type": "function",
           "function": {
               "name": "get_weather",              
               "description": "按城市查询天气",       
               "parameters": {                       
                   "type": "object",
                   "properties": {
                       "city":  {"type": "string", "description": "城市名"},
                       "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                   },
                   "required": ["city"]
               }
           }
       }
   ]
  ```

* ​**temperature**(float, 可选)​：控制模型输出的随机性，取值范围为[0, 1]。值越高输出越多样，值越低输出越确定。默认值：0.1。
* ​​**top_p**​(float, 可选)：控制模型输出的多样性，取值范围为[0, 1]。值越小，越倾向于选择高概率的候选词。默认值：0.1。
* ​**kwargs**​：可变参数，用于传递其他参数。

**返回**：
**AIMessage**，表示AI模型返回的消息，是模型根据指定的提示生成的响应。

**样例**：

```python
>>> import os
>>> import asyncio
>>> from openjiuwen.core.utils.llm.model_utils.default_model import OpenAIChatModel
>>> from openjiuwen.core.utils.llm.messages import AIMessage, HumanMessage
>>> 
>>> os.environ["LLM_SSL_VERIFY"] = "false"
>>> 
>>> # 1. 创建OpenAIChatModel对象
>>> chat_model = OpenAIChatModel(
...     api_key="your_api_key_here",  # 替换为实际的API密钥
...     api_base="your path to model service",  # OpenAI大模型服务的API地址
...     max_retries=3,
...     timeout=60
... )
... 
>>> # 2. 准备输入消息
>>> messages = [
...     HumanMessage(content="你好，请问你是谁？")
... ]
... 
>>> # 3. 调用ainvoke方法
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
我是一个AI助手，我可以帮助你解答问题。
```

## _stream

```python
_stream(self, model_name: str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs: Any) -> Iterator[AIMessageChunk]
```

以**同步流式**方式调用 OpenAI Chat Completions 接口，返回 `AIMessageChunk` 的​**增量迭代器**​。

**参数**：

* ​**model_name**(str)：要调用的大模型名称。
* ​**messages**(List[Dict])：调用大模型的输入消息。每个元素代表一条对话信息，每条消息包含`role`和`content`两个字符串格式字段，其中role的类型为`user`、`assistant`、`system`、`tool`。
* ​​**tools**​(List[Dict], 可选)​：指定模型可调用的工具列表，参数构造可参考[ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)。默认值：`None`，表示没有可选工具。
  
  * tools构造样例：
  
  ```python
  tools = [
       {
           "type": "function",
           "function": {
               "name": "get_weather",              
               "description": "按城市查询天气",       
               "parameters": {                       
                   "type": "object",
                   "properties": {
                       "city":  {"type": "string", "description": "城市名"},
                       "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                   },
                   "required": ["city"]
               }
           }
       }
   ]
  ```

* ​**temperature**(float, 可选)​：控制模型输出的随机性，取值范围为[0, 1]。值越高输出越多样，值越低输出越确定。默认值：0.1。
* ​​**top_p​**(float, 可选)：控制模型输出的多样性，取值范围为[0, 1]。值越小，越倾向于选择高概率的候选词。默认值：0.1。
* ​**kwargs**​：可变参数，用于传递其他参数。

**返回：**
**Iterator[AIMessageChunk]**，一个迭代器，每次迭代返回的项是一个AIMessageChunk，表示一个AI 消息片段，逐步将AI生成的内容以块Chunk为单位输出。

**用例**：

```python
>>> import os
>>> from openjiuwen.core.utils.llm.model_utils.default_model import OpenAIChatModel
>>> from openjiuwen.core.utils.llm.messages import HumanMessage
>>> 
>>> os.environ["LLM_SSL_VERIFY"] = "false"
>>> 
>>> # 1. 创建OpenAIChatModel对象
>>> chat_model = OpenAIChatModel(
...     api_key="your_api_key_here",  # 替换为实际的API密钥
...     api_base="your path to model service",  # OpenAI大模型服务的API地址
...     max_retries=3,
...     timeout=60
... )
... 
>>> # 2. 准备输入消息
>>> messages = [
...     HumanMessage(content="请分步推理：1+2+3")
... ]
... 
>>> # 3. 调用invoke方法# 3. 调用 stream 方法（同步流式）
>>> for chunk in chat_model.stream(
...     model_name="your_model",
...     messages=messages,
...     temperature=0.7,
...     top_p=0.9
... ):
...      if chunk.content:
...         print(chunk.content, end="", flush=True)
... 
思考第1步：1+2=3
思考第2步：3+3=6
结论：6
```

## async _astream

```python
async _astream(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, **kwargs: Any) -> AsyncIterator[AIMessageChunk]
```

**异步流式**方式调用 OpenAI Chat Completions 接口，返回 `AIMessageChunk` 的​**异步增量迭代器**​。

**参数**：

* ​**model_name**(str)：要调用的大模型名称。
* ​**messages**(List[Dict])​：调用大模型的输入消息。每个元素代表一条对话信息，每条消息包含`role`和`content`两个字符串格式字段，其中role的类型为`user`、`assistant`、`system`、`tool`。
* ​​**tools**​(List[Dict], 可选)​：指定模型可调用的工具列表，参数构造可参考[ToolInfo](../../tool/schema.md#class-openjiuwencoreutilstoolschematoolinfo)。默认值：`None`，表示没有可选工具。
  
  * tools构造样例：
  
  ```python
  tools = [
       {
           "type": "function",
           "function": {
               "name": "get_weather",              
               "description": "按城市查询天气",       
               "parameters": {                       
                   "type": "object",
                   "properties": {
                       "city":  {"type": "string", "description": "城市名"},
                       "units": {"type": "string", "enum": ["c", "f"], "default": "c"}
                   },
                   "required": ["city"]
               }
           }
       }
   ]
  ```

* ​**temperature**(float, 可选)：控制模型输出的随机性，取值范围为[0, 1]。值越高输出越多样，值越低输出越确定。默认值：0.1。
* ​​**top_p​**(float, 可选)：控制模型输出的多样性，取值范围为[0, 1]。值越小，越倾向于选择高概率的候选词。默认值：0.1。
* ​**kwargs**​：可变参数，用于传递其他参数。

**返回**：
**AsyncIterator[AIMessageChunk]**，一个异步迭代器，每次迭代返回的项是一个AIMessageChunk，表示一个AI 消息片段，逐步将AI生成的内容以块Chunk为单位输出。

**用例**：

```python
>>> import os
>>> import asyncio
>>> from openjiuwen.core.utils.llm.model_utils.default_model import OpenAIChatModel
>>> from openjiuwen.core.utils.llm.messages import HumanMessage
... 
>>> os.environ["LLM_SSL_VERIFY"] = "false"
... 
>>> # 1. 创建OpenAIChatModel对象
>>> chat_model = OpenAIChatModel(
    api_key="your_api_key_here",  # 替换为实际的API密钥
    api_base="your path to model service",  # OpenAI大模型服务的API地址
    max_retries=3,
    timeout=60
>>> )
... 
>>> # 2. 准备输入消息
>>> messages = [
...     HumanMessage(content="请分步推理：1+2+3")
... ]
... 
>>> # 3. 调用 astream 方法（异步流式）
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
思考第1步：1+2=3
思考第2步：3+3=6
结论：6
```
