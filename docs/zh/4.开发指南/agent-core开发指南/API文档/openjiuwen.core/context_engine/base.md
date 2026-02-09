# openjiuwen.core.context_engine.base

## class openjiuwen.core.context_engine.base.Context
```python
class openjiuwen.core.context_engine.base.Context()
```

`Context`为Agent、Workflow上下文的抽象类，统一了Agent、Workflow使用上下文的接口(无需自定义实现，具体功能请见派生类[AgentContext](./context.md#class-openjiuwencorecontext_enginecontextagentcontext)和[WorkflowContext](./context.md#class-openjiuwencorecontext_enginecontextworkflowcontext))。

### abstract add_message
```python
abstract add_message(message: BaseMessage, tags: Optional[Dict[str, str]] = None)
```

向上下文历史记录中添加*单条*对话消息的抽象接口。

**参数**：

- **message**([BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage))：要添加的单个消息对象，必须是 [`BaseMessage`]()类型。
- **tags**(Dict[str, str], 可选)：消息标签字典，用于为消息添加元数据信息。元数据信息表示为当前这条Message添加自定义内容，用于自定义模式的筛选和数据隔离。默认值：`None`，表示无标签添加。

### abstract batch_add_messages
```python
abstract batch_add_messages(messages: Union[List[Dict], List[BaseMessage]], tags: Optional[Dict[str, str]] = None)
```
向上下文历史记录*批量*添加对话消息的抽象接口。

**参数**：

- **messages**(Union[List[Dict], List[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)]])：待添加的消息列表。
- **tags**(Dict[str, str], 可选)：消息标签字典，用于为批量添加的消息添加元数据信息。元数据信息表示为当前这条Message添加自定义内容，用于自定义模式的筛选和数据隔离。默认值：`None`，表示无标签添加。

### abstract get_messages
```python
abstract get_messages(num: int = -1, tags: Optional[Dict[str, str]] = None) -> List[BaseMessage]
```
上下文历史记录中*批量*获取消息列表的抽象接口。

**参数**：

- **num**(int)：正数，获取最近的num个消息。如果超出最大长度，返回整个列表中消息。默认值：-1，表示获取所有消息。
- **tags**(Dict[str, str], 可选)：消息标签过滤条件，只返回完全匹配所有标签的消息。默认值：`None`，表示无标签查询。

**返回**：

**List[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage)]**，符合条件的最近的消息列表，最近的消息在最后。


### abstract get_latest_message
```python
abstract get_latest_message(role: str = None) -> Optional[BaseMessage]
```
上下文历史记录中获取最新的消息的抽象接口。

**参数**：

- **role**(str, 可选)：消息角色过滤条件，如`user`、`assistant`、`system`或`tool`。默认值`None`，表示不限角色查询最新一条消息。

**返回**：

**Union[[BaseMessage](../../openjiuwen.core/utils/llm/messages.md#class-openjiuwencoreutilsllmmessagesbasemessage), None]**，符合条件的消息对象，如果找不到符合条件的消息则返回 `None`。