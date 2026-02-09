# openjiuwen.agent.react_agent

## create_react_agent_config

```python
create_react_agent_config(agent_id: str, agent_version: str, description: str, model: ModelConfig, prompt_template: List[Dict])
```

创建ReActAgent配置对象。

**参数**：

- **agent_id**(str)：agent的唯一标识符。
- **agent_version**(str)：agent的版本号。
- **description**(str)：agent的描述信息。
- **model**([ModelConfig](../openjiuwen.core/common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig))：agent使用的模型配置。
- **prompt_template**(List[Dict])：提示词模板列表。dict格式为`dict(role="system", content="你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！")`，role的取值可为`system`或`user`，为`system`时表示是系统提示词，为`user`时表示是用户提示词。默认值：[]。

**返回**：

**[ReActAgentConfig](config/react_config.md#class-openjiuwenagentconfigreact_configreactagentconfig)**，一个新的ReActAgentConfig配置对象。

**样例**：

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
...     system_prompt = "你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！今天的日期为：{}\n注意：1. 如果用户请求中未指定具体时间，则默认为今天。"
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
...     description="AI助手",
...     model=model_config,
...     prompt_template=prompt_template
... )
```

## class openjiuwen.agent.react_agent.ReActAgent

```python
openjiuwen.agent.react_agent.ReActAgent(agent_config: ReActAgentConfig)
```

ReActAgent是一种遵循ReAct（Reasoning + Action）规划模式的Agent，通过 “思考（Thought）→ 行动（Action）→ 观察（Observe）”的循环迭代完成用户任务。首先，模型进行逻辑推理进行规划，选择并调用合适的工具（如检索、数据库、第三方 API、代码执行等）或工作流执行具体的操作，接着根据执行结果观察与反馈，不断调整策略，优化推理路径，直至达成任务目标或获得最终答案。其强大的多轮推理与自我修正能力，使ReActAgent具备动态决策能力且能够灵活应对环境变化，适用于需要复杂推理和策略调整的多样化任务场景。

**参数**：

- **agent_config**([ReActAgentConfig](config/react_config.md#class-openjiuwenagentconfigreact_configreactagentconfig))：ReActAgent配置。

**样例**：

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
...     system_prompt = "你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！今天的日期为：{}\n注意：1. 如果用户请求中未指定具体时间，则默认为今天。"
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
...     description="AI助手",
...     model=model_config,
...     prompt_template=prompt_template
... )
>>> 
>>> react_agent = ReActAgent(agent_config=react_agent_config)
```

### async invoke

```python
async invoke(self, inputs: Dict, runtime: Runtime = None) -> Dict
```

运行ReActAgent。

**参数**：

- **inputs**(Dict)：ReActAgent的输入数据。支持的键包括：
  - **query**(str)：用户查询内容。
  - **conversation_id**(str, 可选)：会话ID，用于区分不同会话。默认值：default_session。
- **runtime(Runtime, 可选)**: Runtime（如果不提供，使用 BaseAgent 的 _runtime）

**返回**：

**Dict**，ReActAgent最终输出结果。

**样例**：

- 样例一：
  
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
  ...         description="天气查询插件",
  ...         params=[
  ...             Param(name="location", description="天气查询的地点，必须为英文", type="string", required=True),
  ...             Param(name="date", description="天气查询的时间，格式为YYYY-MM-DD", type="string", required=True),
  ...         ],
  ...         path="your path to weather service",
  ...         headers={},
  ...         method="GET",
  ...         response=[],
  ...     )
  ...     return weather_plugin
  >>>  
  >>> def _create_prompt_template():
  ...     system_prompt = "你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！今天的日期为：{}\n注意：1. 如果用户请求中未指定具体时间，则默认为今天。"
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
  ...     description="AI助手",
  ...     model=model_config,
  ...     prompt_template=prompt_template
  ... )
  >>> 
  >>> react_agent: ReActAgent = ReActAgent(react_agent_config)
  >>> react_agent.add_tools([_create_tool()])
  >>> 
  >>> async def run_test():
  ...     result = await react_agent.invoke({"query": "查询杭州的天气"})
  ...     print(f"ReActAgent 最终输出结果：{result}")
  ReActAgent 最终输出结果：{'output': '杭州今天的天气情况如下：\n\n- 天气：晴\n- 温度：32.6°C\n- 体感温度：34.48°C\n- 湿度：46%\n- 风速：3.21 m/s\n\n天气晴朗，但温度较高，请注意防晒和补水！', 'result_type': 'answer'}
  >>> 
  >>> asyncio.run(run_test())
  ```

### async stream

```python
async stream(self, inputs: Dict, runtime: Runtime = None) -> AsyncIterator[Any]
```

以流式方式运行ReActAgent，逐步返回中间结果。

**参数**：

- **inputs**(Dict)：ReActAgent的输入数据。支持的键包括：
  - **query**(str)：用户查询内容。
  - **conversation_id**(str, 可选)：会话ID，用于区分不同会话。默认值：`default_session`。
- **runtime(Runtime, 可选)**: Runtime（如果不提供，使用 BaseAgent 的 _runtime）

**返回**：

**AsyncIterator[Any]**，异步迭代器，返回数据流的迭代器，用于支持流式输出，包括`BaseMessageChunk`等类型的数据流。

**样例**：

- 样例一：
  
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
  ...         description="天气查询插件",
  ...         params=[
  ...             Param(name="location", description="天气查询的地点，必须为英文", type="string", required=True),
  ...             Param(name="date", description="天气查询的时间，格式为YYYY-MM-DD", type="string", required=True),
  ...         ],
  ...         path="your path to weather service",
  ...         headers={},
  ...         method="GET",
  ...         response=[],
  ...     )
  ...     return weather_plugin
  >>> 
  >>> def _create_prompt_template():
  ...     system_prompt = "你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！今天的日期为：{}\n注意：1. 如果用户请求中未指定具体时间，则默认为今天。"
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
  ...     description="AI助手",
  ...     model=model_config,
  ...     prompt_template=prompt_template
  ... )
  >>> 
  >>> react_agent: ReActAgent = ReActAgent(react_agent_config)
  >>> react_agent.add_tools([_create_tool()])
  >>> 
  >>> async def run_test():
  ...     async for chunk in react_agent.stream({"query": "查询杭州的天气"}):
  ...         print(f"流式输出: {chunk}")
  流式输出: type='tracer_agent' payload={'traceId': '95230980-45e2-4a1d-b58f-b81435933463', 'startTime': datetime.datetime(2025, 10, 10, 15, 3, 56, 280611), 'endTime': None, 'inputs': {'inputs': {}}, 'outputs': None, 'error': None, 'invokeId': 'f8e1225a-24e2-49eb-a56b-c3bc9c3d46cb', 'parentInvokeId': 'df49b119-a0a5-41f8-b605-dc9456cf7ff3', 'childInvokes': [], 'invokeType': 'plugin', 'name': 'RestfulApi', 'elapsedTime': None, 'metaData': {'class_name': 'RestfulApi', 'type': 'tool'}}
  流式输出: type='tracer_agent' payload={'traceId': '95230980-45e2-4a1d-b58f-b81435933463', 'startTime': datetime.datetime(2025, 10, 10, 15, 3, 56, 280611), 'endTime': datetime.datetime(2025, 10, 10, 15, 3, 56, 283458), 'inputs': {'inputs': {}}, 'outputs': {'outputs': {'errCode': 0, 'errMessage': 'success', 'data': {'city': 'Hangzhou', 'country': 'CN', 'feels_like': 35.6, 'humidity': 48, 'temperature': 32.93, 'weather': '晴', 'wind_speed': 3.21}}}, 'error': None, 'invokeId': 'f8e1225a-24e2-49eb-a56b-c3bc9c3d46cb', 'parentInvokeId': 'df49b119-a0a5-41f8-b605-dc9456cf7ff3', 'childInvokes': [], 'invokeType': 'plugin', 'name': 'RestfulApi', 'elapsedTime': '3ms', 'metaData': {'class_name': 'RestfulApi', 'type': 'tool'}}
  流式输出: type='answer' index=0 payload={'output': '杭州今天的天气情况如下：\n\n- **天气**: 晴\n- **温度**: 32.93°C\n- **体感温度**: 35.6°C\n- **湿度**: 48%\n- **风速**: 3.21 m/s\n\n天气晴朗，温度较高，请注意防晒和补水！', 'result_type': 'answer'}
  >>> 
  >>> if __name__ == "__main__":
  ...     asyncio.run(run_test())
  ```

### add_tools

```python
add_tools(self, tools: List[Tool])
```

将工具绑定到ReActAgent中。

**参数**：

- **tools**(List[[Tool](../openjiuwen.core/utils/tool/tool.md#openjiuwencoreutilstooltool)])：需要绑定到ReActAgent的工具列表。

**样例**：

- 样例一：
  
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
  ...         description="天气查询插件",
  ...         params=[
  ...             Param(name="location", description="天气查询的地点，必须为英文", type="string", required=True),
  ...             Param(name="date", description="天气查询的时间，格式为YYYY-MM-DD", type="string", required=True),
  ...         ],
  ...         path="your path to weather service",
  ...         headers={},
  ...         method="GET",
  ...         response=[],
  ...     )
  ...     return weather_plugin
  >>> 
  >>> def _create_prompt_template():
  ...     system_prompt = "你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！今天的日期为：{}\n注意：1. 如果用户请求中未指定具体时间，则默认为今天。"
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
  ...     description="AI助手",
  ...     model=model_config,
  ...     prompt_template=prompt_template
  ... )
  >>> 
  >>> react_agent: ReActAgent = ReActAgent(react_agent_config)
  >>> # 绑定工具
  >>> react_agent.add_tools([_create_tool()])
  ```
- 样例二：
  
  ```python
  >>> # 使用LocalFunction本地函数工具的样例：除了RestfulApi，还可以使用LocalFunction将Python函数注册为工具。
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
  ...     """创建本地函数工具"""
  ...     add_tool = LocalFunction(
  ...         name="add",
  ...         description="加法",
  ...         params=[
  ...             Param(name="a", description="加数", type="number", required=True),
  ...             Param(name="b", description="被加数", type="number", required=True),
  ...         ],
  ...         func=lambda a, b: a + b
  ...     )
  ...     return add_tool
  >>> 
  >>> def _create_function_prompt_template():
  ...     system_prompt = "你是一个数学计算专家。"
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
  ...     description="AI计算助手",
  ...     model=model_config,
  ...     prompt_template=prompt_template
  ... )
  >>> 
  >>> react_agent: ReActAgent = ReActAgent(react_agent_config)
  >>> 
  >>> # 绑定本地函数工具
  >>> react_agent.add_tools([_create_function_tool()])
  >>> async def run_test():
  ...     result = await react_agent.invoke({"query": "计算1+2"})
  ...     print(f"ReActAgent 最终输出结果：{result}")
  ReActAgent 最终输出结果：{'output': '计算结果：1 + 2 = 12', 'result_type': 'answer'}
  >>> 
  >>> if __name__ == "__main__":
  ...     asyncio.run(run_test())
  ```
- 样例三：
  
  ```python
  >>> # 使用@tool装饰器的样例：使用@tool装饰器可以更简洁地将Python函数注册为工具。
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
  >>> # 使用@tool装饰器定义工具函数
  >>> @tool(
  ...     name="add",
  ...     description="加法",
  ...     params=[
  ...         Param(name="a", description="加数", type="number", required=True),
  ...         Param(name="b", description="被加数", type="number", required=True),
  ...     ]
  ... )
  >>> def add_function(a, b):
  ...     """加法函数，使用tool注解装饰"""
  ...     return a + b
  >>> 
  >>> def _create_function_prompt_template():
  ...     system_prompt = "你是一个数学计算专家。"
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
  ...     description="AI计算助手（使用注解）",
  ...     model=model_config,
  ...     prompt_template=prompt_template
  ... )
  >>> 
  >>> react_agent: ReActAgent = ReActAgent(react_agent_config)
  >>> 
  >>> # 绑定使用@tool装饰器创建的工具
  >>> react_agent.add_tools([add_function])
  >>> 
  >>> async def run_test():
  ...     result = await react_agent.invoke({"query": "计算1+2"})
  ...     print(f"ReActAgent 使用注解工具最终输出结果：{result}")
  ReActAgent 使用注解工具最终输出结果：{'output': '1 + 2 的计算结果是 3。', 'result_type': 'answer'}
  >>> 
  >>> if __name__ == "__main__":
  ...     asyncio.run(run_test())
  ```
