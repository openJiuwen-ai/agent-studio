# openjiuwen.core.context_engine.context

## class openjiuwen.core.context_engine.context.AgentContext
```python
class openjiuwen.core.context_engine.context.AgentContext(owner: ContextOwner, accessor: ContextAccessor)
```
**AgentContext** is a subclass of ContextImpl. In practice, obtain an AgentContext via ContextEngine.get_agent_context, and use AgentContext to manage and operate context within the **agent scope**.

### add_message
```python
add_message(message: BaseMessage, tags: Optional[Dict[str, str]] = None)
```
Add a single chat message to the agent-scope context history. The `BaseMessage` data is stored in the context history with an auto-assigned sequential ID, and you can optionally attach tag metadata to the message.

Parameters:

- **message**([BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)): The single message object to add; must be of type `BaseMessage`.
- **tags** (Dict[str, str], optional): A message tag dictionary used to attach metadata to the message. Metadata means adding custom content to the current Message for custom filtering and data isolation. Default: `None`, meaning no tags are added.

Examples:

```python
>>> from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage
>>> from openjiuwen.core.context_engine.engine import ContextEngine
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig

>>> # Example using AgentContext
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id= "agent_id", config= config)
>>> agent_context_impl = context_engine.get_agent_context("session_id")
>>> 
>>> # Example 1: Add a user message
>>> user_message = HumanMessage(content="Hello, please help me check the weather")
>>> agent_context_impl.add_message(user_message, tags={"type": "user_input", "time": "2024-01-01"})
>>> 
>>> # Example 2: Add an AI reply
>>> ai_message = AIMessage(content="Today's weather is sunny, temperature 25°C.")
>>> agent_context_impl.add_message(ai_message, tags={"type": "ai_response", "model": "gpt-4"})
```

### batch_add_messages
```python
batch_add_messages(messages: List[BaseMessage], tags: Optional[Dict[str, str]] = None)
```
Batch add chat messages to the agent-scope context history. Supports batch addition of multiple message formats, and allows adding tags and owner information to messages.

Parameters:

- **messages** (List[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)]): The list of messages to add.
- **tags** (Dict[str, str], optional): A message tag dictionary used to attach metadata to the batch of messages. Metadata means adding custom content to the current Message for custom filtering and data isolation. Default: `None`, meaning no tags are added.

Examples:

```python
>>> from openjiuwen.core.utils.llm.messages import BaseMessage, HumanMessage, AIMessage
>>> from openjiuwen.core.context_engine.engine import ContextEngine
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig
>>> 
>>> # Example using AgentContext
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id= "agent_id", config= config)
>>> agent_context_impl = context_engine.get_agent_context("session_id")
>>> # Example 1: Batch add messages using a list of BaseMessage
>>> messages = [
...     HumanMessage(content="Hello, what can you help me with?"),
...     AIMessage(content="I can help answer questions, handle tasks, and more.")
... ]
>>> agent_context_impl.batch_add_messages(messages, tags={"source": "user_input", "batch_id": "001"})
```

### get_messages
```python
get_messages(num: int = -1, tags: Optional[Dict[str, str]] = None) -> List[BaseMessage]
```
Retrieve a list of messages from the agent-scope context history that meet the criteria. Supports filtering by the number of messages and by tags, returning the most recent messages.

Parameters:

- **num** (int): A positive integer; retrieve the most recent num messages. If num exceeds the total length, returns the entire list. Default: -1, which retrieves all messages.
- **tags** (Dict[str, str], optional): Tag-based filter criteria; returns only messages that fully match all provided tags. Default: `None`, meaning no tag filter.

Returns:

**List[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)]**, the list of recent messages that meet the criteria, with the most recent message at the end.

Examples:

```python
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig
>>> from openjiuwen.core.context_engine.engine import ContextEngine 
>>> from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage, SystemMessage
>>> 
>>> # Example using AgentContext
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id="agent_id", config = config)
>>> agent_context = context_engine.get_agent_context("session_id")
>>> # Add some test messages
>>> agent_context.add_message(HumanMessage(content="Hello"), tags={"type": "greeting"})
>>> agent_context.add_message(AIMessage(content="Hello, how can I help you?"))
>>> agent_context.add_message(HumanMessage(content="How is the weather today?"), tags={"type": "weather_query", "priority": "high"})
>>> agent_context.add_message(AIMessage(content="Today's weather is sunny."))
>>> agent_context.add_message(SystemMessage(content="System prompt: conversation ended"))

>>> # Example 1: Get the most recent 10 messages
>>> recent_messages = agent_context.get_messages(10)
>>> print(f"Example 1 - Get the most recent 10 messages (actually {len(recent_messages)}):")
>>> for i, msg in enumerate(recent_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
Example 1 - Get the most recent 10 messages (actually 5):
  1. HumanMessage: Hello
  2. AIMessage: Hello, how can I help you?
  3. HumanMessage: How is the weather today?
  4. AIMessage: Today's weather is sunny.
  5. SystemMessage: System prompt: conversation ended

>>> # Example 2: Get the most recent messages with specific tags
>>> tagged_messages = agent_context.get_messages(10, tags={"type": "user_input", "priority": "high"})
>>> print(f"Example 2 - Messages with tags {{'type': 'user_input', 'priority': 'high'}}: {len(tagged_messages)}")
>>> for i, msg in enumerate(tagged_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
Example 2 - Messages with tags {'type': 'user_input', 'priority': 'high'}: 0

>>> # Additional example: Get messages with the weather_query tag
>>> weather_tagged_messages = agent_context.get_messages(10, tags={"type": "weather_query"})
>>> print(f"Additional example - Messages with tags {{'type': 'weather_query'}}: {len(weather_tagged_messages)}")
>>> for i, msg in enumerate(weather_tagged_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
Additional example - Messages with tags {'type': 'weather_query'}}: 1
  1. HumanMessage: How is the weather today?

>>> # Additional example: Get the most recent 3 messages
>>> recent_3_messages = agent_context.get_messages(3)
>>> print(f"Additional example - Get the most recent 3 messages: {len(recent_3_messages)}")
>>> for i, msg in enumerate(recent_3_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
Additional example - Get the most recent 3 messages: 3
  1. HumanMessage: How is the weather today?
  2. AIMessage: Today's weather is sunny.
  3. SystemMessage: System prompt: conversation ended

```

### get_latest_message
```python
get_latest_message(role: str = None) -> Union[BaseMessage, None]
```
Retrieve the most recent message from the agent-scope context history. You can filter by message role, returning the most recent message with the specified role.

Parameters:

- **role** (str, optional): Message role filter, such as `user`, `assistant`, `system`, or `tool`. Default: `None`, meaning the most recent message regardless of role.

Returns:

**Union[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage), None]**, the message object that meets the criteria, or `None` if no matching message is found.

Examples:

```python
>>> from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage, SystemMessage
>>> from openjiuwen.core.context_engine.engine import ContextEngine
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig
>>> 
>>> # Example using AgentContext
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id="agent_id", config=config)
>>> agent_context = context_engine.get_agent_context("session_id")
>>> 
>>> # Add some test messages
>>> agent_context.add_message(HumanMessage(content="Hello"), tags={"type": "greeting"})
>>> agent_context.add_message(AIMessage(content="Hello, how can I help you?"))
>>> agent_context.add_message(HumanMessage(content="How is the weather today?"))
>>> agent_context.add_message(AIMessage(content="Today's weather is sunny."))
>>> agent_context.add_message(SystemMessage(content="System prompt: conversation ended"))
>>> 
>>> # Example 1: Get the most recent message (any role)
>>> latest_message = agent_context.get_latest_message()
>>> print(latest_message.content)
System prompt: conversation ended
>>> 
>>> # Example 2: Get the most recent user message
>>> latest_user_message = agent_context.get_latest_message(role="user")
>>> print(latest_user_message.content)
How is the weather today?
>>> 
>>> # Example 3: Get the most recent AI reply
>>> latest_ai_message = agent_context.get_latest_message(role="assistant")
>>> print(latest_ai_message.content)
Today's weather is sunny.
>>> 
>>> # Example 4: Get a non-existent role (returns None)
>>> nonexistent_message = agent_context.get_latest_message(role="tool")
>>> print(nonexistent_message)
None
```

## class openjiuwen.core.context_engine.context.WorkflowContext
```python
class openjiuwen.core.context_engine.context.WorkflowContext()
```
**WorkflowContext** is a subclass of ContextImpl. In practice, obtain a WorkflowContext via ContextEngine.get_workflow_context, and use WorkflowContext to manage and operate context within the **workflow bound to the agent**.

### add_message
```python
add_message(message: BaseMessage, tags: Optional[Dict[str, str]] = None)
```
Add a single chat message to the context history of the workflow bound to the agent. The `BaseMessage` data is stored in the context history with an auto-assigned sequential ID, and you can optionally attach tag metadata to the message.

Parameters:

- **message** ([BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)): The single message object to add; must be of type `BaseMessage`.
- **tags** (Dict[str, str], optional): A message tag dictionary used to attach metadata to the message. Metadata means adding custom content to the current Message for custom filtering and data isolation. Default: `None`, meaning no tags are added.

Examples:

```python
>>> from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage
>>> from openjiuwen.core.context_engine.engine import ContextEngine 
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig
>>>
>>> # Example using WorkflowContext
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id="agent_id", config=config)
>>> workflow_context_impl = context_engine.get_workflow_context("workflow_id", "session_id")
>>> 
>>> # Example 1: Add a user message
>>> user_message = HumanMessage(content="Hello, please help me check the weather")
>>> workflow_context_impl.add_message(user_message, tags={"type": "user_input", "time": "2024-01-01"})
>>> 
>>> # Example 2: Add an AI reply
>>> ai_message = AIMessage(content="Today's weather is sunny, temperature 25°C.")
>>> workflow_context_impl.add_message(ai_message, tags={"type": "ai_response", "model": "gpt-4"})
```

### batch_add_messages
```python
batch_add_messages(messages: List[BaseMessage], tags: Optional[Dict[str, str]] = None)
```
Batch add chat messages to the context history of the workflow bound to the agent. Supports batch addition of multiple message formats, and allows adding tag metadata and owner information to messages.

Parameters:

- **messages** (List[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)]): The list of messages to add.
- **tags** (Dict[str, str], optional): A message tag dictionary used to attach metadata to the batch of messages. Metadata means adding custom content to the current Message for custom filtering and data isolation. Default: `None`, meaning no tags are added.

Examples:

```python
>>> from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage
>>> from openjiuwen.core.context_engine.engine import ContextEngine 
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig
>>>
>>> # Example using WorkflowContext
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id="agent_id", config=config)
>>> workflow_context_impl = context_engine.get_workflow_context("workflow_id", "session_id")
>>> # Example 1: Batch add messages using a list of BaseMessage
>>> messages = [
...     HumanMessage(content="Hello, what can you help me with?"),
...     AIMessage(content="I can help answer questions, handle tasks, and more.")
... ]
>>> workflow_context_impl.batch_add_messages(messages, tags={"source": "user_input", "batch_id": "001"})
```

### get_messages
```python
get_messages(num: int, tags: Optional[Dict[str, str]] = None) -> List[BaseMessage]
```
Retrieve a list of messages from the context history of the workflow bound to the agent that meet the criteria. Supports filtering by the number of messages and by tags, returning the most recent messages.

Parameters:

- **num** (int): A positive integer; retrieve the most recent num messages. If num exceeds the total length, returns the entire list.
- **tags** (Dict[str, str], optional): Tag-based filter criteria; returns only messages that fully match all provided tags. Default: `None`, meaning no tag filter.

Returns:

**List[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)]**, the list of recent messages that meet the criteria, with the most recent message at the end.

Examples:

```python
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig
>>> from openjiuwen.core.context_engine.engine import ContextEngine 
>>> from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage, SystemMessage

>>> # Example using WorkflowContext
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id="agent_id", config=config)
>>> workflow_context_impl = context_engine.get_workflow_context("workflow_id", "session_id")
>>> # Add some test messages
>>> workflow_context_impl.add_message(HumanMessage(content="Hello"), tags={"type": "greeting"})
>>> workflow_context_impl.add_message(AIMessage(content="Hello, how can I help you?"))
>>> workflow_context_impl.add_message(HumanMessage(content="How is the weather today?"), tags={"type": "weather_query", "priority": "high"})
>>> workflow_context_impl.add_message(AIMessage(content="Today's weather is sunny."))
>>> workflow_context_impl.add_message(SystemMessage(content="System prompt: conversation ended"))

>>> # Example 1: Get the most recent 10 messages
>>> recent_messages = workflow_context_impl.get_messages(10)
>>> print(f"Example 1 - Get the most recent 10 messages (actually {len(recent_messages)}):")
>>> for i, msg in enumerate(recent_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
Example 1 - Get the most recent 10 messages (actually 5):
  1. HumanMessage: Hello
  2. AIMessage: Hello, how can I help you?
  3. HumanMessage: How is the weather today?
  4. AIMessage: Today's weather is sunny.
  5. SystemMessage: System prompt: conversation ended

>>> # Example 2: Get the most recent messages with specific tags
>>> tagged_messages = workflow_context_impl.get_messages(10, tags={"type": "user_input", "priority": "high"})
>>> print(f"Example 2 - Messages with tags {{'type': 'user_input', 'priority': 'high'}}: {len(tagged_messages)}")
>>> for i, msg in enumerate(tagged_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
Example 2 - Messages with tags {'type': 'user_input', 'priority': 'high'}: 0

>>> # Additional example: Get messages with the weather_query tag
>>> weather_tagged_messages = workflow_context_impl.get_messages(10, tags={"type": "weather_query"})
>>> print(f"Additional example - Messages with tags {{'type': 'weather_query'}}: {len(weather_tagged_messages)}")
>>> for i, msg in enumerate(weather_tagged_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
Additional example - Messages with tags {'type': 'weather_query'}}: 1
  1. HumanMessage: How is the weather today?

>>> # Additional example: Get the most recent 3 messages
>>> recent_3_messages = workflow_context_impl.get_messages(3)
>>> print(f"Additional example - Get the most recent 3 messages: {len(recent_3_messages)}")
>>> for i, msg in enumerate(recent_3_messages):
...     print(f"  {i+1}. {type(msg).__name__}: {msg.content}")
Additional example - Get the most recent 3 messages: 3
  1. HumanMessage: How is the weather today?
  2. AIMessage: Today's weather is sunny.
  3. SystemMessage: System prompt: conversation ended

```

### get_latest_message
```python
get_latest_message(role: str = None) -> Union[BaseMessage, None]
```
Retrieve the most recent message from the context history of the workflow bound to the agent. You can filter by message role, returning the most recent message with the specified role.

Parameters:

- **role** (str, optional): Message role filter, such as `user`, `assistant`, `system`, or `tool`. Default: `None`, meaning the most recent message regardless of role.

Returns:

**Union[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage), None]**, the message object that meets the criteria, or `None` if no matching message is found.

Examples:

```python
>>> from openjiuwen.core.utils.llm.messages import HumanMessage, AIMessage, SystemMessage
>>> from openjiuwen.core.context_engine.engine import ContextEngine 
>>> from openjiuwen.core.context_engine.config import ContextEngineConfig
>>>
>>> # Example using WorkflowContext
>>> config = ContextEngineConfig()
>>> context_engine = ContextEngine(agent_id="agent_id", config=config)
>>> workflow_context_impl = context_engine.get_workflow_context("workflow_id", "session_id")
>>> 
>>> # Add some test messages
>>> workflow_context_impl.add_message(HumanMessage(content="Hello"), tags={"type": "greeting"})
>>> workflow_context_impl.add_message(AIMessage(content="Hello, how can I help you?"))
>>> workflow_context_impl.add_message(HumanMessage(content="How is the weather today?"))
>>> workflow_context_impl.add_message(AIMessage(content="Today's weather is sunny."))
>>> workflow_context_impl.add_message(SystemMessage(content="System prompt: conversation ended"))
>>> 
>>> # Example 1: Get the most recent message (any role)
>>> latest_message = workflow_context_impl.get_latest_message()
>>> print(latest_message.content)
System prompt: conversation ended
>>> 
>>> # Example 2: Get the most recent user message
>>> latest_user_message = workflow_context_impl.get_latest_message(role="user")
>>> print(latest_user_message.content)
How is the weather today?
>>> 
>>> # Example 3: Get the most recent AI reply
>>> latest_ai_message = workflow_context_impl.get_latest_message(role="assistant")
>>> print(latest_ai_message.content)
Today's weather is sunny.
>>> 
>>> # Example 4: Get a non-existent role (returns None)
>>> nonexistent_message = workflow_context_impl.get_latest_message(role="tool")
>>> print(nonexistent_message)
None
```