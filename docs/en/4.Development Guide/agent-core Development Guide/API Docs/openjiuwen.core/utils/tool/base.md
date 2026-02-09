# openjiuwen.core.utils.tool.base

## class openjiuwen.core.utils.tool.base.Tool

```python
Tool()
```

The Tool base class is invocable by LLMs and defines abstract interfaces that enable Function Calling. When implementing a custom tool, inherit from Tool.

### invoke

```python
abstractmethod invoke(inputs: Input, **kwargs) -> Output
```

Synchronous interface for invoking the tool.

**Parameters**:

- **inputs** (Input): The input parameter object for the tool interface, containing the specific argument values required for the call.
- **kwargs**: Variadic keyword arguments for passing additional request configuration or parameters.

**Returns**:

- **Output**: The response produced by the tool invocation.

### ainvoke

```python
abstractmethod ainvoke(inputs: Input, **kwargs) -> Output
```

Asynchronous interface for invoking the tool.

**Parameters**:

- **inputs** (Input): The input parameter object for the tool interface, containing the specific argument values required for the call.
- **kwargs**: Variadic keyword arguments for passing additional request configuration or parameters.

**Returns**:

- **Output**: The response produced by the tool invocation.

### get_tool_info

```python
abstractmethod get_tool_info() -> ToolInfo
```

Retrieve tool metadata.

**Returns**:

- **ToolInfo**: The tool metadata.

**Example**:

```python
>>> # Implement a local-function wrapper class LocalFunction
>>> from typing import Callable, List, TypeVar
>>> 
>>> from openjiuwen.core.utils.tool.schema import ToolInfo
>>> from openjiuwen.core.utils.tool.base import Tool
>>> from openjiuwen.core.utils.tool.param import Param

>>> Input = TypeVar('Input', contravariant=True)
>>> Output = TypeVar('Output', contravariant=True)
>>> 
>>> # Custom implementation of a local function
>>> class LocalFunction(Tool):
... 
...     def __init__(self, name: str, description: str, params: List[Param] = None, func: Callable = None):
...         super().__init__()
...         self.name = name
...         self.description = description
...         self.params = params
...         self.func = func
... 
...     def invoke(self, inputs: Input, **kwargs) -> Output:
...         """invoke the tool"""
...         res = self.func(**inputs)
...         return res
... 
...     async def ainvoke(self, inputs: Input, **kwargs) -> Output:
...         """async invoke the tool"""
...         res = await self.func(**inputs)
...         return res
... 
...     def get_tool_info(self) -> ToolInfo:
...         """get tool info"""
...         tool_info_dict = Param.format_functions(self)
...         tool_info = ToolInfo(**tool_info_dict)
...         return tool_info
... 
>>> # A developer-defined local function
>>> def add(a: int, b: int):
...     """function add"""
...     return a+b
... 
>>> # Wrap the local function
>>> local_tool = LocalFunction(
...     name="local_add",
...     description="local function for add",
...     params=[
...         Param(name="a", description="first arg", param_type="int", required=True),
...         Param(name="b", description="second arg", param_type="int", required=True),
...     ],
...     func = add)
...
>>> result = local_tool.invoke({"a": 5, "b": 1})
>>> print(f"Invocation succeeded, result: {result}")
Invocation succeeded, result: 6
>>> 
>>> res = local_tool.get_tool_info()
>>> print(res)
type='function' name='local_add' description='local function for add' parameters=Parameters(type='object', properties={'a': {'description': 'first arg', 'type': 'integer'}, 'b': {'description': 'second arg', 'type': 'integer'}}, required=['a', 'b'])
```