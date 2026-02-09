# openjiuwen.core.utils.llm.messages

## class openjiuwen.core.utils.llm.messages.BaseMessage

```python
openjiuwen.core.utils.llm.messages.BaseMessage(role: str, content: Union[str, List[Union[str, Dict]]] = "", name: Optional[str] = None)
```

通用消息基类，表示消息的基本结构，包括角色、内容以及名称。

**参数**：

* ​**role**​(str)：消息的角色，通常为 `"user"`、`"assistant"`、`"system"`、`"tool"`，表示发送者的角色。
* ​**content**​(Union[str, List[Union[str, Dict]]], 可选)：消息内容，可以是字符串，也可以是包含字符串或字典的列表，默认值：`""`。
* ​**name**​(Optional[str], 可选)：发送消息的角色名称标识，默认值：`None`。
* **样例**：

```python
>>> base_msg = BaseMessage(role="user", content="你好")
```

## class openjiuwen.core.utils.llm.messages.UsageMetadata

```python
openjiuwen.core.utils.llm.messages.UsageMetadata(code: int = 0, errmsg: str = "", prompt: str = "", task_id: str = "", model_name: str = "", finish_reason: str = "", total_latency: float = 0.0, model_stats: dict = {}, first_token_time: str = "", request_start_time: str = "")
```

表示一次模型调用的元数据，包括状态码、延迟、模型统计信息等。

**参数**：

* ​**code**​(int, 可选)：业务状态码，表示调用的状态，`0` 为成功，非 `0` 表示失败，默认值：`0`。
* ​**errmsg**​(str, 可选)：错误信息，当模型处理过程中出现问题时，提供错误信息。默认值：`""`。
* ​**prompt**​(str, 可选)：实际发送给模型的提示词，描述用户输入或系统提示词的内容。默认值：`""`。
* ​**task_id**​(str, 可选)：任务的唯一标识符，用于唯一标识一个任务，便于追踪和管理任务，默认值：`""`。
* ​**model_name**​(str, 可选)：使用的模型名称，默认值：`""`。
* ​**finish_reason**​(str, 可选)：生成结束原因，可能为`"stop"`、`"tool_calls"`，默认值：`""`。
* ​**total_latency**​(float, 可选)：端到端耗时（秒），表示从任务开始到结束的总时间，默认值：`0.0`。
* ​**model_stats**​(dict, 可选)：模型侧统计数据（如 token 用量），默认值：`{}`。
* ​**first_token_time**​(str, 可选)：首次生成token的时间戳，记录首次生成 token 的时间，通常用于分析生成的延迟，默认值：`""`。
* ​**request_start_time**​(str, 可选)：请求开始的时间戳，记录模型请求开始的时间，默认值：`""`。

**样例**：

```python
>>> usage = UsageMetadata(code=0, model_name="qwen-plus", finish_reason="stop", total_latency=0.123)
```

## class openjiuwen.core.utils.llm.messages.AIMessage

```python
openjiuwen.core.utils.llm.messages.AIMessage(role: str = "assistant", content: Union[str, List[Union[str, Dict]]] = "", name: Optional[str] = None, tool_calls: Optional[List[ToolCall]] = None, usage_metadata: Optional[UsageMetadata] = None, raw_content: Optional[str] = None, reason_content: Optional[str] = None)
```

表示助手回复的消息，继承自 `BaseMessage`，用于承载模型回复与工具调用。

**参数**：

* ​**role**​(str)：固定为 `"assistant"`，默认值：`"assistant"`。
* ​**content**​(Union[str, List[Union[str, Dict]]], 可选)：助手的回复内容，默认值：`""`。
* ​**name**​(Optional[str], 可选)：可选名称，标识该消息的来源或其他附加信息，默认值：`None`。
* ​**tool_calls**​(Optional[List[[ToolCall](../tool/schema.md#class-openjiuwencoreutilstoolschematoolcall)]], 可选)：本次回复内的工具调用列表，默认值：`None`。
* ​**usage_metadata**​(Optional[[UsageMetadata](#class-openjiuwencoreutilsllmmessagesusagemetadata)], 可选)：本次回复的统计元数据，默认值：`None`。
* ​**raw_content**​(Optional[str], 可选)：原始未处理内容，默认值：`None`。
* ​**reason_content**​(Optional[str], 可选)：思考或解释内容，默认值：`None`。

**样例**：

```python
>>> ai_msg = AIMessage(content="天气已查询完成。", tool_calls=[tcall], usage_metadata=usage)
```

## class openjiuwen.core.utils.llm.messages.HumanMessage

```python
openjiuwen.core.utils.llm.messages.HumanMessage(role: str = "user", content: Union[str, List[Union[str, Dict]]] = "", name: Optional[str] = None)
```

表示用户发送的消息，继承自 `BaseMessage`。

**参数**：

* ​**role**​(str)：固定为 `"user"`，默认值：`"user"`。
* ​**content**​(Union[str, List[Union[str, Dict]]], 可选)：用户输入的消息内容，默认值：`""`。
* ​**name**​(Optional[str], 可选)：可选名称，标识该消息的来源或其他附加信息，默认值：`None`。

**样例**：

```python
>>> human_msg = HumanMessage(content="帮我查下今天上海的温度")
```

## class openjiuwen.core.utils.llm.messages.SystemMessage

```python
openjiuwen.core.utils.llm.messages.SystemMessage(role: str = "system", content: Union[str, List[Union[str, Dict]]] = "", name: Optional[str] = None)
```

表示系统消息，继承自 `BaseMessage`，用于设置对话系统级指令。

**参数**：

* ​**role**​(str)：固定为 `"system"`，默认值：`"system"`。
* ​**content**​(Union[str, List[Union[str, Dict]]], 可选)：系统提示或指令，默认值：`""`。
* ​**name**​(Optional[str], 可选)：可选名称，标识该消息的来源或其他附加信息，默认值：`None`。

**样例**：

```python
>>> sys_msg = SystemMessage(content="你是一名助手。")
```

## class openjiuwen.core.utils.llm.messages.ToolMessage

```python
openjiuwen.core.utils.llm.messages.ToolMessage(role: str = "tool", content: Union[str, List[Union[str, Dict]]] = "", name: Optional[str] = None, tool_call_id: str)
```

表示工具返回消息，继承自 `BaseMessage`，展示工具执行的结果。

**参数**：

* ​**role**​(str)：固定为 `"tool"`，默认值：`"tool"`。
* ​**content**​(Union[str, List[Union[str, Dict]]])：工具的输出内容，默认值：`""`。
* ​**name**​(Optional[str])：可选名称，标识该消息的来源或其他附加信息，默认值：`None`。
* ​**tool_call_id**​(str)：对应工具调用的唯一标识符。

**样例**：

```python
>>> tool_msg = ToolMessage(tool_call_id=toolCall.id or "call_001", content='{"temp": 23, "units": "c"}')
```
