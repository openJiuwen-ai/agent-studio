# openjiuwen.core.context_engine.context

## class openjiuwen.core.context_engine.context.AgentContext
```python
class openjiuwen.core.context_engine.context.AgentContext(owner: ContextOwner, accessor: ContextAccessor)
```
**AgentContext**是ContextImpl的派生类，使用时通过ContextEngine的get_agent_context获取实际的AgentContext，通过AgentContext对**智能体范围**的上下文进行管理与操作。

### add_message
```python
add_message(message: BaseMessage, tags: Optional[Dict[str, str]] = None)
```
向Agent范围的上下文历史记录中添加单条对话消息。将`BaseMessage`数据保存在上下文历史记录中且自动分配顺序ID，同时允许为消息添加标签信息。

**参数**：

- **message**([BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage))：要添加的单个消息对象，必须是`BaseMessage`类型。
- **tags**(Dict[str, str], 可选)：消息标签字典，用于为消息添加元数据信息。元数据信息表示为当前这条Message添加自定义内容，用于自定义模式的筛选和数据隔离。默认值：`None`，表示无标签添加。

**样例**：

```python
>>> from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage
>>> from openjiuwen.core.context_engine.engine import ContextEngine
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig

>>> # 以AgentContext上下文为例
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id= "agent_id", config= config)
>>> agent_context_impl = context_engine.get_agent_context("session_id")
>>> 
>>> # 样例1：添加用户消息
>>> user_message = HumanMessage(content="你好，请帮我查询天气")
>>> agent_context_impl.add_message(user_message, tags={"type": "user_input", "time": "2024-01-01"})
>>> 
>>> # 样例2：添加AI回复消息
>>> ai_message = AIMessage(content="今天天气晴朗，温度25度。")
>>> agent_context_impl.add_message(ai_message, tags={"type": "ai_response", "model": "gpt-4"})
```

### batch_add_messages
```python
batch_add_messages(messages: List[BaseMessage], tags: Optional[Dict[str, str]] = None)
```
向Agent范围的上下文历史记录批量添加对话消息。支持多种消息格式的批量添加，并允许为消息添加标签和所有者信息。

**参数**：

- **messages**(List[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)])：待添加的消息列表。
- **tags**(Dict[str, str], 可选)：消息标签字典，用于为批量添加的消息添加元数据信息。元数据信息表示为当前这条Message添加自定义内容，用于自定义模式的筛选和数据隔离。默认值：`None`，表示无标签添加。

**样例**：

```python
>>> from openjiuwen.core.utils.llm.messages import BaseMessage, HumanMessage, AIMessage
>>> from openjiuwen.core.context_engine.engine import ContextEngine
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig
>>> 
>>> # 以AgentContext上下文为例
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id= "agent_id", config= config)
>>> agent_context_impl = context_engine.get_agent_context("session_id")
>>> # 样例1：使用 BaseMessage 列表批量添加消息
>>> messages = [
...     HumanMessage(content="你好，请问你能帮我什么？"),
...     AIMessage(content="我可以帮您解答问题、处理任务等。")
... ]
>>> agent_context_impl.batch_add_messages(messages, tags={"source": "user_input", "batch_id": "001"})
```

### get_messages
```python
get_messages(num: int = -1, tags: Optional[Dict[str, str]] = None) -> List[BaseMessage]
```
用于从Agent范围的上下文历史记录中获取符合条件的消息列表。支持按消息数量和过滤条件（所有者、标签）来筛选历史消息，返回最近的消息。

**参数**：

- **num**(int)：正数，获取最近的num个消息。如果超出最大长度，返回整个列表中消息。默认值：-1，表示获取所有消息。
- **tags**(Dict[str, str], 可选)：消息标签过滤条件，只返回完全匹配所有标签的消息。默认值：`None`，表示无标签查询。

**返回**：

**List[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)]**，符合条件的最近的消息列表，最近的消息在最后。

**样例**：

```python
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig
>>> from openjiuwen.core.context_engine.engine import ContextEngine 
>>> from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage, SystemMessage
>>> 
>>> # 以AgentContext上下文为例
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id="agent_id", config = config)
>>> agent_context = context_engine.get_agent_context("session_id")
>>> # 添加一些测试消息
>>> agent_context.add_message(HumanMessage(content="你好"), tags={"type": "greeting"})
>>> agent_context.add_message(AIMessage(content="你好，有什么可以帮助您的？"))
>>> agent_context.add_message(HumanMessage(content="今天天气怎么样？"), tags={"type": "weather_query", "priority": "high"})
>>> agent_context.add_message(AIMessage(content="今天天气晴朗。"))
>>> agent_context.add_message(SystemMessage(content="系统提示：对话结束"))

>>> # 样例1：获取最近10条消息
>>> recent_messages = agent_context.get_messages(10)
>>> print(f"样例1 - 获取最近10条消息（实际有{len(recent_messages)}条）:")
>>> for i, msg in enumerate(recent_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
样例1 - 获取最近10条消息（实际有5条）:
  1. HumanMessage: 你好
  2. AIMessage: 你好，有什么可以帮助您的？
  3. HumanMessage: 今天天气怎么样？
  4. AIMessage: 今天天气晴朗。
  5. SystemMessage: 系统提示：对话结束

>>> # 样例2：获取带有特定标签的最近消息
>>> tagged_messages = agent_context.get_messages(10, tags={"type": "user_input", "priority": "high"})
>>> print(f"样例2 - 获取标签{{'type': 'user_input', 'priority': 'high'}}的消息: {len(tagged_messages)}条")
>>> for i, msg in enumerate(tagged_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
样例2 - 获取标签{{'type': 'user_input', 'priority': 'high'}}的消息:0条

>>> # 补充样例：获取带weather_query标签的消息
>>> weather_tagged_messages = agent_context.get_messages(10, tags={"type": "weather_query"})
>>> print(f"补充样例 - 获取标签{{'type': 'weather_query'}}的消息: {len(weather_tagged_messages)}条")
>>> for i, msg in enumerate(weather_tagged_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
补充样例 - 获取标签{'type': 'weather_query'}}的消息: 1条
  1. HumanMessage: 今天天气怎么样？

>>> # 补充样例：获取最近3条消息
>>> recent_3_messages = agent_context.get_messages(3)
>>> print(f"补充样例 - 获取最近3条消息: {len(recent_3_messages)}条")
>>> for i, msg in enumerate(recent_3_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
补充样例 - 获取最近3条消息: 3条
  1. HumanMessage: 今天天气怎么样？
  2. AIMessage: 今天天气晴朗。
  3. SystemMessage: 系统提示：对话结束

```

### get_latest_message
```python
get_latest_message(role: str = None) -> Union[BaseMessage, None]
```
用于从Agent范围的上下文历史记录中获取最新的消息。可以根据消息角色进行过滤，返回指定角色的最新消息。

**参数**：

- **role**(str, 可选)：消息角色过滤条件，如`user`、`assistant`、`system`或`tool`。默认值`None`，表示不限角色查询最新一条消息。

**返回**：

**Union[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage), None]**，符合条件的消息对象，如果找不到符合条件的消息则返回 `None`。

**样例**：

```python
>>> from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage, SystemMessage
>>> from openjiuwen.core.context_engine.engine import ContextEngine
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig
>>> 
>>> # 以AgentContext上下文为例
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id="agent_id", config=config)
>>> agent_context = context_engine.get_agent_context("session_id")
>>> 
>>> # 添加一些测试消息
>>> agent_context.add_message(HumanMessage(content="你好"), tags={"type": "greeting"})
>>> agent_context.add_message(AIMessage(content="你好，有什么可以帮助您的？"))
>>> agent_context.add_message(HumanMessage(content="今天天气怎么样？"))
>>> agent_context.add_message(AIMessage(content="今天天气晴朗。"))
>>> agent_context.add_message(SystemMessage(content="系统提示：对话结束"))
>>> 
>>> # 样例1：获取最新的一条消息（不限角色）
>>> latest_message = agent_context.get_latest_message()
>>> print(latest_message.content)
系统提示：对话结束
>>> 
>>> # 样例2：获取最新的用户消息
>>> latest_user_message = agent_context.get_latest_message(role="user")
>>> print(latest_user_message.content)
今天天气怎么样？
>>> 
>>> # 样例3：获取最新的AI回复消息
>>> latest_ai_message = agent_context.get_latest_message(role="assistant")
>>> print(latest_ai_message.content)
今天天气晴朗。
>>> 
>>> # 样例4：获取不存在的角色消息（返回None）
>>> nonexistent_message = agent_context.get_latest_message(role="tool")
>>> print(nonexistent_message)
None
```

## class openjiuwen.core.context_engine.context.WorkflowContext
```python
class openjiuwen.core.context_engine.context.WorkflowContext()
```
​**WorkflowContext**是ContextImpl的派生类，使用时通过ContextEngine的get_workflow_context得到实际的WorkflowContext，通过WorkflowContext对**智能体绑定的工作流范围内**的上下文进行管理与操作。

### add_message
```python
add_message(message: BaseMessage, tags: Optional[Dict[str, str]] = None)
```
向Agent绑定的工作流的上下文历史记录中添加单条对话消息。将`BaseMessage`数据保存在上下文历史记录中且自动分配顺序ID，同时允许为消息添加标签信息。

**参数**：

- **message**([BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage))：要添加的单个消息对象，必须是`BaseMessage`类型。
- **tags**(Dict[str, str], 可选)：消息标签字典，用于为消息添加元数据信息。元数据信息表示为当前这条Message添加自定义内容，用于自定义模式的筛选和数据隔离。默认值：`None`，表示无标签添加。

**样例**：

```python
>>> from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage
>>> from openjiuwen.core.context_engine.engine import ContextEngine 
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig
>>>
>>> # 以WorkflowContext上下文为例.
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id="agent_id", config=config)
>>> workflow_context_impl = context_engine.get_workflow_context("workflow_id", "session_id")
>>> 
>>> # 样例1：添加用户消息
>>> user_message = HumanMessage(content="你好，请帮我查询天气")
>>> workflow_context_impl.add_message(user_message, tags={"type": "user_input", "time": "2024-01-01"})
>>> 
>>> # 样例2：添加AI回复消息
>>> ai_message = AIMessage(content="今天天气晴朗，温度25度。")
>>> workflow_context_impl.add_message(ai_message, tags={"type": "ai_response", "model": "gpt-4"})
```

### batch_add_messages
```python
batch_add_messages(messages: List[BaseMessage], tags: Optional[Dict[str, str]] = None)
```
用于Agent绑定的工作流的上下文历史记录中批量添加对话消息。支持多种消息格式的批量添加，并允许为消息添加标签和所有者信息。

**参数**：

- **messages**(List[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)])：待添加的消息列表。
- **tags**(Dict[str, str], 可选)：消息标签字典，用于为批量添加的消息添加元数据信息。元数据信息表示为当前这条Message添加自定义内容，用于自定义模式的筛选和数据隔离。默认值：`None`，表示无标签添加。

**样例**：

```python
>>> from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage
>>> from openjiuwen.core.context_engine.engine import ContextEngine 
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig
>>>
>>> # 以WorkflowContext上下文为例
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id="agent_id", config=config)
>>> workflow_context_impl = context_engine.get_workflow_context("workflow_id", "session_id")
>>> # 样例1：使用 BaseMessage 列表批量添加消息
>>> messages = [
...     HumanMessage(content="你好，请问你能帮我什么？"),
...     AIMessage(content="我可以帮您解答问题、处理任务等。")
... ]
>>> workflow_context_impl.batch_add_messages(messages, tags={"source": "user_input", "batch_id": "001"})
```

### get_messages
```python
get_messages(num: int, tags: Optional[Dict[str, str]] = None) -> List[BaseMessage]
```
用于从Agent绑定的工作流的上下文历史记录中中获取符合条件的消息列表。支持按消息数量和过滤条件（所有者、标签）来筛选历史消息，返回最近的消息。

**参数**：

- **num** (int)：正数，获取最近的num个消息。如果超出最大长度，返回整个列表中消息。
- **tags** (Dict[str, str], 可选)：消息标签过滤条件，只返回完全匹配所有标签的消息。默认值：`None`，表示无标签查询。

**返回**：

**List[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)]**，符合条件的最近的消息列表，最近的消息在最后。

**样例**：

```python
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig
>>> from openjiuwen.core.context_engine.engine import ContextEngine 
>>> from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage, SystemMessage

>>> # 以WorkflowContext上下文为例
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id="agent_id", config=config)
>>> workflow_context_impl = context_engine.get_workflow_context("workflow_id", "session_id")
>>> # 添加一些测试消息
>>> workflow_context_impl.add_message(HumanMessage(content="你好"), tags={"type": "greeting"})
>>> workflow_context_impl.add_message(AIMessage(content="你好，有什么可以帮助您的？"))
>>> workflow_context_impl.add_message(HumanMessage(content="今天天气怎么样？"), tags={"type": "weather_query", "priority": "high"})
>>> workflow_context_impl.add_message(AIMessage(content="今天天气晴朗。"))
>>> workflow_context_impl.add_message(SystemMessage(content="系统提示：对话结束"))

>>> # 样例1：获取最近10条消息
>>> recent_messages = workflow_context_impl.get_messages(10)
>>> print(f"样例1 - 获取最近10条消息（实际有{len(recent_messages)}条）:")
>>> for i, msg in enumerate(recent_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
样例1 - 获取最近10条消息（实际有5条）:
  1. HumanMessage: 你好
  2. AIMessage: 你好，有什么可以帮助您的？
  3. HumanMessage: 今天天气怎么样？
  4. AIMessage: 今天天气晴朗。
  5. SystemMessage: 系统提示：对话结束

>>> # 样例2：获取带有特定标签的最近消息
>>> tagged_messages = workflow_context_impl.get_messages(10, tags={"type": "user_input", "priority": "high"})
>>> print(f"样例2 - 获取标签{{'type': 'user_input', 'priority': 'high'}}的消息: {len(tagged_messages)}条")
>>> for i, msg in enumerate(tagged_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
样例2 - 获取标签{'type': 'user_input', 'priority': 'high'}的消息: 0条

>>> # 补充样例：获取带weather_query标签的消息
>>> weather_tagged_messages = workflow_context_impl.get_messages(10, tags={"type": "weather_query"})
>>> print(f"补充样例 - 获取标签{{'type': 'weather_query'}}的消息: {len(weather_tagged_messages)}条")
>>> for i, msg in enumerate(weather_tagged_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
补充样例 - 获取标签{'type': 'weather_query'}}的消息: 1条
  1. HumanMessage: 今天天气怎么样？

>>> # 补充样例：获取最近3条消息
>>> recent_3_messages = workflow_context_impl.get_messages(3)
>>> print(f"补充样例 - 获取最近3条消息: {len(recent_3_messages)}条")
>>> for i, msg in enumerate(recent_3_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
补充样例 - 获取最近3条消息: 3条
  1. HumanMessage: 今天天气怎么样？
  2. AIMessage: 今天天气晴朗。
  3. SystemMessage: 系统提示：对话结束

```

### get_latest_message
```python
get_latest_message(role: str = None) -> Union[BaseMessage, None]
```
用于从Agent绑定的工作流的上下文历史记录中获取最新的消息。可以根据消息角色进行过滤，返回指定角色的最新消息。

**参数**：

- **role**(str, 可选)：消息角色过滤条件，如`user`、`assistant`、`system`或`tool`。默认值：`None`，表示不限角色查询最新一条消息。

**返回**：

**Union[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage), None]**，符合条件的消息对象，如果找不到符合条件的消息则返回 `None`。

**样例**：

```python
>>> from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage, SystemMessage
>>> from openjiuwen.core.context_engine.engine import ContextEngine 
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig
>>>
>>> # 以WorkflowContext上下文为例
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id="agent_id", config=config)
>>> workflow_context_impl = context_engine.get_workflow_context("workflow_id", "session_id")
>>> 
>>> # 添加一些测试消息
>>> workflow_context_impl.add_message(HumanMessage(content="你好"), tags={"type": "greeting"})
>>> workflow_context_impl.add_message(AIMessage(content="你好，有什么可以帮助您的？"))
>>> workflow_context_impl.add_message(HumanMessage(content="今天天气怎么样？"))
>>> workflow_context_impl.add_message(AIMessage(content="今天天气晴朗。"))
>>> workflow_context_impl.add_message(SystemMessage(content="系统提示：对话结束"))
>>> 
>>> # 样例1：获取最新的一条消息（不限角色）
>>> latest_message = workflow_context_impl.get_latest_message()
>>> print(latest_message.content)
系统提示：对话结束
>>> 
>>> # 样例2：获取最新的用户消息
>>> latest_user_message = workflow_context_impl.get_latest_message(role="user")
>>> print(latest_user_message.content)
今天天气怎么样？
>>> 
>>> # 样例3：获取最新的AI回复消息
>>> latest_ai_message = workflow_context_impl.get_latest_message(role="assistant")
>>> print(latest_ai_message.content)
今天天气晴朗。
>>> 
>>> # 样例4：获取不存在的角色消息（返回None）
>>> nonexistent_message = workflow_context_impl.get_latest_message(role="tool")
>>> print(nonexistent_message)
None
```
