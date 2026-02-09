# openjiuwen.core.component.base

## class openjiuwen.core.component.base.WorkflowComponent

`WorkflowComponent` is the abstract base class for custom workflow components. All custom components must inherit from this class and implement the logic for (1) adding themselves to the graph and (2) converting themselves into an executable unit (`ComponentExecutable`).

### add_component

```python
add_component(graph: Graph, node_id: str, wait_for_all: bool = False)
```

Defines how to add the current component into the specified `graph`.

**Parameters**:

- **graph** ([Graph](../graph/base.md#class-graph)): The `graph` instance of the `workflow`.
- **node_id** (str): A unique `node_id` for this component within the `graph`.
- **wait_for_all** (bool): Whether this component must wait for all upstream components to finish execution. `True` means wait; `False` means do not wait. Default: `False`.

**Example**:

```python
>>> import asyncio
>>> import random
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.branch_router import BranchRouter
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.base import Graph
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> 
>>> # The custom component `CustomIntentComponent` implements `add_component` to configure
>>> # built-in conditional edges for this node, and also provides `add_branch` to bind
>>> # target nodes for those conditional edges.
>>> class CustomIntentComponent(WorkflowComponent, ComponentExecutable):
...     def __init__(self, default_intents):
...         super().__init__()
...         self._intents = default_intents
...         self._router = BranchRouter()
... 
...     def add_component(self, graph: Graph, node_id: str, wait_for_all: bool = False) -> None:
...         graph.add_node(node_id, self.to_executable(), wait_for_all=wait_for_all)
...         graph.add_conditional_edges(node_id, self._router)
... 
...     def add_branch(self, condition: str, target: list[str], branch_id: str):
...         self._router.add_branch(condition=condition, target=target, branch_id=branch_id)
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         self._router.set_runtime(runtime)
...         return {'result': self._intents[random.randint(0, len(self._intents) - 1)]}
>>> 
>>> 
>>> class TravelComponent(WorkflowComponent, ComponentExecutable):
...     def __init__(self, node_id):
...         super().__init__()
...         self.node_id = node_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         print(f'[{self.node_id}] inputs = {inputs}')
...         return inputs
>>> 
>>> 
>>> class EatComponent(WorkflowComponent, ComponentExecutable):
...     def __init__(self, node_id):
...         super().__init__()
...         self.node_id = node_id
... 
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         print(f'[{self.node_id}] inputs = {inputs}')
...         return inputs
>>> 
>>> 
>>> async def run_workflow():
...     # Create the workflow
...     flow = Workflow()
...     flow.set_start_comp("start", Start(), inputs_schema={"query": "${user_inputs.query}"})
... 
...     intent_component = CustomIntentComponent(["出行", "餐饮"])
...     intent_component.add_branch(condition="${intent.result} == '出行'", target=['travel'], branch_id='1')
...     intent_component.add_branch(condition="${intent.result} == '餐饮'", target=['eat'], branch_id='2')
...     flow.add_workflow_comp("intent", intent_component, inputs_schema={"query": "${start.query}"})
...     flow.add_workflow_comp("eat", EatComponent("eat"), inputs_schema={"intent": "${intent.result}"})
...     flow.add_workflow_comp("travel", TravelComponent("travel"), inputs_schema={"intent": "${intent.result}"})
...     flow.set_end_comp("end", End(), inputs_schema={"eat": "${eat.intent}", "travel": "${travel.intent}"})
...     flow.add_connection("start", "intent")
...     flow.add_connection("eat", "end")
...     flow.add_connection("travel", "end")
... 
...     runtime = WorkflowRuntime()
...     output = await flow.invoke({"user_inputs": {"query": "去新疆"}}, runtime)
...     print(output.result)
>>> 
>>> if __name__ == '__main__':
...     asyncio.get_event_loop().run_until_complete(run_workflow())
[travel] inputs = {'intent': '出行'}
{'output': {'travel': '出行'}}
```

### to_executable

```python
to_executable() -> Executable
```

Returns an executable instance corresponding to this component. openJiuwen allows users to implement `ComponentExecutable` and return it from this method so that it can be scheduled and executed by the runtime.

**Returns**:

**[Executable](../graph/base.md)**: The executable instance for this component.

**Example**:

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.component.base import WorkflowComponent
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.context_engine.base import Context
>>> from openjiuwen.core.graph.executable import Executable
>>> from openjiuwen.core.runtime.base import ComponentExecutable, Input, Output
>>> from openjiuwen.core.runtime.runtime import Runtime
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> # `CalculateComponent` inherits from `WorkflowComponent`. It performs arithmetic operations.
>>> # It implements `to_executable` to return a `ComputeExecutor` instance containing the
>>> # compute logic, and is added into the workflow graph via `add_component`.
>>> class CalculateComponent(WorkflowComponent):
...     def to_executable(self) -> Executable:
...         return ComputeExecutor()
>>> 
>>> class ComputeExecutor(ComponentExecutable):
...     async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
...         return {'result': self.__calculate__(data=inputs.get('data'))}
... 
...     def __calculate__(self, data):
...         operator = data.get('operator')
...         a = data.get('a')
...         b = data.get('b')
...         if operator == 'add':
...             return a + b
...         if operator == 'multiply':
...             return a * b
...         if operator == 'substract':
...             return a - b
...         return a / b
>>> 
>>> async def run_workflow():
...     # Create and run the workflow
...     flow = Workflow()
...     flow.set_start_comp(
...         "start",
...         Start(),
...         inputs_schema={"a": "${user_inputs.a}", "b": "${user_inputs.b}", "operator": "${user_inputs.operator}"}
...     )
...     flow.add_workflow_comp("compute", CalculateComponent(), inputs_schema={"data": "${start}"})
...     flow.set_end_comp("end", End(), inputs_schema={"result": "${compute.result}"})
...     flow.add_connection("start", "compute")
...     flow.add_connection("compute", "end")
...     runtime = WorkflowRuntime()
...     output = await flow.invoke({"user_inputs": {"a": 1, "b": 2, "operator": "add"}}, runtime)
...     print(output.result)
>>> 
>>> if __name__ == '__main__':
...     asyncio.run(run_workflow())
{'output': {'result': 3}}
```
