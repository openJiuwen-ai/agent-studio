# openjiuwen.core.component.start_comp

## class openjiuwen.core.component.start_comp.Start

```python
class openjiuwen.core.component.start_comp.Start(conf: dict)
```

`Start` is an openJiuwen built-in workflow start component. It defines the entry point of a workflow, receives user input, and provides input validation and formatting.

**Parameters**：

- **conf** (dict, optional): Formatting configuration for user input. Passing `{}` or `None` means user input will not be formatted. Default: `None`.
  - The formatting config dict has a required structure: it must contain the key `"inputs"` with a value of type `list[dict]`. If `"inputs"` has an invalid type, a `JiuWenBaseException` will be raised.
  - Each element in `"inputs"` is a configuration object for one input field, containing:
    - **id** (str): The input field name. If not provided, a `JiuWenBaseException` will be raised.
    - **default_value** (Any, optional): Default value for the input field. Only applies when `required=False`. Default: `None` (no default value).
    - **required** (bool, optional): Whether the input field is required. Default: `False`.
  - An example `config` is shown below. In this example, `"query"` is a required field, so the user must provide it when invoking the workflow.

    ```python
    {
        "inputs": [
            {"id": "query", "required": True},
            {"id": "dialogueHistory", "default_value": [], "required": False},
            {"id": "conversationHistory", "required": False},
        ]
    }
    ```

**Exceptions**：

- **JiuWenBaseException**: The base exception type for openJiuwen. For detailed information and resolution methods, see [StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Example**：

```python
>>> import asyncio
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> # Demonstrates basic usage of the Start component and the workflow creation flow
>>> async def demo_start_component():
...     # 1. Create a workflow instance
...     workflow = Workflow()
...     
...     # 2. Configure Start component input parameters
...     start_config = {
...         "inputs": [
...             {"id": "query", "required": True},
...             {"id": "dialogueHistory", "default_value": ["c", "d"], "required": False},
...             {"id": "conversationHistory", "default_value": ["a", "b"], "required": False},
...         ]
...     }
...     
...     # 3. Create and set the start component
...     start_comp = Start(start_config)
...     workflow.set_start_comp("start", start_comp,
...                            inputs_schema={
...                                "query": "${user_inputs.query}",
...                                "dialogueHistory": "${user_inputs.dialogueHistory}",
...                                "conversationHistory": "${user_inputs.conversationHistory}"
...                            })
...     
...     # 4. Set the end component to capture output
...     workflow.set_end_comp("end", Start(),
...                          inputs_schema={
...                              "query": "${start.query}",
...                              "dialogueHistory": "${start.dialogueHistory}",
...                              "conversationHistory": "${start.conversationHistory}"
...                          })
...     
...     # 5. Add connections between components
...     workflow.add_connection("start", "end")
...     
...     # 6. Execute the workflow
...     result = await workflow.invoke(
...         inputs={"user_inputs": {
...             "query": "hello world",
...             "conversationHistory": ["a", "b"]
...         }},
...         runtime=WorkflowRuntime()
...     )
... 
...     print(f"{result}")
>>> 
>>> def main():
...     asyncio.run(demo_start_component())
>>> 
>>> if __name__ == "__main__":
...     main()
>>> 
>>> # The `Start` component formats the user `input` according to `conf` and passes it to the next component.
>>> # The formatted result is:
result={'query': 'hello world', 'dialogueHistory': ['c', 'd'], 'conversationHistory': ['a', 'b']} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
```

## class openjiuwen.core.component.start_comp.StartInputSchema (Reserved class)

`StartInputSchema` is a **reserved class**. It is the schema definition for custom inputs of the built-in `Start` component, intended to replace the functionality of `config`. It is not currently used.

## class openjiuwen.core.component.start_comp.StartOutputSchema (Reserved class)

`StartOutputSchema` is a **reserved class**. It is the schema definition for custom outputs of the built-in `Start` component, intended to replace the functionality of `config`. It is not currently used.
