# openjiuwen.core.component.end_comp

## class openjiuwen.core.component.end_comp.End

```python
class openjiuwen.core.component.end_comp.End(conf: Union[EndConfig, dict] = None)
```

The `End` component is an openJiuwen built-in workflow termination component. It defines the workflow output and supports two output modes:
- Output data using a predefined template format
- Output data directly according to the input definition

The `End` component implements the four capabilities of the base component `ComponentExecutable`: `invoke`, `stream`, `transform`, and `collect`. The implementation formats and outputs results based on different inputs.

**Parameters**:

- **conf** (Union[[EndConfig](#class-openjiuwencorecomponentend_compendconfig), dict], optional): Output formatting configuration.
  - If the type is `dict`, the key must be `"responseTemplate"` and the value must be a `str`.
  - Default: `None`, meaning no formatting is applied.

> **Notes**
>
> - `conf` currently only supports the `responseTemplate` configuration.
> - `responseTemplate` is a rendering template:
>   - If non-empty, output is rendered according to the template.
>   - If `None` or `""`, the template is not used.
>   - Default: `None`.
>   - Example: if the `End` component receives `{"user_var": "Hello"}` and `conf` is `{"responseTemplate": "Output:{{user_var}}"}`, then the `End` output is `"Output:Hello"`. If `conf` is omitted or `responseTemplate` is empty, then the `End` output is `{"user_var": "Hello"}`.

**Exceptions**:

- **JiuWenBaseException**: The base exception type for openJiuwen. For detailed information and fixes, see [StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Examples**:

```python
>>> # Example 1: Demonstrates the basic usage of the End component and the workflow creation process
>>> import asyncio
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> async def demo_end_component():
...     workflow = Workflow()
... 
...     workflow.set_start_comp("start", Start(),
...                             inputs_schema={
...                                 "query": "${user_inputs.query}",
...                                 "content": "${user_inputs.content}",
...                             })
... 
...     workflow.set_end_comp("end", End(),
...                           inputs_schema={"param1": "${start.query}", "param2": "${start.content}"})
... 
...     workflow.add_connection("start", "end")
... 
...     result = await workflow.invoke(
...         inputs={"user_inputs": {
...             "query": "Hello",
...             "content": "Hangzhou"
...         }},
...         runtime=WorkflowRuntime()
...     )
... 
...     print(f"{result}")
>>> 
>>> def main():
...     asyncio.run(demo_end_component())
>>> 
>>> if __name__ == "__main__":
...     main()
result={'output': {'param1': 'Hello', 'param2': 'Hangzhou'}} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
```

```python
>>> # Example 2: Demonstrates the response template usage of the End component
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> async def demo_end_component():
...     workflow = Workflow()
... 
...     workflow.set_start_comp("start", Start(),
...                             inputs_schema={
...                                 "query": "${user_inputs.query}",
...                                 "content": "${user_inputs.content}",
...                             })
... 
...     conf = {
...         "responseTemplate": "Rendered result:{{param1}},{{param2}}"
...     }
...     workflow.set_end_comp("end", End(conf),
...                           inputs_schema={"param1": "${start.query}", "param2": "${start.content}"})
... 
...     workflow.add_connection("start", "end")
... 
...     result = await workflow.invoke(
...         inputs={"user_inputs": {
...             "query": "Hello",
...             "content": "Hangzhou"
...         }},
...         runtime=WorkflowRuntime()
...     )
... 
...     print(f"{result}")
>>> 
>>> def main():
...     asyncio.run(demo_end_component())
>>> 
>>> if __name__ == "__main__":
...     main()
{'responseContent': 'Rendered result: Hello, Hangzhou'}
result={'responseContent': 'Rendered result: Hello, Hangzhou'} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
```

## class openjiuwen.core.component.end_comp.EndConfig

Configuration data class for the `End` component.

- **responseTemplate** (str, optional): Template configuration used by the `End` component for formatted output.
  Default: `None`, meaning output is generated according to the input definition.

