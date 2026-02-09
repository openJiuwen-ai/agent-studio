# openjiuwen.agent.react_agent

## create_react_agent_config

```python
create_react_agent_config(agent_id: str, agent_version: str, description: str, model: ModelConfig, prompt_template: List[Dict])
```

Creates a ReActAgent configuration object.

**Parameters**:

* **agent_id** (str): Unique identifier of the agent.
* **agent_version** (str): Version number of the agent.
* **description** (str): Description of the agent.
* **model** ([ModelConfig](../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig)): Model configuration used by the agent.
* **prompt_template** (List[Dict]): A list of prompt templates. Each dict is in the format
  `dict(role="system", content="You are an AI assistant. Call the appropriate tools when needed to help me complete tasks!")`.
  The `role` can be `system` or `user`. When `role` is `system`, it indicates a system prompt; when `role` is `user`, it indicates a user prompt. Default: `[]`.

**Returns**:

**[ReActAgentConfig](config/react_config.md#class-openjiuwenagentconfigreact_configreactagentconfig)**, a newly created `ReActAgentConfig` object.

**Example**:

```python
>>> import os 
>>> from datetime import datetime
>>> from openjiuwen.agent.common.schema import PluginSchema
>>> from openjiuwen.agent.react_agent import create_react_agent_config
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> 
>>> def build_current_date():
...     current_datetime = datetime.now()
...     return current_datetime.strftime("%Y-%m-%d")
>>> 
>>> def _create_model():
...     return ModelConfig(model_provider=MODEL_PROVIDER,
...                        model_info=BaseModelInfo(
...                            model=MODEL_NAME,
...                            api_base=API_BASE,
...                            api_key=API_KEY,
...                            temperature=0.7,
...                            top_p=0.9,
...                            timeout=30
...                        ))
>>>  
>>> def _create_prompt_template():
...     system_prompt = "You are an AI assistant. Call appropriate tools when needed to help me complete tasks! Today's date is: {}\nNote: 1. If the user's request does not specify a specific time, default to today."
...     return [
...         dict(role="system", content=system_prompt.format(build_current_date()))
...     ]
>>> 
>>> model_config = _create_model()
>>> prompt_template = _create_prompt_template()
>>> 
>>> react_agent_config = create_react_agent_config(
...     agent_id="react_agent_123",
...     agent_version="0.0.1",
...     description="AI Assistant",
...     model=model_config,
...     prompt_template=prompt_template
... )
```

---

## class openjiuwen.agent.react_agent.ReActAgent

```python
openjiuwen.agent.react_agent.ReActAgent(agent_config: ReActAgentConfig)
```

`ReActAgent` is an agent that follows the ReAct (Reasoning + Action) planning pattern. It completes user tasks through an iterative loop of **“Thought → Action → Observe”**. First, the model performs logical reasoning to plan, then selects and calls appropriate tools (such as retrieval, databases, third-party APIs, code execution, etc.) or workflows to carry out actions. Next, it observes the results and feedback, continuously adjusting strategies and optimizing the reasoning path until the task is completed or a final answer is obtained. Its strong multi-step reasoning and self-correction abilities give the ReActAgent dynamic decision-making capabilities and flexibility in changing environments, making it suitable for diverse task scenarios that require complex reasoning and strategy adjustment.

**Parameters**:

* **agent_config** ([ReActAgentConfig](config/react_config.md#class-openjiuwenagentconfigreact_configreactagentconfig)): Configuration for the ReActAgent.

**Example**:

```python
>>> import os
>>> from datetime import datetime
>>> from openjiuwen.agent.common.schema import PluginSchema
>>> from openjiuwen.agent.react_agent import create_react_agent_config, ReActAgent
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> 
>>> API_BASE = os.getenv("API_BASE", "your api base")
>>> API_KEY = os.getenv("API_KEY", "your api key")
>>> MODEL_NAME = os.getenv("MODEL_NAME", "")
>>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
>>> 
>>> def build_current_date():
...     current_datetime = datetime.now()
...     return current_datetime.strftime("%Y-%m-%d")
>>> 
>>> def _create_model():
...     return ModelConfig(model_provider=MODEL_PROVIDER,
...                        model_info=BaseModelInfo(
...                            model=MODEL_NAME,
...                            api_base=API_BASE,
...                            api_key=API_KEY,
...                            temperature=0.7,
...                            top_p=0.9,
...                            timeout=30
...                        )) 
>>> 
>>> def _create_prompt_template():
...     system_prompt = "You are an AI assistant. Call appropriate tools when needed to help me complete tasks! Today's date is: {}\nNote: 1. If the user's request does not specify a specific time, default to today."
...     return [
...         dict(role="system", content=system_prompt.format(build_current_date()))
...     ]
>>> 
>>> model_config = _create_model()
>>> prompt_template = _create_prompt_template()
>>> 
>>> react_agent_config = create_react_agent_config(
...     agent_id="react_agent_123",
...     agent_version="0.0.1",
...     description="AI Assistant",
...     model=model_config,
...     prompt_template=prompt_template
... )
>>> 
>>> react_agent = ReActAgent(agent_config=react_agent_config)
```

---

### async invoke

```python
async invoke(self, inputs: Dict, runtime: Runtime = None) -> Dict
```

Runs the ReActAgent.

**Parameters**:

* **inputs** (Dict): Input data for the ReActAgent. Supported keys include:

  * **query** (str): The user query content.
  * **conversation_id** (str, optional): Conversation ID used to distinguish different sessions. Default: `default_session`.
* **runtime** (Runtime, optional): Runtime instance (if not provided, uses `BaseAgent`’s `_runtime`).

**Returns**:

**Dict**, the final output result of the ReActAgent.

**Example**:

* Example 1:

  ```python
  >>> import os
  >>> import asyncio
  >>> from datetime import datetime
  >>> from openjiuwen.agent.common.schema import PluginSchema
  >>> from openjiuwen.agent.react_agent import create_react_agent_config, ReActAgent
  >>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
  >>> from openjiuwen.core.utils.llm.base import BaseModelInfo
  >>> from openjiuwen.core.utils.tool.param import Param
  >>> from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
  >>> 
  >>> API_BASE = os.getenv("API_BASE", "your api base")
  >>> API_KEY = os.getenv("API_KEY", "your api key")
  >>> MODEL_NAME = os.getenv("MODEL_NAME", "")
  >>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
  >>> 
  >>> def build_current_date():
  ...     current_datetime = datetime.now()
  ...     return current_datetime.strftime("%Y-%m-%d")
  >>> 
  >>> def _create_model():
  ...     return ModelConfig(model_provider=MODEL_PROVIDER,
  ...                        model_info=BaseModelInfo(
  ...                            model=MODEL_NAME,
  ...                            api_base=API_BASE,
  ...                            api_key=API_KEY,
  ...                            temperature=0.7,
  ...                            top_p=0.9,
  ...                            timeout=30
  ...                        ))
  >>> 
  >>> def _create_tool():
  ...     weather_plugin = RestfulApi(
  ...         name="WeatherReporter",
  ...         description="Weather query plugin",
  ...         params=[
  ...             Param(name="location", description="Location to query weather for; must be in English", type="string", required=True),
  ...             Param(name="date", description="Date to query weather for, in YYYY-MM-DD format", type="string", required=True),
  ...         ],
  ...         path="your path to weather service",
  ...         headers={},
  ...         method="GET",
  ...         response=[],
  ...     )
  ...     return weather_plugin
  >>>  
  >>> def _create_prompt_template():
  ...     system_prompt = "You are an AI assistant. Call appropriate tools when needed to help me complete tasks! Today's date is: {}\nNote: 1. If the user's request does not specify a specific time, default to today."
  ...     return [
  ...         dict(role="system", content=system_prompt.format(build_current_date()))
  ...     ]
  >>> 
  >>> model_config = _create_model()
  >>> prompt_template = _create_prompt_template()
  >>> 
  >>> react_agent_config = create_react_agent_config(
  ...     agent_id="react_agent_123",
  ...     agent_version="0.0.1",
  ...     description="AI Assistant",
  ...     model=model_config,
  ...     prompt_template=prompt_template
  ... )
  >>> 
  >>> react_agent: ReActAgent = ReActAgent(react_agent_config)
  >>> react_agent.add_tools([_create_tool()])
  >>> 
  >>> async def run_test():
  ...     result = await react_agent.invoke({"query": "Check Hangzhou's weather"})
  ...     print(f"ReActAgent final output: {result}")
  ReActAgent final output: {'output': "Hangzhou's weather today is as follows:\n\n- Weather: Sunny\n- Temperature: 32.6°C\n- Feels like: 34.48°C\n- Humidity: 46%\n- Wind speed: 3.21 m/s\n\nIt's sunny but quite hot—please remember sun protection and stay hydrated!", 'result_type': 'answer'}
  >>> 
  >>> asyncio.run(run_test())
  ```

---

### async stream

```python
async stream(self, inputs: Dict, runtime: Runtime = None) -> AsyncIterator[Any]
```

Runs the ReActAgent in streaming mode, returning intermediate results step by step.

**Parameters**:

* **inputs** (Dict): Input data for the ReActAgent. Supported keys include:

  * **query** (str): The user query content.
  * **conversation_id** (str, optional): Conversation ID used to distinguish different sessions. Default: `default_session`.
* **runtime** (Runtime, optional): Runtime instance (if not provided, uses `BaseAgent`’s `_runtime`).

**Returns**:

**AsyncIterator[Any]**, an async iterator that yields the streamed outputs, including types such as `BaseMessageChunk`.

**Example**:

* Example 1:

  ```python
  >>> import os
  >>> import asyncio
  >>> from datetime import datetime
  >>> from openjiuwen.agent.common.schema import PluginSchema
  >>> from openjiuwen.agent.react_agent import create_react_agent_config, ReActAgent
  >>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
  >>> from openjiuwen.core.utils.llm.base import BaseModelInfo
  >>> from openjiuwen.core.utils.tool.param import Param
  >>> from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
  >>> 
  >>> API_BASE = os.getenv("API_BASE", "your api base")
  >>> API_KEY = os.getenv("API_KEY", "your api key")
  >>> MODEL_NAME = os.getenv("MODEL_NAME", "")
  >>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
  >>> 
  >>> def build_current_date():
  ...     current_datetime = datetime.now()
  ...     return current_datetime.strftime("%Y-%m-%d")
  >>> 
  >>> def _create_model():
  ...     return ModelConfig(model_provider=MODEL_PROVIDER,
  ...                        model_info=BaseModelInfo(
  ...                            model=MODEL_NAME,
  ...                            api_base=API_BASE,
  ...                            api_key=API_KEY,
  ...                            temperature=0.7,
  ...                            top_p=0.9,
  ...                            timeout=30
  ...                        ))
  >>> 
  >>> def _create_tool():
  ...     weather_plugin = RestfulApi(
  ...         name="WeatherReporter",
  ...         description="Weather query plugin",
  ...         params=[
  ...             Param(name="location", description="Location to query weather for; must be in English", type="string", required=True),
  ...             Param(name="date", description="Date to query weather for, in YYYY-MM-DD format", type="string", required=True),
  ...         ],
  ...         path="your path to weather service",
  ...         headers={},
  ...         method="GET",
  ...         response=[],
  ...     )
  ...     return weather_plugin
  >>> 
  >>> def _create_prompt_template():
  ...     system_prompt = "You are an AI assistant. Call appropriate tools when needed to help me complete tasks! Today's date is: {}\nNote: 1. If the user's request does not specify a specific time, default to today."
  ...     return [
  ...         dict(role="system", content=system_prompt.format(build_current_date()))
  ...     ]
  >>> 
  >>> model_config = _create_model()
  >>> prompt_template = _create_prompt_template()
  >>> 
  >>> react_agent_config = create_react_agent_config(
  ...     agent_id="react_agent_123",
  ...     agent_version="0.0.1",
  ...     description="AI Assistant",
  ...     model=model_config,
  ...     prompt_template=prompt_template
  ... )
  >>> 
  >>> react_agent: ReActAgent = ReActAgent(react_agent_config)
  >>> react_agent.add_tools([_create_tool()])
  >>> 
  >>> async def run_test():
  ...     async for chunk in react_agent.stream({"query": "Check Hangzhou's weather"}):
  ...         print(f"Streaming output: {chunk}")
  >>> 
  >>> if __name__ == "__main__":
  ...     asyncio.run(run_test())
  ```

---

### add_tools

```python
add_tools(self, tools: List[Tool])
```

Binds tools to the ReActAgent.

**Parameters**:

* **tools** (List[[Tool](../openjiuwen.core/utils/tool/tool.md#openjiuwencoreutilstooltool)]): A list of tools to bind to the ReActAgent.

**Examples**:

* Example 1:

  ```python
  >>> import os
  >>> from datetime import datetime
  >>> from openjiuwen.agent.common.schema import PluginSchema
  >>> from openjiuwen.agent.react_agent import create_react_agent_config, ReActAgent
  >>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
  >>> from openjiuwen.core.utils.llm.base import BaseModelInfo
  >>> from openjiuwen.core.utils.tool.param import Param
  >>> from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
  >>> 
  >>> API_BASE = os.getenv("API_BASE", "your api base")
  >>> API_KEY = os.getenv("API_KEY", "your api key")
  >>> MODEL_NAME = os.getenv("MODEL_NAME", "")
  >>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
  >>> 
  >>> def build_current_date():
  ...     current_datetime = datetime.now()
  ...     return current_datetime.strftime("%Y-%m-%d")
  >>> 
  >>> def _create_model():
  ...     return ModelConfig(model_provider=MODEL_PROVIDER,
  ...                        model_info=BaseModelInfo(
  ...                            model=MODEL_NAME,
  ...                            api_base=API_BASE,
  ...                            api_key=API_KEY,
  ...                            temperature=0.7,
  ...                            top_p=0.9,
  ...                            timeout=30
  ...                        ))
  >>> 
  >>> def _create_tool():
  ...     weather_plugin = RestfulApi(
  ...         name="WeatherReporter",
  ...         description="Weather query plugin",
  ...         params=[
  ...             Param(name="location", description="Location to query weather for; must be in English", type="string", required=True),
  ...             Param(name="date", description="Date to query weather for, in YYYY-MM-DD format", type="string", required=True),
  ...         ],
  ...         path="your path to weather service",
  ...         headers={},
  ...         method="GET",
  ...         response=[],
  ...     )
  ...     return weather_plugin
  >>> 
  >>> def _create_prompt_template():
  ...     system_prompt = "You are an AI assistant. Call appropriate tools when needed to help me complete tasks! Today's date is: {}\nNote: 1. If the user's request does not specify a specific time, default to today."
  ...     return [
  ...         dict(role="system", content=system_prompt.format(build_current_date()))
  ...     ]
  >>> 
  >>> model_config = _create_model()
  >>> prompt_template = _create_prompt_template()
  >>> 
  >>> react_agent_config = create_react_agent_config(
  ...     agent_id="react_agent_123",
  ...     agent_version="0.0.1",
  ...     description="AI Assistant",
  ...     model=model_config,
  ...     prompt_template=prompt_template
  ... )
  >>> 
  >>> react_agent: ReActAgent = ReActAgent(react_agent_config)
  >>> # Bind tools
  >>> react_agent.add_tools([_create_tool()])
  ```

* Example 2:

  ```python
  >>> # Example using the LocalFunction tool:
  >>> # In addition to RestfulApi, you can use LocalFunction to register a Python function as a tool.
  >>> import os
  >>> import asyncio
  >>> from datetime import datetime
  >>> from openjiuwen.agent.common.schema import PluginSchema
  >>> from openjiuwen.agent.react_agent import create_react_agent_config, ReActAgent
  >>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
  >>> from openjiuwen.core.utils.llm.base import BaseModelInfo
  >>> from openjiuwen.core.utils.tool.param import Param
  >>> from openjiuwen.core.utils.tool.function.function import LocalFunction
  >>> 
  >>> API_BASE = os.getenv("API_BASE", "your api base")
  >>> API_KEY = os.getenv("API_KEY", "your api key")
  >>> MODEL_NAME = os.getenv("MODEL_NAME", "")
  >>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
  >>> 
  >>> def build_current_date():
  ...     current_datetime = datetime.now()
  ...     return current_datetime.strftime("%Y-%m-%d")
  >>> 
  >>> def _create_model():
  ...     return ModelConfig(model_provider=MODEL_PROVIDER,
  ...                        model_info=BaseModelInfo(
  ...                            model=MODEL_NAME,
  ...                            api_base=API_BASE,
  ...                            api_key=API_KEY,
  ...                            temperature=0.7,
  ...                            top_p=0.9,
  ...                            timeout=30
  ...                        ))
  >>> 
  >>> def _create_function_tool():
  ...     """Create a local function tool"""
  ...     add_tool = LocalFunction(
  ...         name="add",
  ...         description="Addition",
  ...         params=[
  ...             Param(name="a", description="Addend", type="number", required=True),
  ...             Param(name="b", description="Augend", type="number", required=True),
  ...         ],
  ...         func=lambda a, b: a + b
  ...     )
  ...     return add_tool
  >>> 
  >>> def _create_function_prompt_template():
  ...     system_prompt = "You are a math calculation expert."
  ...     return [
  ...         dict(role="system", content=system_prompt)
  ...     ]
  >>> 
  >>> model_config = _create_model()
  >>> prompt_template = _create_function_prompt_template()
  >>> 
  >>> react_agent_config = create_react_agent_config(
  ...     agent_id="react_agent_1234",
  ...     agent_version="0.0.2",
  ...     description="AI Math Assistant",
  ...     model=model_config,
  ...     prompt_template=prompt_template
  ... )
  >>> 
  >>> react_agent: ReActAgent = ReActAgent(react_agent_config)
  >>> 
  >>> # Bind the local function tool
  >>> react_agent.add_tools([_create_function_tool()])
  >>> async def run_test():
  ...     result = await react_agent.invoke({"query": "Calculate 1+2"})
  ...     print(f"ReActAgent final output: {result}")
  ReActAgent final output: {'output': 'Calculation result: 1 + 2 = 12', 'result_type': 'answer'}
  >>> 
  >>> if __name__ == "__main__":
  ...     asyncio.run(run_test())
  ```

* Example 3:

  ```python
  >>> # Example using the @tool decorator:
  >>> # The @tool decorator provides a simpler way to register a Python function as a tool.
  >>> import os
  >>> import asyncio
  >>> from datetime import datetime
  >>> from openjiuwen.agent.common.schema import PluginSchema
  >>> from openjiuwen.agent.react_agent import create_react_agent_config, ReActAgent
  >>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
  >>> from openjiuwen.core.utils.llm.base import BaseModelInfo
  >>> from openjiuwen.core.utils.tool.param import Param
  >>> from openjiuwen.core.utils.tool.tool import tool
  >>> 
  >>> API_BASE = os.getenv("API_BASE", "your api base")
  >>> API_KEY = os.getenv("API_KEY", "your api key")
  >>> MODEL_NAME = os.getenv("MODEL_NAME", "")
  >>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
  >>> 
  >>> def build_current_date():
  ...     current_datetime = datetime.now()
  ...     return current_datetime.strftime("%Y-%m-%d")
  >>> 
  >>> def _create_model():
  ...     return ModelConfig(model_provider=MODEL_PROVIDER,
  ...                        model_info=BaseModelInfo(
  ...                            model=MODEL_NAME,
  ...                            api_base=API_BASE,
  ...                            api_key=API_KEY,
  ...                            temperature=0.7,
  ...                            top_p=0.9,
  ...                            timeout=30
  ...                        ))
  >>> 
  >>> # Define a tool function using the @tool decorator
  >>> @tool(
  ...     name="add",
  ...     description="Addition",
  ...     params=[
  ...         Param(name="a", description="Addend", type="number", required=True),
  ...         Param(name="b", description="Augend", type="number", required=True),
  ...     ]
  ... )
  >>> def add_function(a, b):
  ...     """Addition function, decorated with the tool annotation"""
  ...     return a + b
  >>> 
  >>> def _create_function_prompt_template():
  ...     system_prompt = "You are a math calculation expert."
  ...     return [
  ...         dict(role="system", content=system_prompt)
  ...     ]
  >>> 
  >>> model_config = _create_model()
  >>> prompt_template = _create_function_prompt_template()
  >>> 
  >>> react_agent_config = create_react_agent_config(
  ...     agent_id="react_agent_1235",
  ...     agent_version="0.0.3",
  ...     description="AI Math Assistant (Annotation-based)",
  ...     model=model_config,
  ...     prompt_template=prompt_template
  ... )
  >>> 
  >>> react_agent: ReActAgent = ReActAgent(react_agent_config)
  >>> 
  >>> # Bind the tool created via the @tool decorator
  >>> react_agent.add_tools([add_function])
  >>> 
  >>> async def run_test():
  ...     result = await react_agent.invoke({"query": "Calculate 1+2"})
  ...     print(f"ReActAgent final output using annotation tool: {result}")
  ReActAgent final output using annotation tool: {'output': 'The result of 1 + 2 is 3.', 'result_type': 'answer'}
  >>> 
  >>> if __name__ == "__main__":
  ...     asyncio.run(run_test())
  ```
