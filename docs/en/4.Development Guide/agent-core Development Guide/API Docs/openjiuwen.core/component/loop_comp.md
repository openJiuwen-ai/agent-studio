# openjiuwen.core.component.loop_comp

## class openjiuwen.core.component.loop_comp.LoopGroup

Loop body container used to organise and manage a set of components executed in a loop. `LoopGroup` is the foundational container for building loop logic: it can contain multiple components and define the connections between them, providing workflows with robust support for loop execution.

### add_workflow_comp

```python
add_workflow_comp(comp_id: str, workflow_comp: Union[Executable, WorkflowComponent], *, comp_ability: list[ComponentAbility] = None, wait_for_all: bool = None, inputs_schema: dict = None, stream_inputs_schema: dict = None, outputs_schema: dict = None, stream_outputs_schema: dict = None, inputs_transformer=None, outputs_transformer=None, **kwargs) -> Self
```

Add a workflow component to the loop body. Note: components added to a loop body can only be used within that loop body and cannot be used outside of it. Likewise, components added outside the loop body (via `openjiuwen.core.workflow.base.BaseWorkFlow.add_workflow_comp`) can only be used outside the loop body and cannot be used inside it.

**Parameters**：

- **comp_id** (str): The unique identifier of the component, used to reference this component within the loop body. Note: this must be unique across the entire Workflow and must not conflict with any other component id.
- **workflow_comp** (Union[Executable, WorkflowComponent]): The loop-body component instance to add. Its type must not be `LoopComponent`. Two types are supported:
  - `Executable`: A basic executable component (e.g., a function, script, or tool invocation instance).
  - `WorkflowComponent`: A sub-workflow component (i.e., a fully-defined workflow that can be used as a sub-node in the current workflow).
- **\***: Parameter separator.
- **comp_ability** (list[ComponentAbility], optional): A list of component abilities, used to specify which capability types the component supports (e.g., `INVOKE`, `STREAM`, `TRANSFORM`, `COLLECT`). Default: `None`, meaning the system will infer abilities automatically.
- **wait_for_all** (bool, optional): Whether to wait for all upstream dependency components to finish before executing this component. `True` means wait for all; `False` means do not wait. Default: `None`, meaning the system decides automatically based on component ability (streaming components default to `True`, other components default to `False`).
- **inputs_schema** (dict, optional): Schema for the component’s regular input parameters. Used to validate the input data format. Keys should match the component’s input parameter names, and values should match the input data types. If not configured, input format validation is skipped. Default: `None`.
- **stream_inputs_schema** (dict, optional): Schema for the component’s streaming input parameters. Used to define the format specification for streaming input data. Default: `None`.
- **outputs_schema** (dict, optional): Schema for the component’s regular output results. Used to define output format specification for downstream parsing; if not configured, the output format is determined by the component itself. Default: `None`.
- **stream_outputs_schema** (dict, optional): Schema for the component’s streaming output results. Used to define the format specification for streaming output data. Default: `None`.
- **inputs_transformer** ([Transformer](../workflow/workflow_config.md#type-alias-openjiuwencoreworkflowworkflow_configtransformercallableany-any), optional): Input data transformer. Responsible for format conversion or preprocessing before passing data into the component, allowing developers to inject custom logic. Schema-based structure comes first, transformer-based conversion comes after; both may be configured. Default: `None`.
- **outputs_transformer** ([Transformer](../workflow/workflow_config.md#type-alias-openjiuwencoreworkflowworkflow_configtransformercallableany-any), optional): Output data transformer. Responsible for format conversion or post-processing after the component produces results, allowing developers to inject custom logic. Default: `None`.
- **kwargs**: Reserved parameters; configuration does not take effect.

> **Notes**
>
> - The configuration and requirements for `inputs_schema` and `inputs_transformer` can be referenced in the developer documentation. Their values may reference upstream component outputs. The values of `outputs_schema` and `outputs_transformer` may use the component’s own outputs.
> - If neither `inputs_schema` nor `inputs_transformer` is configured, all inputs are passed through unchanged. If neither `outputs_schema` nor `outputs_transformer` is configured, the output format is the component’s native output.
> - If schema and transformer are both configured, only the transformer takes effect.

**Example**：

```python
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.executable import Input, Output
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.component.loop_comp import LoopGroup
>>> # Custom component AddTenNode: on each invocation, add 10 to inputs["source"]
>>> class AddTenNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self, node_id: str):
...         super().__init__()
...         self.node_id = node_id
...
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         return {"result": inputs["source"] + 10}
>>>
>>> # Create the loop body
>>> loop_group = LoopGroup()
>>> # Add the first component to process the current item in the loop array
>>> # AddTenNode is a simple component that increments input field `source` by 10 and outputs to `result`
>>> loop_group.add_workflow_comp("1", AddTenNode("1"), inputs_schema={"source": "${l.item}"})
>>> # Add the second component to process an intermediate variable
>>> loop_group.add_workflow_comp("2", AddTenNode("2"), inputs_schema={"source": "${l.user_var}"})
```

### start_nodes

```python
start_nodes(nodes: list[str]) -> Self
```

Set the start component(s) of the loop body.

**Parameters**：

- **nodes** (list[str]): A list of start component identifiers. Currently, only a single start component is supported. The `nodes` list must not contain `None`. Example: `['start_node']`.

**Example**：

```python
>>> from openjiuwen.core.component.loop_comp import LoopGroup
>>> # Set the start component of the loop body
>>> loop_group = LoopGroup()
>>> loop_group.add_workflow_comp("1", AddTenNode("1"))
>>> loop_group.add_workflow_comp("2", AddTenNode("2"))
>>> # Use component "1" as the loop start component
>>> loop_group.start_nodes(["1"])
```

### end_nodes

```python
end_nodes(nodes: list[str]) -> Self
```

Set the end component(s) of the loop body.

**Parameters**：

- **nodes** (list[str]): A list of end component identifiers. Currently, only a single end component is supported. The `nodes` list must not contain `None`. Example: `['end_node']`.

**Example**：

```python
>>> from openjiuwen.core.component.loop_comp import LoopGroup
>>> # Set the end component of the loop body
>>> loop_group = LoopGroup()
>>> loop_group.add_workflow_comp("1", AddTenNode("1"))
>>> loop_group.add_workflow_comp("2", AddTenNode("2"))
>>> # Use component "2" as the loop end component
>>> loop_group.end_nodes(["2"])
```

## class openjiuwen.core.component.loop_comp.LoopType

Loop type enum that defines the supported loop types.

- **Array**: Array loop. Iterates over each element in an array. Value: `"array"`.
- **Number**: Numeric loop. Executes the loop a specified number of times. Value: `"number"`.
- **AlwaysTrue**: Infinite loop. Continues executing until interrupted. Value: `"always_true"`.
- **Expression**: Expression loop. Continues or stops based on the expression result. Value: `"expression"`.

## class openjiuwen.core.component.loop_comp.LoopComponent

```python
class openjiuwen.core.component.loop_comp.LoopComponent(loop_group: LoopGroup, output_schema: dict)
```

A standard loop component that provides a higher-level encapsulation of loop functionality for simpler usage. With `LoopComponent`, you can easily implement multiple loop modes such as array loops and numeric loops, and it also supports advanced features such as loop interruption and intermediate variable passing.

**Parameters**：

- **loop_group** ([LoopGroup](#class-openjiuwencorecomponentloop_comploopgroup)): The loop group instance defining the components executed within the loop body. A loop group may contain multiple components and define their execution order via connections. `loop_group` must contain at least one component.
- **output_schema** (dict): Output schema definition used to extract specific fields from loop results. Keys are output field names, and values are expression paths. For example, `{"results": "${1.result}", "user_var": "${l.user_var}"}` means: expose component `"1"`’s `result` field and the intermediate variable `user_var` as the loop component outputs.

> **Notes**
>
> 1. **Common loop-body components**: When implementing loop functionality, it is common to use the following components together:
>
>    - [BreakComponent](./break_comp.md#class-openjiuwencorecomponentbreak_compbreakcomponent): Used to interrupt the loop. When execution reaches this component, the loop stops immediately.
>    - [SetVariableComponent](./set_variable_comp.md#class-openjiuwencorecomponentset_variable_compsetvariablecomponent): Used to set variable values during the loop, supporting reference paths and nested-structure variable updates.
>
> 2. **Loop variable scope**: Variables inside the loop are only visible within the loop; external components cannot access them directly.
> 3. **Intermediate variable initialisation**: Use the `intermediate_var` parameter of `LoopComponent` to initialise intermediate variables before the loop starts, ensuring correct loop logic.
> 4. **Loop interruption mechanism**:
>
>    - When using `BreakComponent`, you must configure the interruption logic correctly within the `LoopComponent` loop body.
>    - After the loop is interrupted, any results collected so far are still retained and returned.
>    - For details, see [BreakComponent](./break_comp.md#class-openjiuwencorecomponentbreak_compbreakcomponent).
>
> 5. **Loop condition types**: Choose the appropriate loop type based on your needs:
>
>    - `array`: Suitable for iterating over an array.
>    - `always_true`: Suitable for running indefinitely until explicitly interrupted.
>
> 6. **Performance considerations**: For large datasets, pay attention to memory usage and execution efficiency, and avoid overly complex operations inside the loop body.

**Example**：

The following example shows how to use `LoopComponent` together with the `AlwaysTrue` condition and `BreakComponent` to implement an infinite loop that is interrupted under specific conditions.

**Note**: The `AlwaysTrue` condition causes the loop to keep running until `BreakComponent` explicitly interrupts it. For details, see [BreakComponent](./break_comp.md#class-openjiuwencorecomponentbreak_compbreakcomponent).

```python
>>> import asyncio
>>>
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.break_comp import BreakComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.loop_comp import LoopComponent, LoopGroup
>>> from openjiuwen.core.component.set_variable_comp import SetVariableComponent
>>> from openjiuwen.core.component.branch_comp import BranchComponent
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>>
>>> # Generic node component that returns an input value
>>> class CommonNode(ComponentExecutable, WorkflowComponent):
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         return {"output": inputs["value"]}
>>>
>>> # Create LoopGroup
>>> loop_group = LoopGroup()
>>>
>>> # Create a generic node as the core component of the loop body
>>> class commonNode(CommonNode):
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         # Simulate work inside the loop body and return a result
...         return {"output": True}
>>>
>>> # Add workflow components into LoopGroup
>>> loop_group.add_workflow_comp("a", commonNode())
>>>
>>> # Create a branch component for conditional routing
>>> branch_component = BranchComponent()
>>> loop_group.add_workflow_comp("branch", branch_component)
>>>
>>> # Create a variable-setting component to increment user_var
>>> set_variable_component = SetVariableComponent({"user_var": "${loop.user_var} + 1"})
>>> loop_group.add_workflow_comp("setVar", set_variable_component)
>>>
>>> # Create a loop-termination component
>>> break_node = BreakComponent()
>>> loop_group.add_workflow_comp("break", break_node)
>>>
>>> # Set "a" as loop start, and "setVar" as the normal loop end
>>> loop_group.start_nodes(["a"])
>>> loop_group.end_nodes(["setVar"])
>>>
>>> # Configure branch conditions for BranchComponent
>>> # Branch 1: continue looping and execute setVariableComponent
>>> branch_component.add_branch("${loop.index} < 2", ["setVar"])
>>> # Branch 2: terminate looping and execute break component
>>> branch_component.add_branch("${loop.index} >= 2", ["break"])
>>>
>>> # Configure component connections
>>> loop_group.add_connection("a", "branch")
>>>
>>> # Create LoopComponent and configure output schema to capture the final intermediate variable, loop counter, and loop results
>>> loop_component = LoopComponent(
...     loop_group,
...     {
...         "user_var": "${loop.user_var}",
...         "loop_count": "${loop.index}",
...         "results": "${a.output}"
...     }
... )
>>>
>>> # Create workflow instance
>>> workflow = Workflow()
>>>
>>> # Add start component
>>> workflow.set_start_comp("s", Start({}))
>>>
>>> # Add end component and reference outputs from the loop component
>>> workflow.set_end_comp("e", End({}),
...                        inputs_schema={
...                            "user_var": "${loop.user_var}",
...                            "loop_count": "${loop.loop_count}",
...                            "results": "${loop.results}"
...                        })
>>>
>>> # Add loop component; set loop_type to always_true and initialise intermediate variables
>>> workflow.add_workflow_comp("loop", loop_component,
...                               inputs_schema={
...                                   "loop_type": "always_true",
...                                   "intermediate_var": {"user_var": 0}
...                               })
>>>
>>> # Serially connect components: start -> loop -> end
>>> workflow.add_connection("s", "loop")
>>> workflow.add_connection("loop", "e")
>>>
>>> # Execute the workflow by calling invoke
>>> result = asyncio.run(workflow.invoke({}, WorkflowRuntime()))
>>>
>>> print(f"Execution result: {result.result}")
>>> output = result.result.get('output', {})
>>>
>>> # Verify the loop ran 3 times
>>> assert output.get("loop_count") == 3, f"Expected loop_count == 3, got {output.get('loop_count')}"
>>>
>>> # Verify the result of each loop iteration
>>> expected_results = [True, True, True]
>>> assert output.get("results") == expected_results, f"Expected {expected_results}, got {output.get('results')}"
```
