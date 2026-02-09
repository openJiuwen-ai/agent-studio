# openjiuwen.core.component.set_variable_comp

## class openjiuwen.core.component.set_variable_comp.SetVariableComponent

```python
class openjiuwen.core.component.set_variable_comp.SetVariableComponent(variable_mapping: dict[str, Any])
```

`SetVariableComponent` is an openJiuwen built-in workflow variable assignment component. It provides the ability to configure variable mappings and dynamically set and manage variables, enabling dynamic data passing and state management in a workflow. This component also supports being used inside the loop component [LoopComponent](./loop_comp.md#class-openjiuwencorecomponentloop_comploopcomponent). With this variable assignment component, you can dynamically update and pass data during loop execution.

**Parameters**：

* **variable_mapping** (dict[str, Any]): A variable-mapping dictionary that defines the variable names to set and their corresponding values. The value must not be `None`. The mapping dictionary supports one or more key–value pairs. Supported key–value types are as follows:
  * Mapping keys support the following 3 types:

    | Type | Description | Example |
    | :---: | :---: | :---: |
    | Non-reference variable name | String; directly specifies the variable name | `"node_a.var_value"` |
    | Single-level reference variable name | String; extracts the variable name via the `"${variable_path}"` placeholder syntax. The reference path is split by `.`, and is single-level only | `"${node_a.var_value}"` extracts the variable name `"node_a.var_value"` |
    | Nested reference variable name | String; extracts the variable name via the `"${variable_path}"` placeholder syntax. The reference path is split by `.`, and can have multiple levels | `"${node_a.nested.var_value}"` extracts the variable name `"node_a.nested.var_value"` |

  * Mapping values support the following 3 types:

    | Type | Description | Example |
    | :---: | :---: | :---: |
    | Fixed value | Directly provide static data such as text or numbers | `"hello world"`, `123`, etc. |
    | Single-level dynamic reference | Extract a dynamic variable value via the `"${variable_path}"` placeholder syntax. The reference path is split by `.`, and is single-level only | Suppose `node_b.var_value = "hello world"`, then `"${node_b.var_value}"` extracts the dynamic value `"hello world"` |
    | Nested dynamic reference | Extract a dynamic variable value via the `"${variable_path}"` placeholder syntax. The reference path is split by `.`, and can have multiple levels | Suppose `node_b.nested = {"var_value": 123}`, then `"${node_b.nested.var_value}"` extracts the dynamic value `123` |

**Exceptions**：

* **JiuWenBaseException**: The base exception type for openJiuwen. For detailed information and resolution methods, see [StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Examples**：

* Example 1：

```python
>>> # Use `SetVariableComponent` inside the loop body to set intermediate variables
>>> import asyncio
>>> from openjiuwen.core.component.loop_comp import LoopGroup, LoopComponent
>>> from openjiuwen.core.component.set_variable_comp import SetVariableComponent
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> 
>>> 
>>> class AddTenNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id: str):
...         super().__init__()
...         self.node_id = node_id
... 
...     async def invoke(self, inputs, runtime: Runtime, context: Context):
...         return {"result": inputs["source"] + 10}
>>> 
>>> 
>>> class CommonNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id: str):
...         super().__init__()
...         self.node_id = node_id
... 
...     async def invoke(self, inputs, runtime: Runtime, context: Context):
...         return inputs
... 
...     async def stream(self, inputs, runtime: Runtime, context: Context):
...         yield await self.invoke(inputs, runtime, context)
>>> 
>>> 
>>> # Create the workflow
>>> flow = Workflow()
>>> # MockStartNode: the start node of the workflow; simply passes input data to the next node
>>> flow.set_start_comp("s", Start())
>>> # MockEndNode: the end node of the workflow; collects and returns the final workflow result
>>> flow.set_end_comp("e", End(), inputs_schema={"array_result": "${b.array_result}", "user_var": "${b.user_var}"})
>>> # CommonNode: a generic node that returns the input data as-is
>>> flow.add_workflow_comp("a", CommonNode("a"))
>>> flow.add_workflow_comp("b", CommonNode("b"),
>>>                        inputs_schema={"array_result": "${l.results}", "user_var": "${l.user_var}"})
>>> 
>>> # Create the loop body
>>> loop_group = LoopGroup()
>>> # AddTenNode: a special node that adds 10 to the input field `source` and returns it
>>> loop_group.add_workflow_comp("1", AddTenNode("1"), inputs_schema={"source": "${l.index}"})
>>> loop_group.add_workflow_comp("2", AddTenNode("2"), inputs_schema={"source": "${l.user_var}"})
>>> # Use SetVariableComponent to set the intermediate variable
>>> set_variable_component = SetVariableComponent({"${l.user_var}": "${2.result}"})
>>> loop_group.add_workflow_comp("3", set_variable_component)
>>> loop_group.start_nodes(["1"])
>>> loop_group.end_nodes(["3"])
>>> loop_group.add_connection("1", "2")
>>> loop_group.add_connection("2", "3")
>>> 
>>> # Create LoopComponent
>>> loop_component = LoopComponent(loop_group, {"results": "${1.result}", "user_var": "${l.user_var}"})
>>> 
>>> # Add to workflow
>>> flow.add_workflow_comp("l", loop_component, inputs_schema={"loop_type": "number", "loop_number": 3,
>>>                                                            "intermediate_var": {"user_var": "${input_number}"}})
>>> 
>>> # Configure connections
>>> flow.add_connection("s", "a")
>>> flow.add_connection("a", "l")
>>> flow.add_connection("l", "b")
>>> flow.add_connection("b", "e")
>>> 
>>> 
>>> async def run_workflow():
...     return await flow.invoke({"input_number": 2}, WorkflowRuntime())
>>> 
>>> 
>>> if __name__ == "__main__":
...     # Run test
...     result = asyncio.get_event_loop().run_until_complete(run_workflow())
...     print(result.result)
{'output': {'array_result': [10, 11, 12], 'user_var': 32}}
```

* Example 2：

```python
>>> # Use `SetVariableComponent` inside the workflow to set a nested-structure variable
>>> import asyncio
>>> from openjiuwen.core.component.set_variable_comp import SetVariableComponent
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> 
>>> 
>>> class AddTenNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id: str):
...         super().__init__()
...         self.node_id = node_id
... 
...     async def invoke(self, inputs, runtime: Runtime, context: Context):
...         return {"result": inputs["source"] + 10}
>>> 
>>> 
>>> class CommonNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id: str):
...         super().__init__()
...         self.node_id = node_id
... 
...     async def invoke(self, inputs, runtime: Runtime, context: Context):
...         return inputs
... 
...     async def stream(self, inputs, runtime: Runtime, context: Context):
...         yield await self.invoke(inputs, runtime, context)
>>> 
>>> 
>>> flow = Workflow()
>>> flow.set_start_comp("s", Start())
>>> flow.set_end_comp("e", End(), inputs_schema={"result": "${a.nested.value}"})
>>> 
>>>  # Create SetVariableComponent to set a nested-structure variable
>>> set_variable_component = SetVariableComponent({"${a.nested.value}": 123})
>>> flow.add_workflow_comp("a", set_variable_component)
>>> 
>>>  # Configure connections
>>> flow.add_connection("s", "a")
>>> flow.add_connection("a", "e")
>>> 
>>> 
>>> async def run_workflow():
...     return await flow.invoke({"input_number": 2}, WorkflowRuntime())
>>> 
>>> 
>>> if __name__ == "__main__":
...     # Run test
...     result = asyncio.get_event_loop().run_until_complete(run_workflow())
...     print(result.result)
{'output': {'result': 123}}
```

* Example 3：

```python
>>> import asyncio
>>> from openjiuwen.core.component.set_variable_comp import SetVariableComponent
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> 
>>> class AddTenNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id: str):
...         super().__init__()
...         self.node_id = node_id
...     async def invoke(self, inputs, runtime: Runtime, context: Context):
...         return {"result": inputs["source"] + 10}
>>> 
>>> flow = Workflow()
>>> flow.set_start_comp("s", Start(), inputs_schema={"input_value": "${input_value}"})
>>> flow.set_end_comp("e", End(), inputs_schema={"result": "${c.result}"})
>>> 
>>>  # Create a compute node
>>>  # AddTenNode: a special node that adds 10 to the input field `source` and returns it
>>> flow.add_workflow_comp("a", AddTenNode("a"), inputs_schema={"source": "${s.input_value}"})
>>> 
>>>  # Use SetVariableComponent to set a variable via a reference path
>>> set_variable_component = SetVariableComponent({"${b.value}": "${a.result}"})
>>> flow.add_workflow_comp("b", set_variable_component)
>>> 
>>>  # Create another compute node that uses the variable that was set
>>> flow.add_workflow_comp("c", AddTenNode("c"), inputs_schema={"source": "${b.value}"})
>>> 
>>>  # Configure connections
>>> flow.add_connection("s", "a")
>>> flow.add_connection("a", "b")
>>> flow.add_connection("b", "c")
>>> flow.add_connection("c", "e")
>>> 
>>>  # Run test
>>> async def run_workflow():
...       return await flow.invoke({"input_value": 5}, WorkflowRuntime())
>>> 
>>> if __name__ == "__main__":
...     result = asyncio.get_event_loop().run_until_complete(run_workflow())
...     print(result.result)
{'output': {'result': 25}}
```
