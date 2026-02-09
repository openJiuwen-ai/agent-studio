# openjiuwen.core.utils.llm.messages

## class openjiuwen.core.utils.llm.messages.BaseMessage

```python
openjiuwen.core.utils.llm.messages.BaseMessage(role: str, content: Union[str, List[Union[str, Dict]]] = "", name: Optional[str] = None)
```

A generic base class for messages that represents the basic structure of a message, including role, content, and name.

Parameters:

- role (str): The role of the message, typically "user", "assistant", "system", or "tool", indicating the sender's role.
- content (Union[str, List[Union[str, Dict]]], optional): The message content. Can be a string or a list containing strings or dictionaries. Default: "".
- name (Optional[str], optional): An optional name to identify the role sending the message. Default: None.

Example:

```python
>>> base_msg = BaseMessage(role="user", content="Hello")
```

## class openjiuwen.core.utils.llm.messages.UsageMetadata

```python
openjiuwen.core.utils.llm.messages.UsageMetadata(code: int = 0, errmsg: str = "", prompt: str = "", task_id: str = "", model_name: str = "", finish_reason: str = "", total_latency: float = 0.0, model_stats: dict = {}, first_token_time: str = "", request_start_time: str = "")
```

Represents metadata for a single model invocation, including status code, latency, model statistics, and more.

**Parameters**:

- **code** (int, optional): Application status code indicating the call status. 0 means success; non-zero indicates failure. Default: 0.
- **errmsg** (str, optional): Error message provided when a problem occurs during model processing. Default: "".
- **prompt** (str, optional): The actual prompt sent to the model, describing the user input or system prompt content. Default: "".
- **task_id** (str, optional): A unique identifier for the task, used for tracking and managing tasks. Default: "".
- **model_name** (str, optional): The name of the model used. Default: "".
- **finish_reason** (str, optional): The reason the generation ended, e.g., "stop", "tool_calls". Default: "".
- **total_latency** (float, optional): End-to-end latency in seconds, from the start to the end of the task. Default: 0.0.
- **model_stats** (dict, optional): Model-side statistics (e.g., token usage). Default: {}.
- **first_token_time** (str, optional): Timestamp of the first generated token, typically used to analyze generation latency. Default: "".
- **request_start_time** (str, optional): Timestamp when the request started. Default: "".

**Example**:

```python
>>> usage = UsageMetadata(code=0, model_name="qwen-plus", finish_reason="stop", total_latency=0.123)
```

## class openjiuwen.core.utils.llm.messages.AIMessage

```python
openjiuwen.core.utils.llm.messages.AIMessage(role: str = "assistant", content: Union[str, List[Union[str, Dict]]] = "", name: Optional[str] = None, tool_calls: Optional[List[ToolCall]] = None, usage_metadata: Optional[UsageMetadata] = None, raw_content: Optional[str] = None, reason_content: Optional[str] = None)
```

Represents an assistant response message. Inherits from BaseMessage, and is used to carry model responses and tool calls.

**Parameters**:

- **role** (str): Fixed as "assistant". Default: "assistant".
- **content** (Union[str, List[Union[str, Dict]]], optional): The assistant’s reply content. Default: "".
- **name** (Optional[str], optional): An optional name to identify the source or additional information for the message. Default: None.
- **tool_calls** (Optional[List[ToolCall]], optional): The list of tool calls included in this response. Default: None.
- **usage_metadata** (Optional[UsageMetadata], optional): Usage and statistics metadata for this response. Default: None.
- **raw_content** (Optional[str], optional): Raw, unprocessed content. Default: None.
- **reason_content** (Optional[str], optional): Reasoning or explanatory content. Default: None.

Example:

```python
>>> ai_msg = AIMessage(content="The weather query has been completed.", tool_calls=[tcall], usage_metadata=usage)
```

## class openjiuwen.core.utils.llm.messages.HumanMessage

```python
openjiuwen.core.utils.llm.messages.HumanMessage(role: str = "user", content: Union[str, List[Union[str, Dict]]] = "", name: Optional[str] = None)
```

Represents a message sent by the user. Inherits from BaseMessage.

**Parameters**:

- role (str): Fixed as "user". Default: "user".
- content (Union[str, List[Union[str, Dict]]], optional): The user’s input content. Default: "".
- name (Optional[str], optional): An optional name to identify the source or additional information for the message. Default: None.

**Example**:

```python
>>> human_msg = HumanMessage(content="Please check today's temperature in Shanghai for me.")
```

## class openjiuwen.core.utils.llm.messages.SystemMessage

```python
openjiuwen.core.utils.llm.messages.SystemMessage(role: str = "system", content: Union[str, List[Union[str, Dict]]] = "", name: Optional[str] = None)
```

Represents a system message. Inherits from BaseMessage, and is used to set system-level instructions for the conversation.

**Parameters**:

- **role** (str): Fixed as "system". Default: "system".
- **content** (Union[str, List[Union[str, Dict]]], optional): System prompts or instructions. Default: "".
- **name** (Optional[str], optional): An optional name to identify the source or additional information for the message. Default: None.

**Example**:

```python
>>> sys_msg = SystemMessage(content="You are an assistant.")
```

## class openjiuwen.core.utils.llm.messages.ToolMessage

```python
openjiuwen.core.utils.llm.messages.ToolMessage(role: str = "tool", content: Union[str, List[Union[str, Dict]]] = "", name: Optional[str] = None, tool_call_id: str)
```

Represents a tool return message. Inherits from BaseMessage, and displays the results of tool execution.

**Parameters**:

- **role** (str): Fixed as "tool". Default: "tool".
- **content** (Union[str, List[Union[str, Dict]]]): The tool’s output content. Default: "".
- **name** (Optional[str]): An optional name to identify the source or additional information for the message. Default: None.
- **tool_call_id** (str): The unique identifier corresponding to the tool call.

**Example**:

```python
>>> tool_msg = ToolMessage(tool_call_id=toolCall.id or "call_001", content='{"temp": 23, "units": "c"}')
```