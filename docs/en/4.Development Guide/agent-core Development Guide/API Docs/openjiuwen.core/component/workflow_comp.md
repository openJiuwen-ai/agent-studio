# openjiuwen.core.component.workflow_comp

## class openjiuwen.core.component.workflow_comp.SubWorkflowComponent

```python
class openjiuwen.core.component.workflow_comp.SubWorkflowComponent(sub_workflow: Workflow)
```

`SubWorkflowComponent` is an openJiuwen built-in sub-workflow component. It provides the capability to embed a sub-workflow, enabling hierarchical management and flexible composition of complex workflow business logic. When execution reaches a sub-workflow component, it passes input data and configuration to the sub-workflow and starts executing it. After the sub-workflow completes, its results are returned and execution continues in the main workflow.

**Parameters**：

* **sub_workflow** ([Workflow](../workflow/base.md#class-openjiuwencoreworkflowbaseworkflow)): The sub-workflow instance. Must not be `None`.

**Exceptions**：

* **JiuWenBaseException**: The base exception type for openJiuwen. For detailed information and resolution methods, see  
  [StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Example**：

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.workflow_comp import SubWorkflowComponent
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> 
>>> 
>>> class CustomComponent(WorkflowComponent, ComponentExecutable):
...     """Custom component"""
... 
...     def __init__(self):
...         super().__init__()
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         """Process input and return the user's query"""
...         query = inputs.get("query", "")
...         return {
...             "result": query
...         }
>>> 
>>> 
>>> # Initialise the sub-workflow
>>> sub_workflow = Workflow()
>>> 
>>> # Add three components with IDs sub_start, sub_custom_comp, and sub_end to the sub-workflow
>>> sub_workflow.set_start_comp("sub_start", Start(), inputs_schema={"query": "${query}"})
>>> sub_workflow.add_workflow_comp(
...     "sub_custom_comp",
...     CustomComponent(),
...     inputs_schema={"query": "${sub_start.query}"}
... )
>>> sub_workflow.set_end_comp("sub_end", End(), inputs_schema={"result": "${sub_custom_comp.result}"})
>>> 
>>> # Configure the sub-workflow topology: sub_start -> sub_custom_comp -> sub_end
>>> sub_workflow.add_connection("sub_start", "sub_custom_comp")
>>> sub_workflow.add_connection("sub_custom_comp", "sub_end")
>>> 
>>> # Initialise the main workflow
>>> main_workflow = Workflow()
>>> 
>>> # Create the sub-workflow execution component using the previously constructed sub-workflow
>>> sub_workflow_comp = SubWorkflowComponent(sub_workflow)
>>> 
>>> # Add three components with IDs start, sub_workflow_comp, and end to the main workflow
>>> main_workflow.set_start_comp("start", Start(), inputs_schema={"query": "${user_inputs.query}"})
>>> main_workflow.add_workflow_comp(
...     "sub_workflow_comp",
...     sub_workflow_comp,
...     inputs_schema={"query": "${start.query}"}
... )
>>> main_workflow.set_end_comp("end", End(), inputs_schema={"result": "${sub_workflow_comp.output.result}"})
>>> 
>>> # Configure the main workflow topology: start -> sub_workflow_comp -> end
>>> main_workflow.add_connection("start", "sub_workflow_comp")
>>> main_workflow.add_connection("sub_workflow_comp", "end")
>>> 
>>> 
>>> async def run_workflow():
...     # Create a workflow runtime
...     runtime = WorkflowRuntime(workflow_id="test_workflow", session_id="test_session")
... 
...     # Construct inputs
...     inputs = {"user_inputs": {"query": "hello"}}
... 
...     # Invoke the workflow
...     result = await main_workflow.invoke(inputs, runtime)
...     return result
>>> 
>>> 
>>> res = asyncio.run(run_workflow())
>>> print(f"main workflow with sub workflow run result: {res}")
main workflow with sub workflow run result: result={'output': {'result': 'hello'}} state=<WorkflowExecutionState.COMPLETED: 'COMPLETED'>
```
