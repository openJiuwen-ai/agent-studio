# openjiuwen.core.utils.tool.param

## class openjiuwen.core.utils.tool.param.Param

Parameter configuration class for a tool.

- **name** (str): Parameter name.
- **description** (str): Parameter description. Explains the meaning and purpose of the parameter.
- **type** (str): Parameter type. Allowed values: `string`, `int`, `number`, `boolean`, `object`, or `array`.
- **required** (bool): Whether the parameter is required. `True` means required; `False` means optional.

Example**:
**
```python
# Define the tool's parameter type
>>> from openjiuwen.core.utils.tool.param import Param
>>> 
>>> first_args = Param(name="a", description="The first parameter", type="int", required=True)
```