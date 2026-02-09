# openjiuwen.core.operator.llm_call.base

## class openjiuwen.core.operator.llm_call.base.LLMCall

```python
openjiuwen.core.operator.llm_call.base.LLMCall(model_name, llm, system_prompt, user_prompt, freeze_system_prompt, freeze_user_prompt)
```

A model invocation operator class. As an optimizable parameter, it binds model invocation with prompts. Combined with the tuning toolchain, an LLMCall object can dynamically optimize prompts to achieve better performance for specific tasks.

**Parameters**:

- **model_name** (str): The name of the large model to specify the exact model.
- **llm** ([BaseChatModel](../../utils/llm/base.md)): An instance of the large language model.
- **system_prompt** (Union[str, List[[BaseMessage](../../utils/llm/messages.md)], List[Dict]]): A list of system prompts used to define the model's role and behavior. Supports str, [SystemMessage](../../utils/llm/messages.md#class-openjiuwencoreutilsllmmessagessystemmessage), or a dict following the SystemMessage format.
- **user_prompt** (Union[str, List[[BaseMessage](../../utils/llm/messages.md)], List[Dict]]): The user input prompt. Supports str, [HumanMessage](../../utils/llm/messages.md#class-openjiuwencoreutilsllmmessageshumanmessage), or a dict following the HumanMessage format.
- **freeze_system_prompt** (bool, optional): Whether to freeze the system prompt template. Frozen prompts will not be optimized. True to freeze, False to allow optimization. Default: False.
- **freeze_user_prompt** (bool, optional): Whether to freeze the user prompt template. Frozen prompts will not be optimized. True to freeze, False to allow optimization. Default: True.

**Example**:

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
>>> # 1. Create the target LLM
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
... 
>>> # 2. Create prompts
>>> system_prompt = "You are an information extraction assistant."
>>> user_prompt = "Please extract all person names from the given sentence and output them as a list in the form [Name1, Name2, ...]. Do not output anything else. Here is the user input: {{context}}"
>>> 
>>> # 3. Create the prompt optimization layer
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
```

### async invoke

```python
async invoke(inputs: Dict[str, Any], runtime: Runtime, history: Optional[List[BaseMessage]], tools: Optional[List[ToolInfo]]) -> AIMessage
```

Asynchronously invoke the model operator to generate a response.

**Parameters**:

- **inputs** (Dict[str, Any]): Input context variables to fill placeholders in the prompt templates.
- **runtime** ([Runtime](../../runtime/runtime.md)): Runtime context.
- **history** (Optional[List[BaseMessage]], optional): List of historical conversation messages. None means no conversation history. Default: None.
- **tools** (Optional[List[ToolInfo]], optional): Available tool list for plugin invocation scenarios. None means no plugin invocation. Default: None.

**Returns**:
**AIMessage**, a complete response message containing the model output.

**Example**:

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
>>> # 1. Create the target LLM
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2. Create prompts
>>> system_prompt = "You are a Q&A assistant. Please answer the user's questions briefly."
>>> user_prompt = "Here is the user input: {{query}}"
>>> 
>>> # 3. Create the prompt optimization layer
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>> 
>>> # 4. Invoke the model
>>> response = asyncio.run(
...     llm_call.invoke(
...         inputs={"query": "What is the deepest lake in the world?"},
...         runtime=AgentRuntime(session_id="id")
...     )
... )
>>> 
>>> print(response.content)
The deepest lake in the world is Lake Baikal in Russia.
```

### async stream

```python
async stream(inputs: Dict[str, Any], runtime: Runtime, history: Optional[List[BaseMessage]], tools: Optional[List[ToolInfo]]) -> Iterator[AIMessageChunk]
```

Asynchronously invoke the model operator to generate a streaming response.

**Parameters**:

- **inputs** (Dict[str, Any]): Input context variables to fill placeholders in the prompt templates.
- **runtime** ([Runtime](../../runtime/runtime.md)): Runtime context.
- **history** (Optional[List[BaseMessage]], optional): List of historical conversation messages. None means no conversation history. Default: None.
- **tools** (Optional[List[ToolInfo]], optional): Available tool list for plugin invocation scenarios. None means no plugin invocation. Default: None.

**Returns**:
**Iterator[AIMessageChunk]**, an asynchronous streaming iterator. Each iteration yields an AIMessageChunk representing a message fragment, progressively outputting AI-generated content chunk by chunk.

**Example**:

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
>>> # 1. Create the target LLM
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2. Create prompts
>>> system_prompt = "You are a Q&A assistant. Please answer the user's questions briefly."
>>> user_prompt = "Here is the user input: {{query}}"
>>> 
>>> # 3. Create the prompt optimization layer
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>> 
>>> # 4. Invoke the model
>>> async def main():
...     async for chunk in llm_call.stream(
...         inputs={"query": "What is the deepest lake in the world?"},
...         runtime=AgentRuntime(session_id="id")
...     ):
...         print(chunk.content, end="", flush=True)
... 
>>> asyncio.run(main())
The deepest lake in the world is Lake Baikal in Russia.
```

### get_system_prompt

```python
get_system_prompt() -> Template
```

Get the current system prompt template object.

**Returns**:
[Template](../../utils/prompt/template.md), a Template instance containing the system prompt.

**Example**:

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
>>> # 1. Create the target LLM
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2. Create prompts
>>> system_prompt = "You are an information extraction assistant."
>>> user_prompt = "Please extract all person names from the given sentence and output them as a list in the form [Name1, Name2, ...]. Do not output anything else. Here is the user input: {{context}}"
>>> 
>>> # 3. Create the prompt optimization layer
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>> 
>>> # 4. Get the current system prompt template
>>> print(llm_call.get_system_prompt().content)
You are an information extraction assistant.
```

### get_user_prompt

```python
get_user_prompt() -> Template
```

Get the current user prompt template.

**Returns**:
[Template](../../utils/prompt/template.md#class-openjiuwencoreutilsprompttemplatetemplatetemplate), a Template instance containing the user prompt.

**Example**:

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
>>> # 1. Create the target LLM
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2. Create prompts
>>> system_prompt = "You are an information extraction assistant."
>>> user_prompt = "Please extract all person names from the given sentence and output them as a list in the form [Name1, Name2, ...]. Do not output anything else. Here is the user input: {{context}}"
>>> 
>>> # 3. Create the prompt optimization layer
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>> 
>>> # 4. Get the current user prompt template object
>>> print(llm_call.get_user_prompt().content)
Please extract all person names from the given sentence and output them as a list in the form [Name1, Name2, ...]. Do not output anything else. Here is the user input: {{context}}
```

### update_system_prompt

```python
update_system_prompt(system_prompt: Union[str, List[BaseMessage], List[Dict]])
```

Update the system prompt content.

**Parameters**:

- **system_prompt** (Union[str, List[BaseMessage], List[Dict]]): The updated system prompt.

**Example**:

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
>>> # 1. Create the target LLM
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> # 2. Create prompts
>>> system_prompt = "You are an information extraction assistant."
>>> user_prompt = "Please extract all person names from the given sentence and output them as a list in the form [Name1, Name2, ...]. Do not output anything else. Here is the user input: {{context}}"
>>> 
>>> # 3. Create the prompt optimization layer
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=False, freeze_user_prompt=False)
>>> 
>>> # 4. Dynamically update the system prompt content
>>> llm_call.update_system_prompt("You are an intelligent home assistant.")
>>> 
>>> # 5. Get the current system prompt template
>>> print(llm_call.get_system_prompt().content)
You are an intelligent home assistant.
```

### update_user_prompt

```python
update_user_prompt(user_prompt: Union[str, List[BaseMessage], List[Dict]])
```

Update the user prompt content.

**Parameters**:

- **user_prompt** (Union[str, List[BaseMessage], List[Dict]]): The updated user prompt.

**Example**:

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
>>> # 1. Create the target LLM
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2. Create prompts
>>> system_prompt = "You are an information extraction assistant."
>>> user_prompt = "Please extract all person names from the given sentence and output them as a list in the form [Name1, Name2, ...]. Do not output anything else. Here is the user input: {{context}}"
>>> 
>>> # 3. Create the prompt optimization layer
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>> 
>>> # 4. Dynamically update the user prompt content
>>> llm_call.update_user_prompt("Please extract all person names from the given sentence. Here is the user input: {{context}}")
>>> 
>>> # 5. Get the current user prompt template object
>>> print(llm_call.get_user_prompt().content)
Please extract all person names from the given sentence. Here is the user input: {{context}}
```

### set_freeze_system_prompt

```python
set_freeze_system_prompt(switch: bool)
```

Set the freeze state of the system prompt template.

**Parameters**:

- **switch** (bool): Whether to freeze the system prompt. True means the system prompt is frozen and cannot be optimized; False means it is not frozen and can be optimized.

**Example**:

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
>>> # 1. Create the target LLM
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2. Create prompts
>>> system_prompt = "You are an information extraction assistant."
>>> user_prompt = "Please extract all person names from the given sentence and output them as a list in the form [Name1, Name2, ...]. Do not output anything else. Here is the user input: {{context}}"
>>> 
>>> # 3. Create the prompt optimization layer
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>>
>>> # 4. Toggle the freeze state of the system prompt template
>>> llm_call.set_freeze_system_prompt(True)
```

### set_freeze_user_prompt

```python
set_freeze_user_prompt(switch: bool)
```

Set the freeze state of the user prompt template.

**Parameters**:

- **switch** (bool): Whether to freeze the user prompt. True means the user prompt is frozen and cannot be optimized; False means it is not frozen and can be optimized.

**Example**:

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
>>> # 1. Create the target LLM
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2. Create prompts
>>> system_prompt = "You are an information extraction assistant."
>>> user_prompt = "Please extract all person names from the given sentence and output them as a list in the form [Name1, Name2, ...]. Do not output anything else. Here is the user input: {{context}}"
>>> 
>>> # 3. Create the prompt optimization layer
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>>
>>> # 4. Toggle the freeze state of the user prompt template
>>> llm_call.set_freeze_system_prompt(True)
```

### get_freeze_system_prompt

```python
get_freeze_system_prompt() -> bool
```

Get the freeze state of the system prompt.

**Returns**:
**bool**, True means the system prompt is frozen and cannot be optimized; False means it is not frozen and can be optimized.

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
>>> # 1. Create the target LLM
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2. Create prompts
>>> system_prompt = "You are an information extraction assistant."
>>> user_prompt = "Please extract all person names from the given sentence and output them as a list in the form [Name1, Name2, ...]. Do not output anything else. Here is the user input: {{context}}"
>>> 
>>> # 3. Create the prompt optimization layer
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>>
>>> # 4. Check the freeze state of the system prompt template
>>> print(llm_call.get_freeze_system_prompt())
True
```

### get_freeze_user_prompt

```python
get_freeze_user_prompt() -> bool
```

Get the freeze state of the user prompt.

**Returns**:
**bool**, True means the user prompt is frozen and cannot be optimized; False means it is not frozen and can be optimized.

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
>>> # 1. Create the target LLM
>>> llm = ModelFactory().get_model(
...     model_provider=MODEL_PROVIDER,
...     api_key=API_KEY,
...     api_base=API_BASE
... )
>>> 
>>> # 2. Create prompts
>>> system_prompt = "You are an information extraction assistant."
>>> user_prompt = "Please extract all person names from the given sentence and output them as a list in the form [Name1, Name2, ...]. Do not output anything else. Here is the user input: {{context}}"
>>> 
>>> # 3. Create the prompt optimization layer
>>> llm_call = LLMCall(model_name=MODEL_NAME, llm=llm, system_prompt=system_prompt, user_prompt=user_prompt, freeze_system_prompt=True, freeze_user_prompt=False)
>>> 
>>> # 4. Check the freeze state of the user prompt template
>>> print(llm_call.get_freeze_user_prompt())
False
```