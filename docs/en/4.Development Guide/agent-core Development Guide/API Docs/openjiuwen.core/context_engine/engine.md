# openjiuwen.core.context_engine.engine

## class openjiuwen.core.context_engine.engine.ContextEngine
```python
class openjiuwen.core.context_engine.engine.ContextEngine(agent_id:str, config: ContextEngineConfig = None, model: Optional[BaseModelClient] = None)
```
The `ContextEngine` class manages context information for model inputs, including recording, retrieving, and filtering context (short- and long-term memory, tools, knowledge, etc.). It standardizes the management and invocation of context during Agent development.

Parameters:

- **agent_id**(str): The current agent id, required.
- **config**([ContextEngineConfig](./config.md), optional): Configuration parameters related to the context engine. Default: `None`, meaning no configuration available.
- **model**([BaseModelClient](../utils/llm/base.md), optional): Large model instance. Default: `None`, indicating no model instance.

**Example**:

```python
>>> from openjiuwen.core.context_engine.engine import ContextEngine 
>>> 
>>> # Create a context engine instance
>>> context_engine = ContextEngine(agent_id="agent_id")
```

### get_agent_context
```python
get_agent_context(session_id: str) -> AgentContext
```
Obtain the AgentContext instance for the agent's context. Instantiation depends on the creation of the agent (`agent_id`). Through AgentContext, you can manage and operate the context under the specified agent_id.

Parameters:

- **session_id**(str): The current session id, used to isolate different context contents; required.

Returns:

**AgentContext**, the current agent context instance for the specified id, allowing access to and manipulation of the context under the current agent.

**Example**:

```python
>>> import os
>>> os.environ['LLM_SSL_VERIFY'] = 'false'
>>> from datetime import datetime
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
... 
>>> def _create_tool():
...     weather_plugin = RestfulApi(
...         name="WeatherReporter",
...         description="Weather query plugin",
...         params=[
...             Param(name="location", description="The location for the weather query, must be in English", type="string", required=True),
...             Param(name="date", description="The date for the weather query, format YYYY-MM-DD", type="string", required=True),
...         ],
...         path="your weather search api url",
...         headers={},
...         method="GET",
...         response=[],
...     )
...     return weather_plugin
... 
... 
>>> def _create_prompt_template():
...     system_prompt = "You are an AI assistant. Call appropriate tools when needed to help me complete tasks! Today's date is: {}\nNote: 1. If the user request does not specify a specific time, default to today."
...     return [
...         dict(role="system", content=system_prompt.format(build_current_date()))
...     ]
...
>>> agent_id="react_agent_123"
>>> model_config = _create_model()
>>> prompt_template = _create_prompt_template()
>>> 
>>> react_agent_config = create_react_agent_config(
...     agent_id=agent_id,
...     agent_version="0.0.1",
...     description="AI assistant",
...     model=model_config,
...     prompt_template=prompt_template
... )
... 
>>> react_agent: ReActAgent = ReActAgent(react_agent_config)
>>> react_agent.add_tools([_create_tool()])
... 
>>> async def run_test():
...     # Generate session id
...     session_id = "your_session_id"
...     # Invoke the agent
...     result = await react_agent.invoke({"query": "Check the weather in Hangzhou", "conversation_id": session_id})
...     print(f"ReActAgent final output: {result}")
...     # Get the agent context instance via session_id
...     agent_context = react_agent.context_engine.get_agent_context(session_id=session_id)
... 
```

### get_workflow_context
```python
get_workflow_context(workflow_id: str, session_id: str) -> WorkflowContext
```
Obtain the WorkflowContext instance for a workflow. Instantiation depends on the creation of both the agent and the workflow (`agent_id` and `workflow_id`). Through WorkflowContext, you can manage and operate the context of a specific workflow bound to the agent_id.

Parameters:

- **workflow_id**(str): The workflow id of the workflow context; required.
- **session_id**(str): The current session id; required.

Returns:

**WorkflowContext**, the workflow context instance for the specified id, allowing access to and manipulation of the context under the current workflow.

**Example**:

```python
>>> from openjiuwen.agent.common.schema import WorkflowSchema
>>> from openjiuwen.agent.workflow_agent.workflow_agent import WorkflowAgent
>>> from openjiuwen.agent.config.workflow_config import WorkflowAgentConfig
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.workflow.workflow_config import WorkflowConfig, WorkflowMetadata
>>> 
>>> agent_id = "weather_agent_test"
>>> workflow_id = "weather_agent_flow_id_test"
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
... 
>>> flow = Workflow(workflow_config=workflow_config)
>>> 
>>> schema = WorkflowSchema(
...     id=workflow_id,
...     name=workflow_name,
...     description="Weather query workflow",
...     version=workflow_version,
...     inputs={"query": {"type": "string"}}
... )
... 
>>> config = WorkflowAgentConfig(
...     id=agent_id,
...     version="0.1.0",
...     description="Weather agent for testing",
...     workflows=[schema]
... )
... 
>>> workflow_agent = WorkflowAgent(config)
>>> workflow_agent.bind_workflows([flow])
>>> async def run_test():
...     # Generate session id
...     session_id = "your_session_id"
...     result = await workflow_agent.invoke({"query": "Check the weather in Shanghai", "conversation_id": session_id})
...     # Get the workflow context instance via workflow_id and session_id
...     workflow_context = workflow_agent.context_engine.get_workflow_context(workflow_id, session_id)
... 
```