# openjiuwen.core.context_engine.engine

## class openjiuwen.core.context_engine.engine.ContextEngine
```python
class openjiuwen.core.context_engine.engine.ContextEngine(agent_id:str, config: ContextEngineConfig = None, model: Optional[BaseModelClient] = None)
```
`ContextEngine`类用于管理模型输入上下文的信息，包含对上下文信息（长短期记忆、工具、知识等）的记录、获取、筛选等，便于开发Agent时对上下文内容进行标准化管理和调用。

**参数**：

- **agent_id**(str)：当前agent id，必填。
- **config**([ContextEngineConfig](./config.md), 可选)：上下文引擎相关配置参数。默认值：`None`，表示无可用配置。
- **model**([BaseModelClient](../utils/llm/base.md), 可选)：大模型实例。默认值：`None`，表示没有大模型实列。

​**样例**​：

```python
>>> from openjiuwen.core.context_engine.engine import ContextEngine 
>>> 
>>> # 创建上下文引擎实例
>>> context_engine = ContextEngine(agent_id="agent_id")
```

### get_agent_context
```python
get_agent_context(session_id: str) -> AgentContext
```
获取agent上下文AgentContext实例。实例化过程依赖agent的创建(`agent_id`)。通过AgentContext可以对agent_id的上下文进行管理与操作。

**参数**：

- **session_id**(str)：当前会话id，用于隔离不同上下文内容，必填参数。

**返回**：

**AgentContext**，返回对应id的当前agent上下文实例，可访问和处理当前agent下的上下文信息。

**样例**：

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
...         description="天气查询插件",
...         params=[
...             Param(name="location", description="天气查询的地点，必须为英文", type="string", required=True),
...             Param(name="date", description="天气查询的时间，格式为YYYY-MM-DD", type="string", required=True),
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
...     system_prompt = "你是一个AI助手，在适当的时候调用合适的工具，帮助我完成任务！今天的日期为：{}\n注意：1. 如果用户请求中未指定具体时间，则默认为今天。"
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
...     description="AI助手",
...     model=model_config,
...     prompt_template=prompt_template
... )
... 
>>> react_agent: ReActAgent = ReActAgent(react_agent_config)
>>> react_agent.add_tools([_create_tool()])
... 
>>> async def run_test():
...     # 生成会话id
...     session_id = "your_session_id"
...     # 调用agent
...     result = await react_agent.invoke({"query": "查询杭州的天气", "conversation_id": session_id})
...     print(f"ReActAgent 最终输出结果：{result}")
...     # 通过session_id获取agent中上下文实例
...     agent_context = react_agent.context_engine.get_agent_context(session_id=session_id)
... 
```

### get_workflow_context
```python
get_workflow_context(workflow_id: str, session_id: str) -> WorkflowContext
```
获取workflow上下文WorkflowContext实例。实例化过程依赖agent和workflow的创建(`agent_id`和`workflow_id`)。通过WorkflowContext可以对绑定在agent_id上的特定workflow的上下文进行管理与操作。

**参数**：

- **workflow_id**(str)：工作流上下文的workflow id，必填参数。
- **session_id**(str)：当前会话id，必填参数。

**返回**：

**WorkflowContext**，返回对应id的workflow上下文实例，可访问和处理当前workflow下的上下文信息。

**样例**：

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
...     description="天气查询工作流",
...     version=workflow_version,
...     inputs={"query": {"type": "string"}}
... )
... 
>>> config = WorkflowAgentConfig(
...     id=agent_id,
...     version="0.1.0",
...     description="测试用天气 agent",
...     workflows=[schema]
... )
... 
>>> workflow_agent = WorkflowAgent(config)
>>> workflow_agent.bind_workflows([flow])
>>> async def run_test():
...     # 生成会话id
...     session_id = "your_session_id"
...     result = await workflow_agent.invoke({"query": "查询上海的天气", "conversation_id": session_id})
...     # 通过workflow_id和session_id获取工作流中上下文实例
...     workflow_context = workflow_agent.context_engine.get_workflow_context(workflow_id, session_id)
... 
```
