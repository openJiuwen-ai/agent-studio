# `openjiuwen.agent.workflow_agent`

## class `openjiuwen.agent.workflow_agent.WorkflowAgent`

```python
openjiuwen.agent.workflow_agent.WorkflowAgent(agent_config: WorkflowAgentConfig)
```

`WorkflowAgent` is an Agent designed for multi-step, task-oriented workflow automation. It efficiently executes complex tasks by strictly following a user-defined workflow. Users can define clear steps, execution conditions, and role assignments in advance—breaking a task into multiple executable subtasks or tools—and then advance the workflow step by step through topological connections and data passing between components, ultimately producing the expected result. It emphasizes standardizing and improving efficiency by executing predefined processes, and is suitable for scenarios where the task structure is clear and can be decomposed into multiple steps.

**Parameters**:

* **agent_config** ([WorkflowAgentConfig](config/workflow_config.md#class-openjiuwenagentconfigworkflow_configworkflowagentconfig)): Configuration information for the `WorkflowAgent`.

**Example**:

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
...     description="Weather query workflow",
...     version=workflow_version,
...     inputs={"query": {"type": "string"}}
... )
>>> 
>>> config = WorkflowAgentConfig(
...     id="test_weather_agent",
...     version="0.1.0",
...     description="Test weather agent",
...     workflows=[schema],
... )
>>> 
>>> workflow_agent = WorkflowAgent(config)
```

---

### async `invoke`

```python
async invoke(self, inputs: Dict, runtime: Runtime = None) -> Dict
```

Runs the `WorkflowAgent`, executes the entire workflow, and returns the result.

**Parameters**:

* **inputs** (Dict): Input data for the `WorkflowAgent`. Supported keys include:

  * **query** (str): The user query.
  * **conversation_id** (str, optional): Session ID used to distinguish different conversations. Default: `default_session`.
* **runtime** (Runtime, optional): Runtime (if not provided, uses `BaseAgent`’s `_runtime`).

**Returns**:

* **Dict**: The final output result from the `WorkflowAgent`.

**Examples**:

* Example 1:

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
  ...         user_prompt="Please determine the user's intent",
  ...         category_name_list=["Query the weather for a location"],
  ...         model=model_config,
  ...     )
  ...     component = IntentDetectionComponent(config)
  ...     component.add_branch("${intent.classification_id} == 0", ["end"], "Default branch")
  ...     component.add_branch("${intent.classification_id} == 1", ["llm"], "Weather query branch")
  ...     return component
  >>> 
  >>> def _create_llm_component() -> LLMComponent:
  ...     model_config = _create_model_config()
  ...     current_date = build_current_date()
  ...     SYSTEM_PROMPT_TEMPLATE = "You are an AI assistant for rewriting queries. Today's date is {}."
  ...     user_prompt = ("\nOriginal query: {{query}}\n\nRewrite the original query with these requirements:\n"
  ...                    "1. Only translate place names into English; keep other content in Chinese;\n"
  ...                    "2. The rewritten query must include the current date; default date is today;\n"
  ...                    "3. Date format must be YYYY-MM-DD.")
  ...     config = LLMCompConfig(
  ...         model=model_config,
  ...         template_content=[{"role": "user", "content": SYSTEM_PROMPT_TEMPLATE.format(current_date) + user_prompt}],
  ...         response_format={"type": "text"},
  ...         output_config={
  ...             "query": {"type": "string", "description": "Rewritten query", "required": True}
  ...         },
  ...     )
  ...     return LLMComponent(config)
  >>> 
  >>> def _create_questioner_component() -> QuestionerComponent:
  ...     key_fields = [
  ...         FieldInfo(field_name="location", description="Location", required=True),
  ...         FieldInfo(field_name="date", description="Date", required=True, default_value="today"),
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
  ...         description="Weather query plugin",
  ...         params=[
  ...             Param(name="location", description="Location", type="string", required=True),
  ...             Param(name="date", description="Date", type="string", required=True),
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
  ...                           description="Weather query workflow",
  ...                           version=version,
  ...                           inputs={"query": {
  ...                               "type": "string",
  ...                           }})
  >>> 
  >>> # Build workflow
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
  >>> # Instantiate components
  >>> start = _create_start_component()
  >>> intent = _create_intent_detection_component()
  >>> llm = _create_llm_component()
  >>> questioner = _create_questioner_component()
  >>> plugin = _create_plugin_component()
  >>> end = _create_end_component()
  >>> 
  >>> # Register components to workflow
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
  >>> # Connect topology
  >>> flow.add_connection("start", "intent")
  >>> flow.add_connection("llm", "questioner")
  >>> flow.add_connection("questioner", "plugin")
  >>> flow.add_connection("plugin", "end")
  >>> 
  >>> # Create WorkflowAgent
  >>> schema = _create_workflow_schema(workflow_id, workflow_name, workflow_version)
  >>> workflow_agent_config = WorkflowAgentConfig(
  ...     id="test_weather_agent",
  ...     version="0.1.0",
  ...     description="Test weather agent",
  ...     workflows=[schema]
  ... )
  >>> 
  >>> workflow_agent = WorkflowAgent(workflow_agent_config)
  >>> workflow_agent.bind_workflows([flow])
  >>> 
  >>> async def run_test():
  ...     result = await workflow_agent.invoke({"query": "Query Shanghai weather", "conversation_id": "c123"})
  ...     print(f"Final output from WorkflowAgent: {result}")
  Final output from WorkflowAgent: {'output': WorkflowOutput(result={'responseContent': "{'city': 'Shanghai', 'country': 'CN', 'feels_like': 28.89, 'humidity': 59, 'temperature': 27.68, 'weather': 'Sunny', 'wind_speed': 4.13}"}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
  >>> 
  >>> if __name__ == "__main__":
  ...     asyncio.run(run_test())
  ```

* Example 2:

  ```python
  >>> # Interrupt/resume example: if the WorkflowAgent encounters a scenario requiring user interaction (e.g., a follow-up question),
  >>> # it will return an interaction request. The user can provide interactive input and continue execution.
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
  ...         user_prompt="Please determine the user's intent",
  ...         category_name_list=["Query the weather for a location"],
  ...         model=model_config,
  ...     )
  ...     component = IntentDetectionComponent(config)
  ...     component.add_branch("${intent.classification_id} == 0", ["end"], "Default branch")
  ...     component.add_branch("${intent.classification_id} == 1", ["questioner"], "Weather query branch")
  ...     return component
  >>> 
  >>> def _create_questioner_component() -> QuestionerComponent:
  ...     key_fields = [
  ...         FieldInfo(field_name="location", description="Location", required=True),
  ...         FieldInfo(field_name="date", description="Date", required=True, default_value="today"),
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
  ...                           description="Weather query workflow",
  ...                           version=version,
  ...                           inputs={"query": {"type": "string"}})
  >>> 
  >>> # Build an interactive workflow
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
  >>> # Instantiate components
  >>> start = _create_start_component()
  >>> intent = _create_intent_detection_component()
  >>> questioner = _create_questioner_component()
  >>> end = _create_end_component()
  >>> 
  >>> # Register components to workflow
  >>> flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
  >>> flow.add_workflow_comp("intent", intent, inputs_schema={"query": "${start.query}"})
  >>> flow.add_workflow_comp("questioner", questioner, inputs_schema={"query": "${start.query}"})
  >>> flow.set_end_comp("end", end, inputs_schema={"output": "${questioner.location}"})
  >>> 
  >>> # Connect topology
  >>> flow.add_connection("start", "intent")
  >>> flow.add_connection("intent", "questioner")
  >>> flow.add_connection("questioner", "end")
  >>> 
  >>> # Create WorkflowAgent
  >>> schema = _create_workflow_schema(workflow_id, workflow_name, workflow_version)
  >>> workflow_agent_config = WorkflowAgentConfig(
  ...     id="test_interrupt_agent",
  ...     version="0.1.0",
  ...     description="Test interrupt/resume agent",
  ...     workflows=[schema]
  ... )
  >>> 
  >>> workflow_agent = WorkflowAgent(workflow_agent_config)
  >>> workflow_agent.bind_workflows([flow])
  >>> 
  >>> async def run_test():
  ...     # First call - should trigger an interruption
  ...     result = await workflow_agent.invoke({"query": "Query the weather", "conversation_id": "c123"})
  ...     print(f"WorkflowAgent first output >>>  {result}")
  WorkflowAgent first output >>> [OutputSchema(type='__interaction__', index=0, payload=InteractionOutput(id='questioner', value='Please provide location information'))]
  ... 
  ...     # Detect interaction request
  ...     if isinstance(result, List) and isinstance(result[0], OutputSchema) and result[0].type == '__interaction__':
  ...         print("Interaction request detected, preparing to resume...")
  ...         interactive_input = InteractiveInput()
  ...         for item in result:
  ...             component_id = item.payload.id
  ...             interactive_input.update(component_id, "Shanghai")
  ... 
  ...         # Second call - resume with InteractiveInput
  ...         result = await workflow_agent.invoke({"query": interactive_input, "conversation_id": "c123"})
  ...         print(f"WorkflowAgent output after resume >>>  {result}")
  WorkflowAgent output after resume >>> {'output': WorkflowOutput(result={'responseContent': 'Shanghai'}, state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>), 'result_type': 'answer'}
  >>> 
  >>> if __name__ == "__main__":
  ...     asyncio.run(run_test())
  ```

---

### async `stream`

```python
async stream(self, inputs: Dict, runtime: Runtime = None) -> AsyncIterator[Any]
```

Runs the `WorkflowAgent` in streaming mode and returns intermediate results progressively.

**Parameters**:

* **inputs** (Dict): Input data for the `WorkflowAgent`. Supported keys include:

  * **query** (str): The user query.
  * **conversation_id** (str, optional): Session ID used to distinguish different conversations. Default: `default_session`.
* **runtime** (Runtime, optional): Runtime (if not provided, uses `BaseAgent`’s `_runtime`).

**Returns**:

* **AsyncIterator[Any]**: An async iterator that yields a stream of results, supporting streaming output such as `BaseMessageChunk`.

**Examples**:

* Example 1:

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
  ...         user_prompt="Please determine the user's intent",
  ...         category_name_list=["Query the weather for a location"],
  ...         model=model_config,
  ...     )
  ...     component = IntentDetectionComponent(config)
  ...     component.add_branch("${intent.classification_id} == 0", ["end"], "Default branch")
  ...     component.add_branch("${intent.classification_id} == 1", ["llm"], "Weather query branch")
  ...     return component
  >>> 
  >>> def _create_llm_component() -> LLMComponent:
  ...     model_config = _create_model_config()
  ...     current_date = build_current_date()
  ...     SYSTEM_PROMPT_TEMPLATE = "You are an AI assistant for rewriting queries. Today's date is {}."
  ...     user_prompt = ("\nOriginal query: {{query}}\n\nRewrite the original query with these requirements:\n"
  ...                    "1. Only translate place names into English; keep other content in Chinese;\n"
  ...                    "2. The rewritten query must include the current date; default date is today;\n"
  ...                    "3. Date format must be YYYY-MM-DD.")
  ...     config = LLMCompConfig(
  ...         model=model_config,
  ...         template_content=[{"role": "user", "content": SYSTEM_PROMPT_TEMPLATE.format(current_date) + user_prompt}],
  ...         response_format={"type": "text"},
  ...         output_config={
  ...             "query": {"type": "string", "description": "Rewritten query", "required": True}
  ...         },
  ...     )
  ...     return LLMComponent(config)
  >>> 
  >>> def _create_questioner_component() -> QuestionerComponent:
  ...     key_fields = [
  ...         FieldInfo(field_name="location", description="Location", required=True),
  ...         FieldInfo(field_name="date", description="Date", required=True, default_value="today"),
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
  ...         description="Weather query plugin",
  ...         params=[
  ...             Param(name="location", description="Location", type="string", required=True),
  ...             Param(name="date", description="Date", type="string", required=True),
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
  ...                           description="Weather query workflow",
  ...                           version=version,
  ...                           inputs={"query": {
  ...                               "type": "string",
  ...                           }})
  >>> 
  >>> # Build workflow
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
  >>> # Instantiate components
  >>> start = _create_start_component()
  >>> intent = _create_intent_detection_component()
  >>> llm = _create_llm_component()
  >>> questioner = _create_questioner_component()
  >>> plugin = _create_plugin_component()
  >>> end = _create_end_component()
  >>> 
  >>> # Register components to workflow
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
  >>> # Connect topology
  >>> flow.add_connection("start", "intent")
  >>> flow.add_connection("llm", "questioner")
  >>> flow.add_connection("questioner", "plugin")
  >>> flow.add_connection("plugin", "end")
  >>> 
  >>> # Create WorkflowAgent
  >>> schema = _create_workflow_schema(workflow_id, workflow_name, workflow_version)
  >>> workflow_agent_config = WorkflowAgentConfig(
  ...     id="test_weather_agent",
  ...     version="0.1.0",
  ...     description="Test weather agent",
  ...     workflows=[schema]
  ... )
  >>> 
  >>> workflow_agent = WorkflowAgent(workflow_agent_config)
  >>> workflow_agent.bind_workflows([flow])
  >>> 
  >>> async def run_test():
  ...     async for chunk in workflow_agent.stream({"query": "Query Shanghai weather", "conversation_id": "c123"}):
  ...         print(f"Streaming output: {chunk}")
  Streaming output: type='tracer_workflow' payload={'traceId': '05354dbc-dab6-49aa-b7ca-b255180b6559', 'startTime': datetime.datetime(2025, 10, 10, 16, 46, 2, 444639), 'endTime': datetime.datetime(2025, 10, 10, 16, 46, 2, 445668), 'inputs': {'output': {'city': 'Shanghai', 'country': 'CN', 'feels_like': 28.82, 'humidity': 59, 'temperature': 27.63, 'weather': 'Sunny', 'wind_speed': 4.13}}, 'outputs': {'responseContent': "{'city': 'Shanghai', 'country': 'CN', 'feels_like': 28.82, 'humidity': 59, 'temperature': 27.63, 'weather': 'Sunny', 'wind_speed': 4.13}"}, 'error': None, 'invokeId': 'end', 'parentInvokeId': 'plugin', 'executionId': '05354dbc-dab6-49aa-b7ca-b255180b6559', 'conversationId': '', 'onInvokeData': [], 'agentId': '', 'componentId': '', 'componentName': '', 'componentType': 'end', 'agentParentInvokeId': '', 'metaData': '{"component_id": "", "component_name": "", "component_type": "end"}', 'loopNodeId': None, 'loopIndex': None, 'status': 'finish', 'parentNodeId': ''}
  >>> 
  >>> if __name__ == "__main__":
  ...     asyncio.run(run_test())
  ```

* Example 2:

  ```python
  >>> # Interrupt/resume example: if the WorkflowAgent encounters a scenario requiring user interaction (e.g., a follow-up question),
  >>> # streaming output will return an interaction request. The user can provide interactive input and continue execution.
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
  ...         user_prompt="Please determine the user's intent",
  ...         category_name_list=["Query the weather for a location"],
  ...         model=model_config,
  ...     )
  ...     component = IntentDetectionComponent(config)
  ...     component.add_branch("${intent.classification_id} == 0", ["end"], "Default branch")
  ...     component.add_branch("${intent.classification_id} == 1", ["questioner"], "Weather query branch")
  ...     return component
  >>> 
  >>> def _create_questioner_component() -> QuestionerComponent:
  ...     key_fields = [
  ...         FieldInfo(field_name="location", description="Location", required=True),
  ...         FieldInfo(field_name="date", description="Date", required=True, default_value="today"),
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
  ...                           description="Weather query workflow",
  ...                           version=version,
  ...                           inputs={"query": {"type": "string"}})
  >>> 
  >>> # Build an interactive workflow
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
  >>> # Instantiate components
  >>> start = _create_start_component()
  >>> intent = _create_intent_detection_component()
  >>> questioner = _create_questioner_component()
  >>> end = _create_end_component()
  >>> 
  >>> # Register components to workflow
  >>> flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
  >>> flow.add_workflow_comp("intent", intent, inputs_schema={"query": "${start.query}"})
  >>> flow.add_workflow_comp("questioner", questioner, inputs_schema={"query": "${start.query}"})
  >>> flow.set_end_comp("end", end, inputs_schema={"output": "${questioner.location}"})
  >>> 
  >>> # Connect topology
  >>> flow.add_connection("start", "intent")
  >>> flow.add_connection("intent", "questioner")
  >>> flow.add_connection("questioner", "end")
  >>> 
  >>> # Create WorkflowAgent
  >>> schema = _create_workflow_schema(workflow_id, workflow_name, workflow_version)
  >>> workflow_agent_config = WorkflowAgentConfig(
  ...     id="test_interrupt_agent",
  ...     version="0.1.0",
  ...     description="Test interrupt/resume agent",
  ...     workflows=[schema]
  ... )
  >>> 
  >>> workflow_agent = WorkflowAgent(workflow_agent_config)
  >>> workflow_agent.bind_workflows([flow])
  >>> 
  >>> async def run_test():
  ...     # First streaming call - should trigger an interruption
  ...     interaction_outputs = []
  ...     async for chunk in workflow_agent.stream({"query": "Query the weather", "conversation_id": "c123"}):
  ...         print(f"WorkflowAgent first output >>>  {chunk}")
  ...         if isinstance(chunk, OutputSchema) and chunk.type == "__interaction__":
  ...             print("✅ Interaction request detected in stream!")
  ...             interaction_outputs.append(chunk)
  ... 
  ...     # If there are interaction requests, provide user input and continue streaming execution
  ...     if interaction_outputs:
  ...         print("Interaction request detected, preparing to resume...")
  ...         interactive_input = InteractiveInput()
  ...         for item in interaction_outputs:
  ...             component_id = item.payload.id
  ...             interactive_input.update(component_id, "Shanghai")
  ... 
  ...         # Second streaming call - resume with InteractiveInput
  ...         async for chunk in workflow_agent.stream({"query": interactive_input, "conversation_id": "c123"}):
  ...             print(f"WorkflowAgent output after resume >>>  {chunk}")
  >>> 
  >>> if __name__ == "__main__":
  ...     asyncio.run(run_test())
  ```

---

### `bind_workflows`

```python
bind_workflows(self, workflows: List[Workflow])
```

Binds workflows to the `WorkflowAgent`.

**Parameters**:

* **workflows** (List[[Workflow](../openjiuwen.core/workflow/base.md#class-openjiuwencoreworkflowbaseworkflow)]): A list of workflows to bind to the `WorkflowAgent`.

**Example**:

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
...                         description="Weather query workflow",
...                         version=version,
...                         inputs={"query": {"type": "string"}})
>>> 
>>> # Build workflow
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
>>> # Instantiate components
>>> start = _create_start_component()
>>> end = _create_end_component()
>>> 
>>> # Register components to workflow
>>> flow.set_start_comp("start", start, inputs_schema={"query": "${query}"})
>>> flow.set_end_comp("end", end, inputs_schema={"output": "${start.query}"})
>>> 
>>> # Connect topology
>>> flow.add_connection("start", "end")
>>> 
>>> # Create WorkflowAgent
>>> schema = _create_workflow_schema(workflow_id, workflow_name, workflow_version)
>>> workflow_agent_config = WorkflowAgentConfig(
...   id="test_weather_agent",
...   version="0.1.0",
...   description="Test weather agent",
...   workflows=[schema]
... )
>>> 
>>> workflow_agent = WorkflowAgent(workflow_agent_config)
>>> 
>>> # Bind workflows
>>> workflow_agent.add_workflows([flow])
```
