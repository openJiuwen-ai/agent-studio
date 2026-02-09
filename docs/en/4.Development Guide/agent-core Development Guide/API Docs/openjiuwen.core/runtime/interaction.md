# openjiuwen.core.runtime.interaction

## class openjiuwen.core.runtime.interaction.interactive_input.InteractiveInput

```python
class openjiuwen.core.runtime.interaction.interactive_input.InteractiveInput(raw_inputs: Any)
```

Construct interactive input between the user and the workflow in interruption scenarios.

**Parameters**:

- **raw_inputs** (Any): The user's interactive input, which will be returned when resuming the workflow after an interruption. Passing None will raise an exception.

**Exceptions**:

- **JiuWenBaseException**: Base class for openJiuwen exceptions. For detailed information and solutions, see [StatusCode](../common/exception/status_code.md).

**Examples**:

```python
>>> import asyncio
>>> import uuid
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.executable import Input, Output
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.interaction.interaction import InteractionOutput
>>> from openjiuwen.core.runtime.interaction.interactive_input import InteractiveInput
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> 
>>> # Create a workflow component with interruption-based interaction
>>> class InteractiveNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         cmd = inputs.get("cmd")
...         # Ask the user and wait for a reply
...         user_input = await runtime.interact(f"Do you want to execute the command '{cmd}'?")
...         return {"result": user_input}
...  
>>> # Build a workflow and execute it to trigger the interactive interruption flow
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start({}), inputs_schema={"command1": "${cmd1}"})
>>> flow.add_workflow_comp("interactive_node1", InteractiveNode(), inputs_schema={"cmd": "${start.command1}"})
>>> flow.set_end_comp("end", End(), inputs_schema={"result1": "${interactive_node1.result}"})
>>> flow.add_connection("start", "interactive_node1")
>>> flow.add_connection("interactive_node1", "end")
>>> 
>>> session_id = uuid.uuid4().hex
>>> 
>>> # Execute the workflow
>>> output = asyncio.run(flow.invoke({"cmd1": "delete all files"}, WorkflowRuntime(session_id=session_id)))
>>> 
>>> # Check whether the result is an interaction output (interruption)
>>> if isinstance(output.result[0].payload, InteractionOutput):
...     # Get the prompt from the interrupted component
...     print(output.result[0].payload.value)
...
Do you want to execute the command 'delete all files'?
>>> 
>>> # Create `InteractiveInput` to provide user input and resume workflow execution
>>> 
>>> user_input = InteractiveInput(raw_inputs='Yes')
>>> output = asyncio.run(flow.invoke(user_input, WorkflowRuntime(session_id=session_id)))
>>> print(output.result.get("output").get("result1"))
Yes
```

Notes

- output is the workflow output. For details, see [Workflow output overview](../../openjiuwen.core/workflow/base.md).
- The first workflow output is `Do you want to execute the command '{delete all files}'?`. At this time, output.result is a list, and each element is a streaming output chunk. For details, see [Streaming output overview](../../../../agent-core%20Development%20Guide/Advanced%20Usage/Runtime/Streaming%20Output.md). The payload contains the interaction output. For details, see [Interaction output overview](#class-openjiuwencoreruntimeinteractioninteractioninteractionoutput).
- After constructing user input with InteractiveInput, the output becomes `Yes`. At this time, output.result comes from the end component. For details, see [End component overview](../component/end_comp.md#class-openjiuwencorecomponentend_compend).

### update

```python
update(self, node_id: str, value: Any)
```

Provide user input for a specified component. This is generally used in workflows that have components with multiple interruption resumes. When interactive interruptions occur, each interrupted component may require different user input. If user input has already been provided via the constructor and raw_inputs, calling this method will raise an exception.

**Parameters**:

- **node_id** (str): The ID of the interrupted component. Passing None will raise an exception.
- **value** (Any): The user input, which will be returned by the [interact](./runtime.md#interact) API. Passing None will raise an exception.

**Exceptions**:

- **JiuWenBaseException**: Base class for openJiuwen exceptions. For detailed information and solutions, see [StatusCode](../common/exception/status_code.md).

**Examples**:

```python
>>> import asyncio
>>> import uuid
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.executable import Input, Output
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.interaction.interactive_input import InteractiveInput
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> # Create a component with interactive interruption
>>> class InteractiveNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         cmd = inputs.get("cmd")
...         # Ask the user and wait for a reply
...         user_input = await runtime.interact(f"Do you want to execute the command '{cmd}'?")
...         return {"result": user_input}
... 
>>> # Build a workflow with two interactive interruption nodes,
>>> # and execute it to trigger both components' interruption flows
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start({}), inputs_schema={"command1": "${cmd1}", "command2": "${cmd2}"})
>>> flow.add_workflow_comp("interactive_node1", InteractiveNode(), inputs_schema={"cmd": "${start.command1}"})
>>> flow.add_workflow_comp("interactive_node2", InteractiveNode(), inputs_schema={"cmd": "${start.command2}"})
>>> flow.set_end_comp("end", End(),inputs_schema={"result1": "${interactive_node1.result}", "result2": "${interactive_node2.result}"})
>>> flow.add_connection("start", "interactive_node1")
>>> flow.add_connection("start", "interactive_node2")
>>> flow.add_connection("interactive_node1", "end")
>>> flow.add_connection("interactive_node2", "end")
>>> 
>>> session_id = uuid.uuid4().hex
>>> output = asyncio.run(flow.invoke({"cmd1": "delete all files", "cmd2": "kill all processes"}, WorkflowRuntime(session_id=session_id)))
>>> 
>>> node_id_1 = output.result[0].payload.id
>>> print(node_id_1)
interactive_node2
>>> print(output.result[0].payload.value)
Do you want to execute the command 'kill all processes'?
>>> 
>>> node_id_2 = output.result[1].payload.id
>>> print(node_id_2)
interactive_node1
>>> print(output.result[1].payload.value)
Do you want to execute the command 'delete all files'?
>>> 
>>> # Provide different user inputs for the interrupted components
>>> print("----------Second round------------")
----------Second round------------
>>> user_input = InteractiveInput()
>>> user_input.update(node_id_1, "Yes")
>>> user_input.update(node_id_2, "No")
>>> 
>>> output = asyncio.run(flow.invoke(user_input, WorkflowRuntime(session_id=session_id)))
>>> print(output.result.get("output"))
{'result1': 'No', 'result2': 'Yes'}
>>> 
```

Notes

- Here, output is the workflow output. For details, see [Workflow output overview](../../openjiuwen.core/workflow/base.md).
- The first workflow output contains `interactive_node1`, `Do you want to execute the command 'delete all files'?`, `interactive_node2`, and `Do you want to execute the command 'kill all processes'?`. At this time, output.result is a list, and each element is a streaming output chunk. For details, see [Streaming output overview](../../../../agent-core%20Development%20Guide/Advanced%20Usage/Runtime/Streaming%20Output.md). The payload contains the interaction output. For details, see [Interaction output overview](#class-openjiuwencoreruntimeinteractioninteractioninteractionoutput).
- After constructing the user inputs with InteractiveInput, the output becomes `{'result1': 'Yes', 'result2': 'No'}`. At this time, output.result comes from the end component. For details, see [End component overview](../component/end_comp.md#class-openjiuwencorecomponentend_compend).

## class openjiuwen.core.runtime.interaction.interaction.InteractionOutput

```python
class openjiuwen.core.runtime.interaction.interaction.InteractionOutput
```

A data class representing user–workflow interaction output, primarily used in interruption scenarios. It is typically used as the payload of a [WorkflowChunk](../../openjiuwen.core/workflow/base.md).

- id (str): The ID of the interrupted component.
- value (Any): The prompt message produced when the component is interrupted.

Examples:

```python
>>> import asyncio
>>> import uuid
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.executable import Input, Output
>>> from openjiuwen.core.runtime.base import ComponentExecutable
>>> from openjiuwen.core.runtime.interaction.interaction import InteractionOutput
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> 
>>> # Create a workflow component with interruption-based interaction
>>> class InteractiveNode(ComponentExecutable, WorkflowComponent):
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         cmd = inputs.get("cmd")
...         # Ask the user and wait for a reply
...         user_input = await runtime.interact(f"Do you want to execute the command '{cmd}'?")
...         return {"user_input": user_input}
... 
>>> # Build a workflow and execute it to trigger the interactive interruption flow
>>> flow = Workflow()
>>> flow.set_start_comp("start", Start({}), inputs_schema={"command1": "${cmd1}"})
>>> flow.add_workflow_comp("interactive_node1", InteractiveNode(), inputs_schema={"cmd": "${start.command1}"})
>>> flow.set_end_comp("end", End(), inputs_schema={ "result1": "${interactive_node1.result}"})
>>> flow.add_connection("start", "interactive_node1")
>>> flow.add_connection("interactive_node1", "end")
>>> 
>>> session_id = uuid.uuid4().hex
>>> # Execute the workflow
>>> output = asyncio.run(flow.invoke({"cmd1": "delete all files"}, WorkflowRuntime(session_id=session_id)))
>>> 
>>> # Check whether the result is an interaction output
>>> if isinstance(output.result[0].payload, InteractionOutput):
...     # Get the prompt from the interrupted component
...     print(output.result[0].payload.id)
...
interactive_node1
>>>     print(output.result[0].payload.value)
Do you want to execute the command 'delete all files'
```

Notes

- Here, output is the workflow output. For details, see [Workflow output overview](../../openjiuwen.core/workflow/base.md).
- The workflow output contains `interactive_node1` and `Do you want to execute the command '{delete all files}'`. At this time, output.result is a list, and each element is a streaming output chunk. For details, see [Streaming output overview](../../../../agent-core%20Development%20Guide/Advanced%20Usage/Runtime/Streaming%20Output.md). The payload contains the interaction output, i.e., the `InteractionOutput` described in this section.