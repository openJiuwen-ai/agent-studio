# openjiuwen.core.utils.tool.tool

The @tool decorator registers a local Python function as a Tool class callable by an LLM, enabling Function Calling-like capabilities.

## tool

```python
tool(func: Callable = None, *, name: str = None, description: str = None, params: List[Param] = None) -> LocalFunction
```

The tool decorator can be used directly as: @tool(name=..., description=..., params=...).

Developers can configure the tool name, description, and params to describe the local function.

**Parameters**:

- **func** (Callable, optional): The Python function to decorate. When used as a decorator, this is automatically provided.
- **name** (str, optional): The unique tool name. If not provided, the function’s __name__ will be used.
- **description** (str, optional): A description of the tool explaining its functionality and use. If not provided, the function’s __doc__ will be used.
- **params** (List[Param], optional): A list of request parameters used to build a JSON Schema for the model. If not provided, parameter info will be automatically extracted from the function signature.

**Returns**:

**LocalFunction**, which inherits from Tool and can be called by the LLM.

**Example**:

```python
>>> from openjiuwen.core.utils.tool.param import Param
>>> from openjiuwen.core.utils.tool.tool import tool
>>> 
>>> # Developer implements the add function and wraps it directly with the tool decorator
>>> # so it can be identified and called by the LLM
>>> @tool(name="Local_add",
...     description="Local addition plugin",
...     params=[
...         Param(name="a", description="First parameter", type="int", required=True),
...         Param(name="b", description="Second parameter", type="int", required=True),
...     ])
... def add(a: int, b: int) -> int:
...     return a + b
... 
>>> # Prepare input parameters
>>> inputs = {
...     "a": 5,
...     "b": 1
... }
... 
>>> result = add.invoke(inputs=inputs)
>>> print(f"Call succeeded, result: {result}")
Call succeeded, result: 6
```