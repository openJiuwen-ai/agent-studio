# openjiuwen.core.operator.llm_call.base

## class openjiuwen.core.operator.llm_call.base.LLMCall

```python
openjiuwen.core.operator.llm_call.base.LLMCall(model_name, llm, system_prompt, user_prompt, freeze_system_prompt, freeze_user_prompt)
```

模型调用算子类，作为可优化的参数，其功能是将模型调用与提示词绑定，结合调优工具链，LLMCall对象可以动态优化提示词，使得在特定任务上有更好的表现。

**参数**：

- **model_name**(str)：大模型的名称，用于指定具体模型。
- **llm**([BaseChatModel](../../utils/llm/base.md))：大语言模型实例。
- **system_prompt**(Union[str, List[[BaseMessage](../../utils/llm/messages.md)], List[Dict]])：系统提示词列表，用于定义模型角色与行为规范。支持str类型、[SystemMessage](../../utils/llm/messages.md#class-openjiuwencoreutilsllmmessagessystemmessage)类型或符合SystemMessage格式的字典类型。
- **user_prompt** (Union[str, List[[BaseMessage](../../utils/llm/messages.md)], List[Dict]])：用户输入提示词。支持str类型、[HumanMessage](../../utils/llm/messages.md#class-openjiuwencoreutilsllmmessageshumanmessage)类型或符合HumanMessage格式的字典类型。
- **freeze_system_prompt**(bool, 可选)：是否冻结系统提示词模板，冻结的提示词不会被优化。`True`表示冻结系统提示词，`False`表示不冻结系统提示词。默认值：`False`。
- **freeze_user_prompt**(bool, 可选)：是否冻结用户提示词模板，冻结的提示词不会被优化。`True`表示冻结用户提示词，`False`表示不冻结用户提示词。默认值：`True`。

**样例：**

```python
>>> import os
>>> from openjiuwen.core.operator.llm_call.base import LLMCall
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> 
>>> # 1、创建访问的大模型
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
... 
>>> # 2、创建提示词
>>> system_prompt = "你是一个信息抽取助手."
>>> user_prompt = "请从给定句子中提取所有的人名名称输出格式为[人名1, 人名2, ...]的列表形式，不要输出其他内容，以下是用户输入：{{context}}"
>>> 
>>> # 3、创建提示词优化层
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
```

### async invoke

```python
async invoke(inputs: Dict[str, Any], runtime: Runtime, history: Optional[List[BaseMessage]], tools: Optional[List[ToolInfo]]) -> AIMessage
```

异步调用模型算子生成回答。

**参数**：

- **inputs**(Dict[str, Any])：输入上下文变量，用于填充提示词模板中的占位符。
- **runtime**([Runtime](../../runtime/runtime.md))：运行时上下文。
- **history**(Optional[List[BaseMessage]]，可选)：历史对话消息列表，为`None`表示没有对话历史。默认值：`None`。
- **tools**(Optional[List[ToolInfo]]，可选)：可用工具列表，在插件调用场景使用，为`None`表示非插件调用。默认值：`None`。

**返回值**：
**AIMessage**，完整响应消息，包含模型输出内容。

**样例**：

```python
>>> import os
>>> import asyncio
>>> from openjiuwen.core.operator.llm_call.base import LLMCall
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> from openjiuwen.core.runtime.agent import AgentRuntime
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> 
>>> # 1、创建访问的大模型
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2、创建提示词
>>> system_prompt = "你是一个问答助手, 请简短回答用户的问题"
>>> user_prompt = "以下是用户输入：{{query}}"
>>> 
>>> # 3、创建提示词优化层
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>> 
>>> # 4、调用模型
>>> response = asyncio.run(
...     llm_call.invoke(
...         inputs={"query": "世界上最深的湖是什么"},
...         runtime=AgentRuntime(session_id="id")
...     )
... )
>>> 
>>> print(response.content)
世界上最深的湖是位于俄罗斯境内的贝加尔湖。
```

### async stream

```python
async stream(inputs: Dict[str, Any], runtime: Runtime, history: Optional[List[BaseMessage]], tools: Optional[List[ToolInfo]]) -> Iterator[AIMessageChunk]
```

异步调用模型算子生成流式回答。

**参数**：

- **inputs**(Dict[str, Any])：输入上下文变量，用于填充提示词模板中的占位符。
- **runtime**([Runtime](../../runtime/runtime.md))：运行时上下文。
- **history**(Optional[List[BaseMessage]]，可选)：历史对话消息列表，为`None`表示没有对话历史。默认值：`None`。
- **tools**(Optional[List[ToolInfo]]，可选)：可用工具列表，在插件调用场景使用，为`None`表示非插件调用。默认值：`None`。

**返回值**：
​**Iterator[AIMessageChunk]​**​，异步流式迭代器，每次迭代返回的项是一个`AIMessageChunk`，表示一个消息片段，逐步将AI生成的内容以Chunk为单位输出。

**样例**：

```python
>>> import os
>>> import asyncio
>>> from openjiuwen.core.operator.llm_call.base import LLMCall
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> from openjiuwen.core.runtime.agent import AgentRuntime
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> 
>>> # 1、创建访问的大模型
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2、创建提示词
>>> system_prompt = "你是一个问答助手，请简短回答用户的问题"
>>> user_prompt = "以下是用户输入：{{query}}"
>>> 
>>> # 3、创建提示词优化层
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>> 
>>> # 4、调用模型
>>> async def main():
...     async for chunk in llm_call.stream(
...         inputs={"query": "世界上最深的湖是什么"},
...         runtime=AgentRuntime(session_id="id")
...     ):
...         print(chunk.content, end="", flush=True)
... 
>>> asyncio.run(main())
世界上最深的湖是位于俄罗斯境内的贝加尔湖。
```

### get_system_prompt

```python
get_system_prompt() -> Template
```

获取当前系统提示词的模板对象。

**返回值**：

**[Template](../../utils/prompt/template.md)**，包含系统提示词信息的`Template`实例。

**样例**：

```python
>>> import os
>>> from openjiuwen.core.operator.llm_call.base import LLMCall
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> 
>>> # 1、创建访问的大模型
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2、创建提示词
>>> system_prompt = "你是一个信息抽取助手."
>>> user_prompt = "请从给定句子中提取所有的人名名称输出格式为[人名1, 人名2, ...]的列表形式，不要输出其他内容，以下是用户输入：{{context}}"
>>> 
>>> # 3、创建提示词优化层
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>> 
>>> # 4、获取当前系统提示词模
>>> print(llm_call.get_system_prompt().content)
你是一个信息抽取助手.
```

### get_user_prompt

```python
get_user_prompt() -> Template
```

获取当前用户提示词的模板。

**返回值**：

**[Template](../../utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate)**，包含用户提示词信息的`Template`实例。

**样例：**

```python
>>> import os
>>> from openjiuwen.core.operator.llm_call.base import LLMCall
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> 
>>> # 1、创建访问的大模型
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2、创建提示词
>>> system_prompt = "你是一个信息抽取助手."
>>> user_prompt = "请从给定句子中提取所有的人名名称输出格式为[人名1, 人名2, ...]的列表形式，不要输出其他内容，以下是用户输入：{{context}}"
>>> 
>>> # 3、创建提示词优化层
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>> 
>>> # 4、获取当前用户提示词模板对象
>>> print(llm_call.get_user_prompt().content)
请从给定句子中提取所有的人名名称输出格式为[人名1, 人名2, ...]的列表形式，不要输出其他内容，以下是用户输入：{{context}}
```

### update_system_prompt

```python
update_system_prompt(system_prompt: Union[str, List[BaseMessage], List[Dict]])
```

更新系统提示词内容。

**参数**：

* **system_prompt**(Union[str, List[BaseMessage], List[Dict]])：更新后的系统提示词。

**样例：**

```python
>>> import os
>>> from openjiuwen.core.operator.llm_call.base import LLMCall
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> 
>>> # 1、创建访问的大模型
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> # 2、创建提示词
>>> system_prompt = "你是一个信息抽取助手"
>>> user_prompt = "请从给定句子中提取所有的人名名称输出格式为[人名1, 人名2, ...]的列表形式，不要输出其他内容，以下是用户输入：{{context}}"
>>> 
>>> # 3、创建提示词优化层
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=False, freeze_user_prompt=False)
>>> 
>>> # 4、动态更新系统提示词内容。
>>> llm_call.update_system_prompt("你是一个智能管家助手")
>>> 
>>> # 5、获取当前系统提示词模
>>> print(llm_call.get_system_prompt().content)
你是一个智能管家助手
```

### update_user_prompt

```python
update_user_prompt(user_prompt: Union[str, List[BaseMessage], List[Dict]])
```

更新用户提示词内容。

**参数**：

* **user_prompt**(Union[str, List[BaseMessage], List[Dict]])：更新后的用户提示词。

**样例：**

```python
>>> import os
>>> from openjiuwen.core.operator.llm_call.base import LLMCall
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> 
>>> # 1、创建访问的大模型
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2、创建提示词
>>> system_prompt = "你是一个信息抽取助手."
>>> user_prompt = "请从给定句子中提取所有的人名名称输出格式为[人名1, 人名2, ...]的列表形式，不要输出其他内容，以下是用户输入：{{context}}"
>>> 
>>> # 3、创建提示词优化层
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>> 
>>> # 4、动态更新用户提示词内容。
>>> llm_call.update_user_prompt("请从给定句子中提取所有的人名，以下是用户输入：{{context}}")
>>> 
>>> # 5、获取当前用户提示词模板对象
>>> print(llm_call.get_user_prompt().content)
请从给定句子中提取所有的人名，以下是用户输入：{{context}}
```

### set_freeze_system_prompt

```python
set_freeze_system_prompt(switch: bool)
```

设置系统提示词模板的冻结状态。

**参数**：

- **switch**(bool)：是否冻结系统提示词。`True`表示系统提示词冻结，不可优化；`False`表示系统不冻结提示词，可被优化。

**样例：**

```python
>>> import os
>>> from openjiuwen.core.operator.llm_call.base import LLMCall
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>>
>>> # 1、创建访问的大模型
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2、创建提示词
>>> system_prompt = "你是一个信息抽取助手."
>>> user_prompt = "请从给定句子中提取所有的人名名称输出格式为[人名1, 人名2, ...]的列表形式，不要输出其他内容，以下是用户输入：{{context}}"
>>> 
>>> # 3、创建提示词优化层
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>>
>>> # 4、切换系统提示词模板的冻结状态。
>>> llm_call.set_freeze_system_prompt(True)
```

### set_freeze_user_prompt

```python
set_freeze_user_prompt(switch: bool)
```

设置用户提示词模板的冻结状态。

**参数**：

- **switch**(bool)：是否冻结用户提示词。`True`表示用户提示词冻结，不可优化；`False`表示不冻结提示词，可被优化。

**样例：**

```python
>>> import os
>>> from openjiuwen.core.operator.llm_call.base import LLMCall
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>>
>>> # 1、创建访问的大模型
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2、创建提示词
>>> system_prompt = "你是一个信息抽取助手."
>>> user_prompt = "请从给定句子中提取所有的人名名称输出格式为[人名1, 人名2, ...]的列表形式，不要输出其他内容，以下是用户输入：{{context}}"
>>> 
>>> # 3、创建提示词优化层
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>>
>>> # 4、切换用户提示词模板的冻结状态。
>>> llm_call.set_freeze_system_prompt(True)
```

### get_freeze_system_prompt

```python
get_freeze_system_prompt() -> bool
```

获取系统提示词的冻结状态。

**返回值**：
**bool**，`True`表示系统提示词冻结，不可优化；`False`表示系统不冻结提示词，可被优化。

```python
>>> import os
>>> from openjiuwen.core.operator.llm_call.base import LLMCall
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>>
>>> # 1、创建访问的大模型
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2、创建提示词
>>> system_prompt = "你是一个信息抽取助手."
>>> user_prompt = "请从给定句子中提取所有的人名名称输出格式为[人名1, 人名2, ...]的列表形式，不要输出其他内容，以下是用户输入：{{context}}"
>>> 
>>> # 3、创建提示词优化层
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>>
>>> # 4、查看系统提示词模板的冻结状态。
>>> print(llm_call.get_freeze_system_prompt())
True
```

### get_freeze_user_prompt

```python
get_freeze_user_prompt() -> bool
```

获取用户提示词的冻结状态。

**返回值**：
**bool**，`True`表示用户提示词冻结，不可优化；`False`表示不冻结用户提示词，可被优化。

```python
>>> import os
>>> from openjiuwen.core.operator.llm_call.base import LLMCall
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> 
>>> # 1、创建访问的大模型
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2、创建提示词
>>> system_prompt = "你是一个信息抽取助手."
>>> user_prompt = "请从给定句子中提取所有的人名名称输出格式为[人名1, 人名2, ...]的列表形式，不要输出其他内容，以下是用户输入：{{context}}"
>>> 
>>> # 3、创建提示词优化层
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>> 
>>> # 4、查看用户提示词模板的冻结状态。
>>> print(llm_call.get_freeze_user_prompt())
False
```
