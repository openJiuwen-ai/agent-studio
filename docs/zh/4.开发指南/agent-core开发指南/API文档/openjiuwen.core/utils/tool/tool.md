# openjiuwen.core.utils.tool.tool

`@tool`装饰器用于将本地Python函数注册为可被LLM调用的Tool类，从而实现类似Function Calling的能力。

## tool

```python
tool(func: Callable = None, *, name: str = None, description: str = None, params: List[Param] = None) -> LocalFunction
```

`tool`装饰器支持使用方式：作为装饰器直接使用：`@tool(name=..., description=..., params=...)`

开发者配置工具名称、描述信息与params参数等信息用于描述本地函数。

**参数**：

* **func**(Callable, 可选)：要装饰的Python函数。当作为装饰器使用时，此参数由装饰器自动传入。
* **name**(str, 可选)：工具名称，具有唯一性。如果不提供，将使用函数的`__name__`属性。
* **description**(str, 可选)：工具的描述信息，用于说明功能和用途。如果不提供，将使用函数的`__doc__`属性。
* **params**(List[[Param](./param.md#class-openjiuwencoreutilstoolparamparam)], 可选)：请求参数列表，用于组成Json schema供大模型识别。如果不提供，将从函数签名中自动提取参数信息。

**返回**：

**LocalFunction**，继承自`Tool`类，可被LLM调用的工具类。

**样例**：

```python
>>> from openjiuwen.core.utils.tool.param import Param
>>> from openjiuwen.core.utils.tool.tool import tool
>>> 
>>> # 开发者实现add函数，直接使用tool装饰器进行封装，可供大模型识别调用
>>> @tool(name="Local_add",
...     description="本地加法插件",
...     params=[
...         Param(name="a", description="第一个参数", type="int", required=True),
...         Param(name="b", description="第二个参数", type="int", required=True),
...     ])
... def add(a: int, b: int) -> int:
...     return a + b
... 
>>> # 准备输入参数
>>> inputs = {
...     "a": 5,
...     "b": 1
... }
... 
>>> result = add.invoke(inputs=inputs)
>>> print(f"调用成功，返回结果: {result}")
调用成功，返回结果: 6
```
