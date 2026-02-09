# openjiuwen.core.utils.tool.schema

## class openjiuwen.core.utils.tool.schema.Parameters

```python
openjiuwen.core.utils.tool.schema.Parameters(type: str = "object", properties: Dict[str, Any] = {}, required: List[str] = [])
```

定义工具描述信息的参的结构化信息。

**参数**：

* ​**type**​(str)：参数类型标识，固定为 `"object"`（表示参数为结构化对象），默认值为 `"object"`。
* ​**properties**​(Dict[str, Any])：工具输入参数的集合，键为参数名，值为参数的详细定义（如类型、描述等），默认值为空字典。
* ​**required**​(List[str])：必填参数名称列表，指定哪些参数是调用工具时的必选参数，默认值为空列表，表示不存在非必选参数。

**样例**：

```python
>>> params = Parameters(
...     properties={
...         "city": {"type": "string", "description": "城市名称"},
...         "units": {"type": "string", "description": "温度单位，c表示摄氏度，f表示华氏度"}
...     },
...     required=["city"]
... )
```

### class openjiuwen.core.utils.tool.schema.ToolInfo

```python
ToolInfo(type: str = Field(default="function"), name: str = Field(default=""), description: str = Field(default=""), parameters: Optional[Parameters] = Field(default=None))
```

描述工具的基础信息，包含工具类型、名称、描述及参数定义。

**参数**：

* ​**type**​(str)：工具类型标识，固定为 `"function"`（表示工具为函数类型），默认值为 `"function"`。
* ​**name**(str): 工具/函数的名称，需唯一标识该工具，默认值为空字符串。
* ​**description**(str): 工具/函数的功能描述，用于说明工具的用途，默认值为空字符串。
* ​**parameters**(Parameters, 可选): 工具参数的结构化定义，为`Parameters`类实例，无参数时为`None`，默认值为`None`。

**样例**：

```python
>>> params = Parameters(
...     properties={"city": {"type": "string", "description": "城市名称"}},
...     required=["city"]
... )
>>> tool_info = ToolInfo(
...     name="get_weather",
...     description="根据城市名称查询实时天气信息",
...     parameters=params
... )
```

### class openjiuwen.core.utils.tool.schema.ToolCall

```python
ToolCall(id: Optional[str], type: str, name: str, arguments: str, index: Optional[int] = None)
```

记录一次大模型生成的工具调用信息，包含调用标识、工具类型、名称及原始参数。

**参数**：

* ​**id**​(str, 可选)：工具调用的唯一标识，用于追踪单次调用，无标识时为`None`，无默认值。
* ​**type**​(str)：调用的工具类型，需与`ToolInfo`的`type`保持一致（通常为"function"），无默认值。
* ​**name**​(str)：被调用工具/函数的名称，需与`ToolInfo`的`name`匹配，无默认值。
* ​**arguments**​(str)：工具调用的原始参数字符串（通常为JSON格式），无默认值。
* **index**(int, 可选)：工具调用在序列中的位置索引，用于多工具调用排序，默认值为 `None`。

**样例**：

```python
>>> tool_call = ToolCall(
...     id="call_890123",
...     type="function",
...     name="get_weather",
...     arguments='{"city":"北京","units":"c"}'
... )
>>> # 无调用ID的示例
>>> tool_call_no_id = ToolCall(
...     type="function",
...     name="get_weather",
...     arguments='{"city":"广州"}'
... )
```
