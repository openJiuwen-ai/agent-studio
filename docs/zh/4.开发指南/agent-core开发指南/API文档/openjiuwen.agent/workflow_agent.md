# openjiuwen.agent.workflow_agent

## class openjiuwen.agent.workflow_agent.WorkflowAgent

```python
openjiuwen.agent.workflow_agent.WorkflowAgent(agent_config: WorkflowAgentConfig)
```

WorkflowAgent是一种专注于多步骤、任务导向的流程自动化Agent，通过严格遵循用户预定义的任务流程高效地执行复杂任务。用户可预先设定清晰的任务步骤、执行条件及角色分工，将任务拆解为多个可执行的子任务或工具，并通过组件间的拓扑连接与数据传递，逐步推进整个工作流，最终输出预期结果。其侧重于基于预设流程实现任务的规范化与高效化执行，适用于任务结构清晰、可分解为多个步骤的场景。

**参数**：

- **agent_config**([WorkflowAgentConfig](config/workflow_config.md#class-openjiuwenagentconfigworkflow_configworkflowagentconfig))：WorkflowAgent的配置信息。

**样例**：

```python
>>> from openjiuwen.agent.common.schema import WorkflowSchema
>>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
>>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> 
>>> workflow_id = "test_weather_agent"
>>> workflow_name = "weather"
>>> workflow_version = "1.0"
>>> 
>>> workflow_config = WorkflowConfig(
...     metadata=WorkflowMetadata(
...         name=workflow_name,
...         id=workflow_id,
...         version=workflow_version,
...     )
... )
>>> flow = Workflow(workflow_config=workflow_config)
>>> 
>>> schema = WorkflowSchema(
...     id=workflow_id,
...     name=workflow_name,
...     description="天气查询工作流",
...     version=workflow_version,
...     inputs={"query": {"type": "string"}}
... )
>>> 
>>> config = WorkflowAgentConfig(
...     id="test_weather_agent",
...     version="0.1.0",
...     description="测试用天气 agent",
...     workflows=[schema],
... )
>>> 
>>> workflow_agent = WorkflowAgent(config)
```

### async invoke

```python
async invoke(self, inputs: Dict, runtime: Runtime = None) -> Dict
```

运行WorkflowAgent，执行整个工作流并返回结果。

**参数**：

- **inputs**(Dict)：WorkflowAgent的输入数据。支持的键包括：
  - **query**(str)：用户查询内容。
  - **conversation_id**(str, 可选)：会话ID，用于区分不同会话。默认值：`default_session`。
- **runtime(Runtime, 可选)**: Runtime（如果不提供，使用 BaseAgent 的 _runtime）

**返回**：

**Dict**，WorkflowAgent的最终输出结果。

**样例**：

- 样例一：
  
  ```python
  >>> import os
  >>> import asyncio
  >>> from datetime import datetime
  >>> from openjiuwen.agent.common.schema import WorkflowSchema
  >>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
  >>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
  >>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
  >>> from openjiuwen.core.component.end_comp import End
  >>> from openjiuwen.core.component.intent_detection_comp import IntentDetectionComponent, IntentDetectionCompConfig
  >>> from openjiuwen.core.component.llm_comp import LLMComponent, LLMCompConfig
  >>> from openjiuwen.core.component.questioner_comp import QuestionerComponent, QuestionerConfig, FieldInfo
  >>> from openjiuwen.core.component.start_comp import Start
  >>> from openjiuwen.core.component.tool_comp import ToolComponent, ToolComponentConfig
  >>> from openjiuwen.core.utils.llm.base import BaseModelInfo
  >>> from openjiuwen.core.utils.tool.param import Param
  >>> from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
  >>> from openjiuwen.core.workflow.base import Workflow
  >>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
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
  >>> def _create_model_config() -> ModelConfig:
  ...     return ModelConfig(
  ...         model_provider=MODEL_PROVIDER,
  ...         model_info=BaseModelInfo(
  ...             model=MODEL_NAME,
  ...             api_base=API_BASE,
  ...             api_key=API_KEY,
  ...             temperature=0.7,
  ...             top_p=0.9,
  ...             timeout=120,
  ...         ),
  ...     )
  >>> 
  >>> def _create_intent_detection_component() -> IntentDetectionComponent:
  ...     model_config = _create_model_config()
  ...     config = IntentDetectionCompConfig(
  ...         user_prompt="请判断用户意图",
  ...         category_name_list=["查询某地天气"],
  ...         model=model_config,
  ...     )
  ...     component = IntentDetectionComponent(config)
  ...     component.add_branch("${intent.classification_id} == 0", ["end"], "默认分支")
  ...     component.add_branch("${intent.classification_id} == 1", ["llm"], "查询天气分支")
  ...     return component
  >>> 
  >>> def _create_llm_component() -> LLMComponent:
  ...     model_config = _create_model_config()
  ...     current_date = build_current_date()
  ...     SYSTEM_PROMPT_TEMPLATE = "你是一个query改写的AI助手。今天的日期是{}。"
  ...     user_prompt = ("\n原始query为：{{query}}\n\n帮我改写原始query，要求：\n"
  ...                    "1. 只把地名改为英文，其他信息保留中文；\n"
  ...                    "2. 改写后的query必须包含当前的日期，默认日期为今天；\n"
  ...                    "3. 日期为YYYY-MM-DD格式。")
  ...     config = LLMCompConfig(
  ...         model=model_config,
  ...         template_content=[{"role": "user", "content": SYSTEM_PROMPT_TEMPLATE.format(current_date) + user_prompt}],
  ...         response_format={"type": "text"},
  ...         output_config={
  ...             "query": {"type": "string", "description": "改写后的query", "required": True}
  ...         },
  ...     )
  ...     return LLMComponent(config)
  >>> 
  >>> def _create_questioner_component() -> QuestionerComponent:
  ...     key_fields = [
  ...         FieldInfo(field_name="location", description="地点", required=True),
  ...         FieldInfo(field_name="date", description="时间", required=True, default_value="today"),
  ...     ]
  ...     model_config = _create_model_config()
  ...     config = QuestionerConfig(
  ...         model=model_config,
  ...         question_content="",
  ...         extract_fields_from_response=True,
  ...         field_names=key_fields,
  ...         with_chat_history=False,
  ...     )
  ...     return QuestionerComponent(config)
  >>> 
  >>> def _create_plugin_component() -> ToolComponent:
  ...     tool_config = ToolComponentConfig()
  ...     weather_tool = RestfulApi(
  ...         name="WeatherReporter",
  ...         description="天气查询插件",
  ...         params=[
  ...             Param(name="location", description="地点", type="string", required=True),
  ...             Param(name="date", description="日期", type="string", required=True),
  ...         ],
  ...         path="your path to weather service",
  ...         headers={},
  ...         method="GET",
  ...         response=[],
  ...     )
  ...     return ToolComponent(tool_config).bind_tool(weather_tool)
  >>> 
  >>> def _create_start_component():
  ...     return Start({"inputs": [{"id": "query", "type": "String", "required": "true", "sourceType": "ref"}]})
  >>> 
  >>> def _create_end_component():
  ...     return End({"responseTemplate": "{{output}}"})
  >>> 
  >>> def _create_workflow_schema(id, name: str, version: str) -> WorkflowSchema:
  ...     return WorkflowSchema(id=id,
  ...                           name=name,
  ...                           description="天气查询工作流",
  ...                           version=version,
  ...                           inputs={"query": {
  ...                               "type": "string",
  ...                           }})
  >>> 
  >>> # 构建工作流
  >>> workflow_id = "test_weather_agent"
  >>> workflow_version = "1.0"
  >>> workflow_name = "weather"
  >>> workflow_config = WorkflowConfig(
  ...     metadata=WorkflowMetadata(
  ...         name=workflow_name,
  ...         id=workflow_id,
  ...         version=workflow_version,
  ...     )
  ... )
  >>> flow = Workflow(workflow_config=workflow_config)
  >>> 
  >>> # 实例化各组件
  >>> start = _create_start_component()
  >>> intent = _create_intent_detection_component()
  >>> llm = _create_llm_component()
  >>> questioner = _create_questioner_component()
  >>> plugin = _create_plugin_component()
  >>> end = _create_end_component()
  >>> 
  >>> # 注册组件到工作流
  >>> flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
  >>> flow.add_workflow_comp("intent", intent, inputs_schema={"query": "${start.query}"})
  >>> flow.add_workflow_comp("llm", llm, inputs_schema={"query": "${start.query}"})
  >>> flow.add_workflow_comp("questioner", questioner, inputs_schema={"query": "${llm.query}"})
  >>> flow.add_workflow_comp("plugin", plugin, inputs_schema={
  ...     "location": "${questioner.location}",
  ...     "date": "${questioner.date}",
  ... })
  >>> flow.set_end_comp("end", end, inputs_schema={"output": "${plugin.data}"})
  >>> 
  >>> # 连接拓扑
  >>> flow.add_connection("start", "intent")
  >>> flow.add_connection("llm", "questioner")
  >>> flow.add_connection("questioner", "plugin")
  >>> flow.add_connection("plugin", "end")
  >>> 
  >>> # 创建WorkflowAgent
  >>> schema = _create_workflow_schema(workflow_id, workflow_name, workflow_version)
  >>> workflow_agent_config = WorkflowAgentConfig(
  ...     id="test_weather_agent",
  ...     version="0.1.0",
  ...     description="测试用天气 agent",
  ...     workflows=[schema]
  ... )
  >>> 
  >>> workflow_agent = WorkflowAgent(workflow_agent_config)
  >>> workflow_agent.bind_workflows([flow])
  >>> 
  >>> async def run_test():
  ...     result = await workflow_agent.invoke({"query": "查询上海的天气", "conversation_id": "c123"})
  ...     print(f"WorkflowAgent输出的最终结果：{result}")
  WorkflowAgent输出的最终结果：{'output': WorkflowOutput(result={'responseContent': "{'city': 'Shanghai', 'country': 'CN', 'feels_like': 28.89, 'humidity': 59, 'temperature': 27.68, 'weather': '晴', 'wind_speed': 4.13}"}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
  >>> 
  >>> if __name__ == "__main__":
  ...     asyncio.run(run_test())
  ```
- 样例二：
  
  ```python
  >>> # 中断恢复样例：当WorkflowAgent执行过程中遇到需要用户交互的场景（如追问），会返回交互请求。用户可以提供交互输入后继续执行。
  >>> import os
  >>> import asyncio
  >>> from typing import List
  >>> from openjiuwen.agent.common.schema import WorkflowSchema
  >>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
  >>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
  >>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
  >>> from openjiuwen.core.component.end_comp import End
  >>> from openjiuwen.core.component.intent_detection_comp import IntentDetectionComponent, IntentDetectionCompConfig
  >>> from openjiuwen.core.component.questioner_comp import QuestionerComponent, QuestionerConfig, FieldInfo
  >>> from openjiuwen.core.component.start_comp import Start
  >>> from openjiuwen.core.runtime.interaction.interactive_input import InteractiveInput
  >>> from openjiuwen.core.stream.writer import OutputSchema
  >>> from openjiuwen.core.utils.llm.base import BaseModelInfo
  >>> from openjiuwen.core.workflow.base import Workflow
  >>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
  >>> 
  >>> API_BASE = os.getenv("API_BASE", "your api base")
  >>> API_KEY = os.getenv("API_KEY", "your api key")
  >>> MODEL_NAME = os.getenv("MODEL_NAME", "")
  >>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
  >>> 
  >>> def _create_model_config() -> ModelConfig:
  ...     return ModelConfig(
  ...         model_provider=MODEL_PROVIDER,
  ...         model_info=BaseModelInfo(
  ...             model=MODEL_NAME,
  ...             api_base=API_BASE,
  ...             api_key=API_KEY,
  ...             temperature=0.7,
  ...             top_p=0.9,
  ...             timeout=120,
  ...         ),
  ...     )
  >>> 
  >>> def _create_intent_detection_component() -> IntentDetectionComponent:
  ...     model_config = _create_model_config()
  ...     config = IntentDetectionCompConfig(
  ...         user_prompt="请判断用户意图",
  ...         category_name_list=["查询某地天气"],
  ...         model=model_config,
  ...     )
  ...     component = IntentDetectionComponent(config)
  ...     component.add_branch("${intent.classification_id} == 0", ["end"], "默认分支")
  ...     component.add_branch("${intent.classification_id} == 1", ["questioner"], "查询天气分支")
  ...     return component
  >>> 
  >>> def _create_questioner_component() -> QuestionerComponent:
  ...     key_fields = [
  ...         FieldInfo(field_name="location", description="地点", required=True),
  ...         FieldInfo(field_name="date", description="时间", required=True, default_value="today"),
  ...     ]
  ...     model_config = _create_model_config()
  ...     config = QuestionerConfig(
  ...         model=model_config,
  ...         question_content="",
  ...         extract_fields_from_response=True,
  ...         field_names=key_fields,
  ...         with_chat_history=False,
  ...     )
  ...     return QuestionerComponent(config)
  >>> 
  >>> def _create_start_component():
  ...     return Start({"inputs": [{"id": "query", "type": "String", "required": "true", "sourceType": "ref"}]})
  >>> 
  >>> def _create_end_component():
  ...     return End({"responseTemplate": "{{output}}"})
  >>> 
  >>> def _create_workflow_schema(id, name: str, version: str) -> WorkflowSchema:
  ...     return WorkflowSchema(id=id,
  ...                           name=name,
  ...                           description="天气查询工作流",
  ...                           version=version,
  ...                           inputs={"query": {"type": "string"}})
  >>> 
  >>> # 构建包含交互式组件的工作流
  >>> workflow_id = "test_interrupt_workflow"
  >>> workflow_version = "1.0"
  >>> workflow_name = "interrupt_test"
  >>> workflow_config = WorkflowConfig(
  ...     metadata=WorkflowMetadata(
  ...         name=workflow_name,
  ...         id=workflow_id,
  ...         version=workflow_version,
  ...     )
  ... )
  >>> flow = Workflow(workflow_config=workflow_config)
  >>> 
  >>> # 实例化各组件
  >>> start = _create_start_component()
  >>> intent = _create_intent_detection_component()
  >>> questioner = _create_questioner_component()
  >>> end = _create_end_component()
  >>> 
  >>> # 注册组件到工作流
  >>> flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
  >>> flow.add_workflow_comp("intent", intent, inputs_schema={"query": "${start.query}"})
  >>> flow.add_workflow_comp("questioner", questioner, inputs_schema={"query": "${start.query}"})
  >>> flow.set_end_comp("end", end, inputs_schema={"output": "${questioner.location}"})
  >>> 
  >>> # 连接拓扑
  >>> flow.add_connection("start", "intent")
  >>> flow.add_connection("intent", "questioner")
  >>> flow.add_connection("questioner", "end")
  >>> 
  >>> # 创建WorkflowAgent
  >>> schema = _create_workflow_schema(workflow_id, workflow_name, workflow_version)
  >>> workflow_agent_config = WorkflowAgentConfig(
  ...     id="test_interrupt_agent",
  ...     version="0.1.0",
  ...     description="测试中断恢复的 agent",
  ...     workflows=[schema]
  ... )
  >>> 
  >>> workflow_agent = WorkflowAgent(workflow_agent_config)
  >>> workflow_agent.bind_workflows([flow])
  >>> 
  >>> async def run_test():
  ...     # 第一次调用 - 应该触发中断
  ...     result = await workflow_agent.invoke({"query": "查询天气", "conversation_id": "c123"})
  ...     print(f"WorkflowAgent第一次输出结果 >>>  {result}")
  WorkflowAgent第一次输出结果 >>> [OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='请您提供地点相关的信息'))]
  ... 
  ...     # 检测交互请求
  ...     if isinstance(result, List) and isinstance(result[0], OutputSchema) and result[0].type == '__interaction__':
  ...         print("检测到交互请求，准备进行中断恢复...")
  检测到交互请求，准备进行中断恢复...
  ...         interactive_input = InteractiveInput()
  ...         for item in result:
  ...             component_id = item.payload.id
  ...             interactive_input.update(component_id, "上海")
  ... 
  ...         # 第二次调用 - 使用InteractiveInput进行恢复
  ...         result = await workflow_agent.invoke({"query": interactive_input, "conversation_id": "c123"})
  ...         print(f"WorkflowAgent中断恢复后输出结果 >>>  {result}")
  WorkflowAgent中断恢复后输出结果 >>> {'output': WorkflowOutput(result={'responseContent': '上海'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
  >>> 
  >>> if __name__ == "__main__":
  ...     asyncio.run(run_test())
  ```

### async stream

```python
async stream(self, inputs: Dict, runtime: Runtime = None) -> AsyncIterator[Any]
```

以流式方式运行WorkflowAgent，逐步返回中间结果。

**参数**：

- **inputs**(Dict)：WorkflowAgent的输入数据。支持的键包括：
  - **query**(str)：用户查询内容。
  - **conversation_id**(str, 可选)：会话ID，用于区分不同会话，默认为`default_session`。
- **runtime(Runtime, 可选)**: Runtime（如果不提供，使用 BaseAgent 的 _runtime）

**返回**：

**AsyncIterator[Any]**，异步迭代器，返回数据流的迭代器，用于支持流式输出，包括`BaseMessageChunk`等类型的数据流。

**样例**：

- 样例一：
  
  ```python
  >>> import os
  >>> import asyncio
  >>> from datetime import datetime
  >>> from openjiuwen.agent.common.schema import WorkflowSchema
  >>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
  >>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
  >>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
  >>> from openjiuwen.core.component.end_comp import End
  >>> from openjiuwen.core.component.intent_detection_comp import IntentDetectionComponent, IntentDetectionCompConfig
  >>> from openjiuwen.core.component.llm_comp import LLMComponent, LLMCompConfig
  >>> from openjiuwen.core.component.questioner_comp import QuestionerComponent, QuestionerConfig, FieldInfo
  >>> from openjiuwen.core.component.start_comp import Start
  >>> from openjiuwen.core.component.tool_comp import ToolComponent, ToolComponentConfig
  >>> from openjiuwen.core.utils.llm.base import BaseModelInfo
  >>> from openjiuwen.core.utils.tool.param import Param
  >>> from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
  >>> from openjiuwen.core.workflow.base import Workflow
  >>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
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
  >>> def _create_model_config() -> ModelConfig:
  ...     return ModelConfig(
  ...         model_provider=MODEL_PROVIDER,
  ...         model_info=BaseModelInfo(
  ...             model=MODEL_NAME,
  ...             api_base=API_BASE,
  ...             api_key=API_KEY,
  ...             temperature=0.7,
  ...             top_p=0.9,
  ...             timeout=120,
  ...         ),
  ...     )
  >>> 
  >>> def _create_intent_detection_component() -> IntentDetectionComponent:
  ...     model_config = _create_model_config()
  ...     config = IntentDetectionCompConfig(
  ...         user_prompt="请判断用户意图",
  ...         category_name_list=["查询某地天气"],
  ...         model=model_config,
  ...     )
  ...     component = IntentDetectionComponent(config)
  ...     component.add_branch("${intent.classification_id} == 0", ["end"], "默认分支")
  ...     component.add_branch("${intent.classification_id} == 1", ["llm"], "查询天气分支")
  ...     return component
  >>> 
  >>> def _create_llm_component() -> LLMComponent:
  ...     model_config = _create_model_config()
  ...     current_date = build_current_date()
  ...     SYSTEM_PROMPT_TEMPLATE = "你是一个query改写的AI助手。今天的日期是{}。"
  ...     user_prompt = ("\n原始query为：{{query}}\n\n帮我改写原始query，要求：\n"
  ...                    "1. 只把地名改为英文，其他信息保留中文；\n"
  ...                    "2. 改写后的query必须包含当前的日期，默认日期为今天；\n"
  ...                    "3. 日期为YYYY-MM-DD格式。")
  ...     config = LLMCompConfig(
  ...         model=model_config,
  ...         template_content=[{"role": "user", "content": SYSTEM_PROMPT_TEMPLATE.format(current_date) + user_prompt}],
  ...         response_format={"type": "text"},
  ...         output_config={
  ...             "query": {"type": "string", "description": "改写后的query", "required": True}
  ...         },
  ...     )
  ...     return LLMComponent(config)
  >>> 
  >>> def _create_questioner_component() -> QuestionerComponent:
  ...     key_fields = [
  ...         FieldInfo(field_name="location", description="地点", required=True),
  ...         FieldInfo(field_name="date", description="时间", required=True, default_value="today"),
  ...     ]
  ...     model_config = _create_model_config()
  ...     config = QuestionerConfig(
  ...         model=model_config,
  ...         question_content="",
  ...         extract_fields_from_response=True,
  ...         field_names=key_fields,
  ...         with_chat_history=False,
  ...     )
  ...     return QuestionerComponent(config)
  >>> 
  >>> def _create_plugin_component() -> ToolComponent:
  ...     tool_config = ToolComponentConfig()
  ...     weather_tool = RestfulApi(
  ...         name="WeatherReporter",
  ...         description="天气查询插件",
  ...         params=[
  ...             Param(name="location", description="地点", type="string", required=True),
  ...             Param(name="date", description="日期", type="string", required=True),
  ...         ],
  ...         path="your path to weather service",
  ...         headers={},
  ...         method="GET",
  ...         response=[],
  ...     )
  ...     return ToolComponent(tool_config).bind_tool(weather_tool)
  >>> 
  >>> def _create_start_component():
  ...     return Start({"inputs": [{"id": "query", "type": "String", "required": "true", "sourceType": "ref"}]})
  >>> 
  >>> def _create_end_component():
  ...     return End({"responseTemplate": "{{output}}"})
  >>> 
  >>> def _create_workflow_schema(id, name: str, version: str) -> WorkflowSchema:
  ...     return WorkflowSchema(id=id,
  ...                           name=name,
  ...                           description="天气查询工作流",
  ...                           version=version,
  ...                           inputs={"query": {
  ...                               "type": "string",
  ...                           }})
  >>> 
  >>> # 构建工作流
  >>> workflow_id = "test_weather_agent"
  >>> workflow_version = "1.0"
  >>> workflow_name = "weather"
  >>> workflow_config = WorkflowConfig(
  ...     metadata=WorkflowMetadata(
  ...         name=workflow_name,
  ...         id=workflow_id,
  ...         version=workflow_version,
  ...     )
  ... )
  >>> flow = Workflow(workflow_config=workflow_config)
  >>> 
  >>> # 实例化各组件
  >>> start = _create_start_component()
  >>> intent = _create_intent_detection_component()
  >>> llm = _create_llm_component()
  >>> questioner = _create_questioner_component()
  >>> plugin = _create_plugin_component()
  >>> end = _create_end_component()
  >>> 
  >>> # 注册组件到工作流
  >>> flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
  >>> flow.add_workflow_comp("intent", intent, inputs_schema={"query": "${start.query}"})
  >>> flow.add_workflow_comp("llm", llm, inputs_schema={"query": "${start.query}"})
  >>> flow.add_workflow_comp("questioner", questioner, inputs_schema={"query": "${llm.query}"})
  >>> flow.add_workflow_comp("plugin", plugin, inputs_schema={
  ...     "location": "${questioner.location}",
  ...     "date": "${questioner.date}",
  ... })
  >>> flow.set_end_comp("end", end, inputs_schema={"output": "${plugin.data}"})
  >>> 
  >>> # 连接拓扑
  >>> flow.add_connection("start", "intent")
  >>> flow.add_connection("llm", "questioner")
  >>> flow.add_connection("questioner", "plugin")
  >>> flow.add_connection("plugin", "end")
  >>> 
  >>> # 创建WorkflowAgent
  >>> schema = _create_workflow_schema(workflow_id, workflow_name, workflow_version)
  >>> workflow_agent_config = WorkflowAgentConfig(
  ...     id="test_weather_agent",
  ...     version="0.1.0",
  ...     description="测试用天气 agent",
  ...     workflows=[schema]
  ... )
  >>> 
  >>> workflow_agent = WorkflowAgent(workflow_agent_config)
  >>> workflow_agent.bind_workflows([flow])
  >>> 
  >>> async def run_test():
  ...     async for chunk in workflow_agent.stream({"query": "查询上海的天气", "conversation_id": "c123"}):
  ...         print(f"流式输出: {chunk}")
  流式输出: type='tracer_workflow' payload={'traceId': '05354dbc-dab6-49aa-b7ca-b255180b6559', 'startTime': datetime.datetime(2025, 10, 10, 16, 46, 2, 444639), 'endTime': datetime.datetime(2025, 10, 10, 16, 46, 2, 445668), 'inputs': {'output': {'city': 'Shanghai', 'country': 'CN', 'feels_like': 28.82, 'humidity': 59, 'temperature': 27.63, 'weather': '晴', 'wind_speed': 4.13}}, 'outputs': {'responseContent': "{'city': 'Shanghai', 'country': 'CN', 'feels_like': 28.82, 'humidity': 59, 'temperature': 27.63, 'weather': '晴', 'wind_speed': 4.13}"}, 'error': None, 'invokeId': 'end', 'parentInvokeId': 'plugin', 'executionId': '05354dbc-dab6-49aa-b7ca-b255180b6559', 'conversationId': '', 'onInvokeData': [], 'agentId': '', 'componentId': '', 'componentName': '', 'componentType': 'end', 'agentParentInvokeId': '', 'metaData': '{"component_id": "", "component_name": "", "component_type": "end"}', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
  >>> 
  >>> if __name__ == "__main__":
  ...     asyncio.run(run_test())
  ```
- 样例二：
  
  ```python
  >>> # 中断恢复样例：当WorkflowAgent执行过程中遇到需要用户交互的场景（如追问），流式输出会返回交互请求。用户可以提供交互输入后继续执行。
  >>> import os
  >>> import asyncio
  >>> from datetime import datetime
  >>> from openjiuwen.agent.common.schema import WorkflowSchema
  >>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
  >>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
  >>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
  >>> from openjiuwen.core.component.end_comp import End
  >>> from openjiuwen.core.component.intent_detection_comp import IntentDetectionComponent, IntentDetectionCompConfig
  >>> from openjiuwen.core.component.questioner_comp import QuestionerComponent, QuestionerConfig, FieldInfo
  >>> from openjiuwen.core.component.start_comp import Start
  >>> from openjiuwen.core.runtime.interaction.interactive_input import InteractiveInput
  >>> from openjiuwen.core.stream.writer import OutputSchema
  >>> from openjiuwen.core.utils.llm.base import BaseModelInfo
  >>> from openjiuwen.core.workflow.base import Workflow
  >>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
  >>> 
  >>> API_BASE = os.getenv("API_BASE", "your api base")
  >>> API_KEY = os.getenv("API_KEY", "your api key")
  >>> MODEL_NAME = os.getenv("MODEL_NAME", "")
  >>> MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "")
  >>> 
  >>> def _create_model_config() -> ModelConfig:
  ...     return ModelConfig(
  ...         model_provider=MODEL_PROVIDER,
  ...         model_info=BaseModelInfo(
  ...             model=MODEL_NAME,
  ...             api_base=API_BASE,
  ...             api_key=API_KEY,
  ...             temperature=0.7,
  ...             top_p=0.9,
  ...             timeout=120,
  ...         ),
  ...     )
  ... 
  >>> def _create_intent_detection_component() -> IntentDetectionComponent:
  ...     model_config = _create_model_config()
  ...     config = IntentDetectionCompConfig(
  ...         user_prompt="请判断用户意图",
  ...         category_name_list=["查询某地天气"],
  ...         model=model_config,
  ...     )
  ...     component = IntentDetectionComponent(config)
  ...     component.add_branch("${intent.classification_id} == 0", ["end"], "默认分支")
  ...     component.add_branch("${intent.classification_id} == 1", ["questioner"], "查询天气分支")
  ...     return component
  >>> 
  >>> def _create_questioner_component() -> QuestionerComponent:
  ...     key_fields = [
  ...         FieldInfo(field_name="location", description="地点", required=True),
  ...         FieldInfo(field_name="date", description="时间", required=True, default_value="today"),
  ...     ]
  ...     model_config = _create_model_config()
  ...     config = QuestionerConfig(
  ...         model=model_config,
  ...         question_content="",
  ...         extract_fields_from_response=True,
  ...         field_names=key_fields,
  ...         with_chat_history=False,
  ...     )
  ...     return QuestionerComponent(config)
  >>> 
  >>> def _create_start_component():
  ...     return Start({"inputs": [{"id": "query", "type": "String", "required": "true", "sourceType": "ref"}]})
  >>> 
  >>> def _create_end_component():
  ...     return End({"responseTemplate": "{{output}}"})
  >>> 
  >>> def _create_workflow_schema(id, name: str, version: str) -> WorkflowSchema:
  ...     return WorkflowSchema(id=id,
  ...                           name=name,
  ...                           description="天气查询工作流",
  ...                           version=version,
  ...                           inputs={"query": {"type": "string"}})
  >>> 
  >>> # 构建包含交互式组件的工作流
  >>> workflow_id = "test_interrupt_workflow"
  >>> workflow_version = "1.0"
  >>> workflow_name = "interrupt_test"
  >>> workflow_config = WorkflowConfig(
  ...     metadata=WorkflowMetadata(
  ...         name=workflow_name,
  ...         id=workflow_id,
  ...         version=workflow_version,
  ...     )
  ... )
  >>> flow = Workflow(workflow_config=workflow_config)
  >>> 
  >>> # 实例化各组件
  >>> start = _create_start_component()
  >>> intent = _create_intent_detection_component()
  >>> questioner = _create_questioner_component()
  >>> end = _create_end_component()
  >>> 
  >>> # 注册组件到工作流
  >>> flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
  >>> flow.add_workflow_comp("intent", intent, inputs_schema={"query": "${start.query}"})
  >>> flow.add_workflow_comp("questioner", questioner, inputs_schema={"query": "${start.query}"})
  >>> flow.set_end_comp("end", end, inputs_schema={"output": "${questioner.location}"})
  >>> 
  >>> # 连接拓扑
  >>> flow.add_connection("start", "intent")
  >>> flow.add_connection("intent", "questioner")
  >>> flow.add_connection("questioner", "end")
  >>> 
  >>> # 创建WorkflowAgent
  >>> schema = _create_workflow_schema(workflow_id, workflow_name, workflow_version)
  >>> workflow_agent_config = WorkflowAgentConfig(
  ...     id="test_interrupt_agent",
  ...     version="0.1.0",
  ...     description="测试中断恢复的 agent",
  ...     workflows=[schema]
  ... )
  >>> 
  >>> workflow_agent = WorkflowAgent(workflow_agent_config)
  >>> workflow_agent.bind_workflows([flow])
  >>> 
  >>> async def run_test():
  ...     # 第一次流式调用 - 应该触发中断
  ...     interaction_outputs = []
  ...     async for chunk in workflow_agent.stream({"query": "查询天气", "conversation_id": "c123"}):
  ...         print(f"WorkflowAgent第一次输出结果 >>>  {chunk}")
  WorkflowAgent第一次输出结果 >>> type='__interaction__' index=0 payload=InteractionOutput(id='questioner', value='请您提供地点相关的信息')
  ...         if isinstance(chunk, OutputSchema) and chunk.type == "__interaction__":
  ...             print("✅ stream 检测到交互请求!")
  ✅ stream 检测到交互请求!
  ...             interaction_outputs.append(chunk)
  ... 
  ...     # 如果有交互请求，则提供用户输入后继续流式执行
  ...     if interaction_outputs:
  ...         print("检测到交互请求，准备进行中断恢复...")
  检测到交互请求，准备进行中断恢复...
  ...         interactive_input = InteractiveInput()
  ...         for item in interaction_outputs:
  ...             component_id = item.payload.id
  ...             interactive_input.update(component_id, "上海")
  ... 
  ...         # 第二次流式调用 - 使用InteractiveInput进行恢复
  ...         async for chunk in workflow_agent.stream({"query": interactive_input, "conversation_id": "c123"}):
  ...             print(f"WorkflowAgent中断恢复后输出结果 >>>  {chunk}")
  WorkflowAgent中断恢复后输出结果 >>> type='tracer_workflow' payload={'traceId': 'b828c79d-d546-44cf-a7e2-3d3488f9713e', 'startTime': datetime.datetime(2025, 10, 10, 16, 51, 46, 545213), 'endTime': datetime.datetime(2025, 10, 10, 16, 51, 46, 545587), 'inputs': {'output': '上海'}, 'outputs': {'responseContent': '上海'}, 'error': None, 'invokeId': 'end', 'parentInvokeId': 'questioner', 'executionId': 'b828c79d-d546-44cf-a7e2-3d3488f9713e', 'conversationId': '', 'onInvokeData': [], 'agentId': '', 'componentId': '', 'componentName': '', 'componentType': 'end', 'agentParentInvokeId': '', 'metaData': '{"component_id": "", "component_name": "", "component_type": "end"}', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
  >>> 
  >>> if __name__ == "__main__":
  ...     asyncio.run(run_test())
  ```

### bind_workflows

```python
bind_workflows(self, workflows: List[Workflow])
```

将工作流绑定到WorkflowAgent中。

**参数**：

- **workflows**(List[[Workflow](../openjiuwen.core/workflow/base.md#class-openjiuwencoreworkflowbaseworkflow)])：需要绑定到WorkflowAgent的工作流列表。

**样例**：

```python
>>> import os
>>> from openjiuwen.agent.common.schema import WorkflowSchema
>>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
>>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> 
>>> def _create_start_component():
...   return Start({"inputs": [{"id": "query", "type": "String", "required": "true", "sourceType": "ref"}]})
>>> 
>>> def _create_end_component():
...   return End({"responseTemplate": "{{output}}"})
>>> 
>>> def _create_workflow_schema(id, name: str, version: str) -> WorkflowSchema:
...   return WorkflowSchema(id=id,
...                         name=name,
...                         description="天气查询工作流",
...                         version=version,
...                         inputs={"query": {"type": "string"}})
>>> 
>>> # 构建工作流
>>> workflow_id = "test_weather_agent"
>>> workflow_version = "1.0"
>>> workflow_name = "weather"
>>> workflow_config = WorkflowConfig(
...   metadata=WorkflowMetadata(
...       name=workflow_name,
...       id=workflow_id,
...       version=workflow_version,
...   )
... )
>>> flow = Workflow(workflow_config=workflow_config)
>>> 
>>> # 实例化各组件
>>> start = _create_start_component()
>>> end = _create_end_component()
>>> 
>>> # 注册组件到工作流
>>> flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
>>> flow.set_end_comp("end", end, inputs_schema={"output": "${start.query}"})
>>> 
>>> # 连接拓扑
>>> flow.add_connection("start", "end")
>>> 
>>> # 创建WorkflowAgent
>>> schema = _create_workflow_schema(workflow_id, workflow_name, workflow_version)
>>> workflow_agent_config = WorkflowAgentConfig(
...   id="test_weather_agent",
...   version="0.1.0",
...   description="测试用天气 agent",
...   workflows=[schema]
... )
>>> 
>>> workflow_agent = WorkflowAgent(workflow_agent_config)
>>> 
>>> # 绑定工作流
>>> workflow_agent.add_workflows([flow])
```
