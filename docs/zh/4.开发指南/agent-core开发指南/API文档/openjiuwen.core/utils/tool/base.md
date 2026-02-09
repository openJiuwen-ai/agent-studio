# openjiuwen.core.utils.tool.base

## class openjiuwen.core.utils.tool.base.Tool

```python
Tool()
```

`Tool`基类是可被LLM调用的基类，定义的抽象接口实现了Function Calling的能力。开发者实现自定义工具时，需要继承`Tool`基类。

### invoke

```python
abstractmethod invoke(inputs: Input, **kwargs) -> Output
```

调用工具的同步接口。

**参数**：

* **inputs**(Input)：工具接口的输入参数对象，包含接口调用所需的具体参数值。
* **kwargs**：可变关键字参数，用于传递额外的请求配置或参数。

**返回**：

**Output**，工具调用的响应结果。

### ainvoke

```python
abstractmethod ainvoke(inputs: Input, **kwargs) -> Output
```

调用工具的异步接口。

**参数**：

* **inputs**(Input)：工具接口的输入参数对象，包含接口调用所需的具体参数值。
* **kwargs**：可变关键字参数，用于传递额外的请求配置或参数。

**返回**：

**Output**，工具调用的响应结果。

### get_tool_info

```python
abstractmethod get_tool_info() -> ToolInfo
```

获取工具信息。

**返回**：

**ToolInfo**，工具信息。

**样例**：

```python
>>> # 实现本地函数封装类LocalFunction
>>> from typing import Callable, List, TypeVar
>>> 
>>> from openjiuwen.core.utils.tool.schema import ToolInfo
>>> from openjiuwen.core.utils.tool.base import Tool
>>> from openjiuwen.core.utils.tool.param import Param

>>> Input = TypeVar('Input', contravariant=True)
>>> Output = TypeVar('Output', contravariant=True)
>>> 
>>> # 自定义实现本地函数
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
>>> # 开发者自定义本地函数
>>> def add(a: int, b: int):
...     """function add"""
...     return a+b
... 
>>> # 封装本地函数
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
>>> print(f"调用成功，返回结果: {result}")
调用成功，返回结果: 6
>>> 
>>> res = local_tool.get_tool_info()
>>> print(res)
type='function' name='local_add' description='local function for add' parameters=Parameters(type='object', properties={'a': {'description': 'first arg', 'type': 'integer'}, 'b': {'description': 'second arg', 'type': 'integer'}}, required=['a', 'b'])
```
