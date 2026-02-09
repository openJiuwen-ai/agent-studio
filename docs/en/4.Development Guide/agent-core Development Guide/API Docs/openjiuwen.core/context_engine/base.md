# openjiuwen.core.context_engine.base

## class openjiuwen.core.context_engine.base.Context
```python
class openjiuwen.core.context_engine.base.Context()
```

`Context` is the abstract class for Agent and Workflow contexts. It unifies the interface for using contexts in Agents and Workflows (no custom implementation is needed; see the derived classes [AgentContext](./context.md#class-openjiuwencorecontext_enginecontextagentcontext) and [WorkflowContext](./context.md#class-openjiuwencorecontext_enginecontextworkflowcontext) for concrete functionality).

### abstract add_message
```python
abstract add_message(message: BaseMessage, tags: Optional[Dict[str, str]] = None)
```

Abstract interface for adding a *single* conversation message to the context history.

**Parameters**:

- **message**([BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)): The single message object to add; must be of type [`BaseMessage`]().
- **tags**(Dict[str, str], optional): A dictionary of message tags used to attach metadata to the message. The metadata represents custom content added to this Message and can be used for custom-mode filtering and data isolation. Default: `None` (no tags).

### abstract batch_add_messages
```python
abstract batch_add_messages(messages: Union[List[Dict], List[BaseMessage]], tags: Optional[Dict[str, str]] = None)
```
Abstract interface for *batch* adding conversation messages to the context history.

**Parameters**:

- **messages**(Union[List[Dict], List[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)]]): The list of messages to add.
- **tags**(Dict[str, str], optional): A dictionary of message tags used to attach metadata to the messages being added in batch. The metadata represents custom content added to each Message and can be used for custom-mode filtering and data isolation. Default: `None` (no tags).

### abstract get_messages
```python
abstract get_messages(num: int = -1, tags: Optional[Dict[str, str]] = None) -> List[BaseMessage]
```
Abstract interface for *batch* retrieving a list of messages from the context history.

**Parameters**:

- **num**(int): A positive integer that specifies how many of the most recent messages to retrieve. If it exceeds the maximum length, all messages in the list are returned. Default: -1 (retrieve all messages).
- **tags**(Dict[str, str], optional): A tag filter; only messages that exactly match all tags are returned. Default: `None` (no tag filter).

**Returns**:

**List[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)]**, the most recent messages that meet the criteria, with the most recent message at the end.

### abstract get_latest_message
```python
abstract get_latest_message(role: str = None) -> Optional[BaseMessage]
```
Abstract interface for retrieving the latest message from the context history.

**Parameters**:

- **role**(str, optional): A message role filter, such as `user`, `assistant`, `system`, or `tool`. Default: `None` (retrieve the latest message regardless of role).

**Returns**:

**Union[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage), None]**, the message object that meets the criteria, or `None` if no matching message is found.